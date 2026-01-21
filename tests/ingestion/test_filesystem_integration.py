"""Integration tests for filesystem and metadata system."""

import asyncio
import tempfile
import pytest
from pathlib import Path
from datetime import datetime

from src.ingestion.filesystem import (
    FilesystemMonitor,
    FilesystemTraversal,
    MetadataTracker,
    FileChangeType,
)


@pytest.fixture
def integration_dir():
    """Create a realistic directory structure for integration tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        
        # Create document hierarchy
        docs = tmppath / "Documents"
        docs.mkdir()
        (docs / "report.pdf").write_text("PDF content")
        (docs / "presentation.pptx").write_text("PPTX content")
        
        research = docs / "Research"
        research.mkdir()
        (research / "paper1.pdf").write_text("Paper 1")
        (research / "paper2.pdf").write_text("Paper 2")
        
        # Create media hierarchy
        media = tmppath / "Media"
        media.mkdir()
        (media / "image1.png").write_bytes(b"PNG")
        (media / "image2.jpg").write_bytes(b"JPG")
        (media / "video.mp4").write_bytes(b"MP4")
        (media / "audio.mp3").write_bytes(b"MP3")
        
        # Create mixed files
        (tmppath / "notes.md").write_text("# Notes")
        (tmppath / "data.json").write_text('{"key": "value"}')
        (tmppath / "README.txt").write_text("README")
        
        yield tmppath


class TestFilesystemIntegration:
    """Integration tests for filesystem traversal."""

    def test_complete_traversal(self, integration_dir):
        """Test complete directory traversal."""
        traversal = FilesystemTraversal(integration_dir)
        files = traversal.traverse()
        
        # Should find all supported files
        assert len(files) >= 10
        
        # Check various file types are found
        names = {f.name for f in files}
        assert "report.pdf" in names
        assert "presentation.pptx" in names
        assert "image1.png" in names
        assert "audio.mp3" in names
        assert "notes.md" in names
        assert "data.json" in names

    def test_nested_structure_traversal(self, integration_dir):
        """Test traversing nested directory structure."""
        traversal = FilesystemTraversal(integration_dir)
        files = traversal.traverse()
        
        # Should find files in nested directories
        paths = {f.path for f in files}
        
        # Check for nested paths
        pdf_in_research = any("Research" in p and "pdf" in p for p in paths)
        assert pdf_in_research

    def test_mime_type_detection(self, integration_dir):
        """Test MIME type detection across various files."""
        traversal = FilesystemTraversal(integration_dir)
        files = traversal.traverse()
        
        mime_types = {f.mime_type for f in files if f.mime_type}
        
        # Should detect various MIME types
        assert len(mime_types) > 0
        # Note: Some files might not be recognized due to content


class TestMetadataTrackingIntegration:
    """Integration tests for metadata tracking."""

    def test_full_tracking_workflow(self, integration_dir):
        """Test complete metadata tracking workflow."""
        db_path = integration_dir / ".metadata.db"
        
        # Initialize tracker
        tracker = MetadataTracker(db_path)
        traversal = FilesystemTraversal(integration_dir)
        
        # Extract metadata
        files = traversal.traverse()
        
        # Store metadata
        for f in files:
            tracker.upsert_file(f)
        
        # Verify storage
        stats = tracker.get_statistics()
        assert stats["total_files"] == len(files)
        assert stats["indexed_files"] == 0  # Not indexed yet

    def test_incremental_indexing(self, integration_dir):
        """Test incremental indexing workflow."""
        db_path = integration_dir / ".metadata.db"
        
        tracker = MetadataTracker(db_path)
        traversal = FilesystemTraversal(integration_dir)
        
        # First scan
        files = traversal.traverse()
        for f in files:
            tracker.upsert_file(f)
        
        # Mark some as indexed
        indexed_files = files[:3]
        for f in indexed_files:
            tracker.mark_indexed(f.file_id)
        
        # Verify status
        stats = tracker.get_statistics()
        assert stats["indexed_files"] == 3
        assert stats["unindexed_files"] == len(files) - 3

    def test_change_tracking(self, integration_dir):
        """Test tracking file changes."""
        db_path = integration_dir / ".metadata.db"
        
        tracker = MetadataTracker(db_path)
        traversal = FilesystemTraversal(integration_dir)
        
        # Initial scan
        files = traversal.traverse()
        for f in files:
            tracker.upsert_file(f)
        
        # Record some changes
        for i, f in enumerate(files[:2]):
            change_type = FileChangeType.MODIFIED if i == 0 else FileChangeType.DELETED
            tracker.record_change(f.file_id, f.path, change_type)
        
        # Verify changes recorded
        changes = tracker.get_unprocessed_changes()
        assert len(changes) == 2

    def test_change_processing(self, integration_dir):
        """Test processing recorded changes."""
        db_path = integration_dir / ".metadata.db"
        
        tracker = MetadataTracker(db_path)
        traversal = FilesystemTraversal(integration_dir)
        
        # Setup
        files = traversal.traverse()
        for f in files:
            tracker.upsert_file(f)
        
        # Record changes
        for f in files[:3]:
            tracker.record_change(f.file_id, f.path, FileChangeType.MODIFIED)
        
        # Process changes
        changes = tracker.get_unprocessed_changes()
        initial_count = len(changes)
        
        for change in changes:
            tracker.mark_change_processed(change["id"])
        
        # Verify all processed
        unprocessed = tracker.get_unprocessed_changes()
        assert len(unprocessed) == 0


class TestFilesystemMonitorIntegration:
    """Integration tests for filesystem monitor."""

    def test_monitor_scan_and_statistics(self, integration_dir):
        """Test monitor scan and statistics."""
        db_path = integration_dir / ".metadata.db"
        
        monitor = FilesystemMonitor(integration_dir, db_path)
        stats = monitor.scan()
        
        assert stats["total_files"] > 0
        assert "indexed_files" in stats
        assert "unindexed_files" in stats
        assert "indexing_percentage" in stats

    def test_incremental_updates_workflow(self, integration_dir):
        """Test incremental updates workflow."""
        db_path = integration_dir / ".metadata.db"
        
        monitor = FilesystemMonitor(integration_dir, db_path)
        
        # First scan
        monitor.scan()
        
        # Get incremental updates
        updates = monitor.get_incremental_updates()
        
        # Should have updates for unindexed files
        assert len(updates) > 0
        
        # Mark first file as indexed
        if updates:
            first_file_id = updates[0].get("file_id")
            if first_file_id:
                monitor.tracker.mark_indexed(first_file_id)
        
        # Check statistics changed
        stats = monitor.tracker.get_statistics()
        assert stats["indexed_files"] > 0

    def test_context_manager_workflow(self, integration_dir):
        """Test using monitor as context manager."""
        db_path = integration_dir / ".metadata.db"
        
        with FilesystemMonitor(integration_dir, db_path) as monitor:
            stats = monitor.scan()
            assert "total_files" in stats
            
            updates = monitor.get_incremental_updates()
            assert isinstance(updates, list)


class TestFilesystemScenarios:
    """Test realistic filesystem scenarios."""

    def test_large_directory_structure(self, integration_dir):
        """Test handling large directory structures."""
        # Create many files
        for i in range(20):
            (integration_dir / f"document_{i}.pdf").write_text(f"PDF {i}")
        
        traversal = FilesystemTraversal(integration_dir)
        files = traversal.traverse()
        
        assert len(files) >= 20

    def test_mixed_supported_unsupported_files(self, integration_dir):
        """Test handling mix of supported and unsupported files."""
        # Add unsupported files
        (integration_dir / "archive.zip").write_bytes(b"ZIP")
        (integration_dir / "executable.exe").write_bytes(b"EXE")
        (integration_dir / "unknown.xyz").write_bytes(b"XYZ")
        
        traversal = FilesystemTraversal(integration_dir)
        files = traversal.traverse()
        
        # Should not include unsupported files
        names = {f.name for f in files}
        assert "archive.zip" not in names
        assert "executable.exe" not in names
        assert "unknown.xyz" not in names

    def test_special_characters_in_filenames(self, integration_dir):
        """Test handling files with special characters."""
        special_names = [
            "file with spaces.pdf",
            "file-with-dashes.docx",
            "file_with_underscores.txt",
        ]
        
        for name in special_names:
            (integration_dir / name).write_text("content")
        
        traversal = FilesystemTraversal(integration_dir)
        files = traversal.traverse()
        
        found_names = {f.name for f in files}
        for name in special_names:
            assert name in found_names

    def test_empty_directories(self, integration_dir):
        """Test handling empty directories."""
        # Create empty directory structure
        (integration_dir / "empty1").mkdir()
        (integration_dir / "empty1" / "empty2").mkdir()
        
        traversal = FilesystemTraversal(integration_dir)
        files = traversal.traverse()
        
        # Should not include directories, only files
        for f in files:
            assert not f.is_directory


class TestFileHashingConsistency:
    """Test file hashing consistency."""

    def test_hash_consistency(self, integration_dir):
        """Test that hashing is consistent."""
        file_path = integration_dir / "test.pdf"
        file_path.write_text("content")
        
        hash1 = FilesystemTraversal.compute_file_hash(file_path)
        hash2 = FilesystemTraversal.compute_file_hash(file_path)
        
        assert hash1 == hash2

    def test_different_content_different_hash(self, integration_dir):
        """Test that different content produces different hashes."""
        file1 = integration_dir / "file1.pdf"
        file2 = integration_dir / "file2.pdf"
        
        file1.write_text("content 1")
        file2.write_text("content 2")
        
        hash1 = FilesystemTraversal.compute_file_hash(file1)
        hash2 = FilesystemTraversal.compute_file_hash(file2)
        
        assert hash1 != hash2

    def test_path_hash_uniqueness(self, integration_dir):
        """Test that path hashes are unique."""
        paths = [
            integration_dir / "file1.pdf",
            integration_dir / "file2.pdf",
            integration_dir / "subdir" / "file1.pdf",
        ]
        
        (integration_dir / "subdir").mkdir(exist_ok=True)
        
        hashes = set()
        for p in paths:
            h = FilesystemTraversal.compute_path_hash(p)
            assert h not in hashes
            hashes.add(h)
