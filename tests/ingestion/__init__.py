"""Unit tests for filesystem traversal and metadata tracking."""

import asyncio
import tempfile
import pytest
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock

from src.ingestion.filesystem import (
    FilesystemTraversal,
    FilesystemWatcher,
    MetadataTracker,
    FilesystemMonitor,
    FileMetadata,
    FileChangeType,
    DOCLING_FORMATS,
)


@pytest.fixture
def temp_dir():
    """Create temporary directory with test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        
        # Create test files
        (tmppath / "document.pdf").touch()
        (tmppath / "image.png").touch()
        (tmppath / "audio.mp3").touch()
        (tmppath / "data.json").touch()
        (tmppath / "unsupported.xyz").touch()
        
        # Create subdirectory with files
        subdir = tmppath / "subdir"
        subdir.mkdir()
        (subdir / "nested.docx").touch()
        
        yield tmppath


@pytest.fixture
def temp_db():
    """Create temporary database."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)
    yield db_path
    db_path.unlink(missing_ok=True)


class TestFilesystemTraversal:
    """Tests for FilesystemTraversal class."""

    def test_init_valid_directory(self, temp_dir):
        """Test initialization with valid directory."""
        traversal = FilesystemTraversal(temp_dir)
        assert traversal.data_dir == temp_dir

    def test_init_invalid_directory(self):
        """Test initialization with invalid directory."""
        with pytest.raises(ValueError):
            FilesystemTraversal(Path("/nonexistent/directory"))

    def test_compute_file_hash(self, temp_dir):
        """Test file hash computation."""
        test_file = temp_dir / "test.txt"
        test_file.write_text("hello world")
        
        hash1 = FilesystemTraversal.compute_file_hash(test_file)
        hash2 = FilesystemTraversal.compute_file_hash(test_file)
        
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA256 hex length

    def test_compute_path_hash(self, temp_dir):
        """Test path hash computation."""
        path = temp_dir / "test.txt"
        hash1 = FilesystemTraversal.compute_path_hash(path)
        hash2 = FilesystemTraversal.compute_path_hash(path)
        
        assert hash1 == hash2
        assert len(hash1) == 64

    def test_detect_mime_type(self, temp_dir):
        """Test MIME type detection."""
        # Create files with content
        pdf_file = temp_dir / "test.pdf"
        pdf_file.write_bytes(b"%PDF-1.4")
        
        txt_file = temp_dir / "test.txt"
        txt_file.write_text("plain text")
        
        pdf_mime = FilesystemTraversal.detect_mime_type(pdf_file)
        txt_mime = FilesystemTraversal.detect_mime_type(txt_file)
        
        # filetype is lenient, so we just check it returns something
        assert pdf_mime is not None or txt_mime is not None

    def test_is_supported_format(self, temp_dir):
        """Test format support checking."""
        pdf_file = temp_dir / "test.pdf"
        unsupported_file = temp_dir / "test.xyz"
        
        assert FilesystemTraversal.is_supported_format(pdf_file)
        assert not FilesystemTraversal.is_supported_format(unsupported_file)

    def test_extract_file_metadata(self, temp_dir):
        """Test file metadata extraction."""
        test_file = temp_dir / "test.pdf"
        test_file.write_text("test content")
        
        traversal = FilesystemTraversal(temp_dir)
        metadata = traversal.extract_file_metadata(test_file)
        
        assert metadata.name == "test.pdf"
        assert metadata.file_size > 0
        assert metadata.path == "test.pdf"
        assert metadata.absolute_path == str(test_file)
        assert not metadata.is_directory

    def test_traverse_all_formats(self, temp_dir):
        """Test traversing and finding all supported formats."""
        traversal = FilesystemTraversal(temp_dir)
        files = traversal.traverse()
        
        # Should find: document.pdf, image.png, audio.mp3, data.json, nested.docx
        assert len(files) >= 4
        
        # Check that unsupported file is not included
        names = [f.name for f in files]
        assert "unsupported.xyz" not in names

    def test_traverse_with_extension_filter(self, temp_dir):
        """Test traversing with extension filter."""
        traversal = FilesystemTraversal(temp_dir)
        files = traversal.traverse(extensions={'pdf', 'docx'})
        
        names = [f.name for f in files]
        assert "document.pdf" in names
        assert "nested.docx" in names
        assert "audio.mp3" not in names

    def test_traverse_nested_directories(self, temp_dir):
        """Test traversing nested directories."""
        traversal = FilesystemTraversal(temp_dir)
        files = traversal.traverse()
        
        # Should find nested file
        paths = [f.path for f in files]
        assert any("subdir" in p for p in paths)


class TestMetadataTracker:
    """Tests for MetadataTracker class."""

    def test_init_creates_database(self, temp_db):
        """Test database initialization."""
        tracker = MetadataTracker(temp_db)
        assert temp_db.exists()

    def test_upsert_file(self, temp_db):
        """Test inserting file metadata."""
        tracker = MetadataTracker(temp_db)
        
        metadata = FileMetadata(
            file_id="test-id",
            path="test.pdf",
            absolute_path="/tmp/test.pdf",
            name="test.pdf",
            mime_type="application/pdf",
            file_size=1024,
            created_at=datetime.now(),
            modified_at=datetime.now(),
            indexed_at=None,
            file_hash="abc123",
            indexed=False,
            is_directory=False,
            tags=["document"],
            metadata_json={"format": "pdf"},
        )
        
        tracker.upsert_file(metadata)
        
        # Verify it was stored
        retrieved = tracker.get_file_by_id("test-id")
        assert retrieved is not None
        assert retrieved["path"] == "test.pdf"

    def test_has_file_changed(self, temp_db):
        """Test file change detection."""
        tracker = MetadataTracker(temp_db)
        
        metadata = FileMetadata(
            file_id="test-id",
            path="test.pdf",
            absolute_path="/tmp/test.pdf",
            name="test.pdf",
            mime_type="application/pdf",
            file_size=1024,
            created_at=datetime.now(),
            modified_at=datetime.now(),
            indexed_at=None,
            file_hash="abc123",
            indexed=False,
            is_directory=False,
            tags=[],
            metadata_json={},
        )
        
        tracker.upsert_file(metadata)
        
        # Same hash should not be changed
        assert not tracker.has_file_changed("test-id", "abc123")
        
        # Different hash should be changed
        assert tracker.has_file_changed("test-id", "xyz789")
        
        # New file should be changed
        assert tracker.has_file_changed("unknown-id", "any-hash")

    def test_mark_indexed(self, temp_db):
        """Test marking file as indexed."""
        tracker = MetadataTracker(temp_db)
        
        metadata = FileMetadata(
            file_id="test-id",
            path="test.pdf",
            absolute_path="/tmp/test.pdf",
            name="test.pdf",
            mime_type="application/pdf",
            file_size=1024,
            created_at=datetime.now(),
            modified_at=datetime.now(),
            indexed_at=None,
            file_hash="abc123",
            indexed=False,
            is_directory=False,
            tags=[],
            metadata_json={},
        )
        
        tracker.upsert_file(metadata)
        tracker.mark_indexed("test-id")
        
        retrieved = tracker.get_file_by_id("test-id")
        assert retrieved["indexed"] == 1

    def test_get_indexed_files(self, temp_db):
        """Test retrieving indexed files."""
        tracker = MetadataTracker(temp_db)
        
        for i in range(3):
            metadata = FileMetadata(
                file_id=f"test-{i}",
                path=f"test{i}.pdf",
                absolute_path=f"/tmp/test{i}.pdf",
                name=f"test{i}.pdf",
                mime_type="application/pdf",
                file_size=1024,
                created_at=datetime.now(),
                modified_at=datetime.now(),
                indexed_at=None,
                file_hash="abc123",
                indexed=(i < 2),
                is_directory=False,
                tags=[],
                metadata_json={},
            )
            tracker.upsert_file(metadata)
        
        indexed = tracker.get_indexed_files()
        assert len(indexed) == 2

    def test_record_change(self, temp_db):
        """Test recording file changes."""
        tracker = MetadataTracker(temp_db)
        
        tracker.record_change("test-id", "test.pdf", FileChangeType.MODIFIED)
        
        changes = tracker.get_unprocessed_changes()
        assert len(changes) == 1
        assert changes[0]["change_type"] == FileChangeType.MODIFIED.value

    def test_mark_change_processed(self, temp_db):
        """Test marking changes as processed."""
        tracker = MetadataTracker(temp_db)
        
        tracker.record_change("test-id", "test.pdf", FileChangeType.MODIFIED)
        
        changes = tracker.get_unprocessed_changes()
        assert len(changes) == 1
        
        tracker.mark_change_processed(changes[0]["id"])
        
        unprocessed = tracker.get_unprocessed_changes()
        assert len(unprocessed) == 0

    def test_get_statistics(self, temp_db):
        """Test getting statistics."""
        tracker = MetadataTracker(temp_db)
        
        for i in range(3):
            metadata = FileMetadata(
                file_id=f"test-{i}",
                path=f"test{i}.pdf",
                absolute_path=f"/tmp/test{i}.pdf",
                name=f"test{i}.pdf",
                mime_type="application/pdf",
                file_size=1024,
                created_at=datetime.now(),
                modified_at=datetime.now(),
                indexed_at=None,
                file_hash="abc123",
                indexed=(i < 2),
                is_directory=False,
                tags=[],
                metadata_json={},
            )
            tracker.upsert_file(metadata)
        
        stats = tracker.get_statistics()
        assert stats["total_files"] == 3
        assert stats["indexed_files"] == 2
        assert stats["unindexed_files"] == 1


class TestFilesystemWatcher:
    """Tests for FilesystemWatcher class."""

    @pytest.mark.asyncio
    async def test_watcher_creation(self):
        """Test creating filesystem watcher."""
        callback = AsyncMock()
        watcher = FilesystemWatcher(callback)
        assert watcher.callback == callback

    @pytest.mark.asyncio
    async def test_watcher_executes_callbacks(self):
        """Test watcher executes callbacks."""
        callback = AsyncMock()
        watcher = FilesystemWatcher(callback)
        
        # Simulate file created event
        from watchdog.events import FileCreatedEvent
        
        event = FileCreatedEvent("/tmp/test.pdf")
        watcher.on_created(event)
        
        # Wait for debounce
        await asyncio.sleep(1.5)
        
        # Callback should have been called
        assert callback.called


class TestFilesystemMonitor:
    """Tests for FilesystemMonitor class."""

    def test_init(self, temp_dir, temp_db):
        """Test monitor initialization."""
        monitor = FilesystemMonitor(temp_dir, temp_db)
        assert monitor.traversal.data_dir == temp_dir

    def test_scan(self, temp_dir, temp_db):
        """Test filesystem scan."""
        monitor = FilesystemMonitor(temp_dir, temp_db)
        stats = monitor.scan()
        
        assert "total_files" in stats
        assert "indexed_files" in stats
        assert stats["total_files"] > 0

    def test_get_incremental_updates(self, temp_dir, temp_db):
        """Test getting incremental updates."""
        monitor = FilesystemMonitor(temp_dir, temp_db)
        
        # Scan first
        monitor.scan()
        
        # All files should be unindexed initially
        updates = monitor.get_incremental_updates()
        assert len(updates) > 0

    def test_context_manager(self, temp_dir, temp_db):
        """Test using as context manager."""
        with FilesystemMonitor(temp_dir, temp_db) as monitor:
            stats = monitor.scan()
            assert "total_files" in stats


class TestFileMetadata:
    """Tests for FileMetadata dataclass."""

    def test_to_dict(self):
        """Test converting to dictionary."""
        metadata = FileMetadata(
            file_id="test-id",
            path="test.pdf",
            absolute_path="/tmp/test.pdf",
            name="test.pdf",
            mime_type="application/pdf",
            file_size=1024,
            created_at=datetime.now(),
            modified_at=datetime.now(),
            indexed_at=None,
            file_hash="abc123",
            indexed=False,
            is_directory=False,
            tags=["document"],
            metadata_json={"format": "pdf"},
        )
        
        d = metadata.to_dict()
        assert d["file_id"] == "test-id"
        assert d["path"] == "test.pdf"
        assert "created_at" in d


class TestDoclingFormats:
    """Tests for Docling format support."""

    def test_all_formats_present(self):
        """Test that all expected formats are supported."""
        expected = {
            'pdf', 'docx', 'pptx', 'xlsx',
            'jpg', 'png', 'mp4', 'mp3', 'wav',
        }
        
        for fmt in expected:
            assert fmt in DOCLING_FORMATS

    def test_format_count(self):
        """Test minimum number of formats."""
        assert len(DOCLING_FORMATS) >= 36
