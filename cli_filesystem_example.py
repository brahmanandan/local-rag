#!/usr/bin/env python
"""
CLI example demonstrating filesystem traversal and metadata tracking.

Usage:
    python cli_filesystem_example.py --scan ./rag-data/data
    python cli_filesystem_example.py --watch ./rag-data/data
    python cli_filesystem_example.py --stats ./rag-data/data
    python cli_filesystem_example.py --changes ./rag-data/data
"""

import asyncio
import logging
from pathlib import Path
from typing import Optional
from datetime import datetime

import typer
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, BarColumn
from rich.logging import RichHandler

from src.ingestion.filesystem import (
    FilesystemMonitor,
    FilesystemTraversal,
    MetadataTracker,
    FileChangeType,
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[RichHandler(rich_tracebacks=True)]
)
logger = logging.getLogger(__name__)

# Rich console for output
console = Console()

app = typer.Typer(help="Filesystem & Metadata Management CLI")


@app.command()
def scan(
    data_dir: Path = typer.Argument(
        ...,
        help="Directory to scan",
        exists=True,
        file_okay=False,
        dir_okay=True,
    ),
    extensions: Optional[str] = typer.Option(
        None,
        "--ext",
        help="Comma-separated extensions to filter (e.g., pdf,docx,txt)"
    ),
    db_path: Path = typer.Option(
        Path(".rag_metadata.db"),
        "--db",
        help="Path to metadata database"
    ),
):
    """Scan directory and index files."""
    console.print(f"[bold blue]Scanning:[/bold blue] {data_dir}")
    
    # Parse extensions
    ext_set = None
    if extensions:
        ext_set = set(ext.strip().lower() for ext in extensions.split(","))
    
    # Create monitor
    monitor = FilesystemMonitor(data_dir, db_path)
    
    # Scan with progress
    with Progress(
        SpinnerColumn(),
        BarColumn(),
        "[progress.description]{task.description}",
        console=console,
    ) as progress:
        task = progress.add_task("Scanning files...", total=None)
        
        # Traverse filesystem
        traversal = monitor.traversal
        files = traversal.traverse(extensions=ext_set)
        
        progress.update(task, total=len(files), completed=0)
        
        # Store in database
        for i, metadata in enumerate(files):
            monitor.tracker.upsert_file(metadata)
            progress.update(task, advance=1)
    
    # Show statistics
    stats = monitor.tracker.get_statistics()
    
    console.print("\n[bold green]✓ Scan Complete[/bold green]\n")
    
    stats_table = Table(title="Scan Statistics", show_header=True)
    stats_table.add_column("Metric", style="cyan")
    stats_table.add_column("Value", style="green")
    
    stats_table.add_row("Total Files", str(stats["total_files"]))
    stats_table.add_row("Indexed", str(stats["indexed_files"]))
    stats_table.add_row("Unindexed", str(stats["unindexed_files"]))
    stats_table.add_row("Total Size", f"{stats['total_size_bytes'] / 1024 / 1024:.1f} MB")
    stats_table.add_row("MIME Types", str(stats["unique_mime_types"]))
    stats_table.add_row("Indexing %", f"{stats['indexing_percentage']:.1f}%")
    
    console.print(stats_table)
    console.print(f"\nDatabase: [blue]{db_path}[/blue]")


@app.command()
def list_files(
    data_dir: Path = typer.Argument(
        ...,
        help="Directory to list",
        exists=True,
        file_okay=False,
        dir_okay=True,
    ),
    indexed_only: bool = typer.Option(
        False,
        "--indexed",
        help="Show only indexed files"
    ),
    unindexed_only: bool = typer.Option(
        False,
        "--unindexed",
        help="Show only unindexed files"
    ),
    limit: int = typer.Option(
        50,
        "--limit",
        help="Maximum files to display"
    ),
    db_path: Path = typer.Option(
        Path(".rag_metadata.db"),
        "--db",
        help="Path to metadata database"
    ),
):
    """List files in database."""
    import sqlite3
    
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        
        # Build query
        query = "SELECT * FROM files"
        
        if indexed_only:
            query += " WHERE indexed = 1"
        elif unindexed_only:
            query += " WHERE indexed = 0"
        
        query += f" LIMIT {limit}"
        
        cursor = conn.execute(query)
        files = cursor.fetchall()
    
    # Display in table
    table = Table(title=f"Files ({len(files)} shown)")
    table.add_column("Name", style="cyan")
    table.add_column("Path", style="blue")
    table.add_column("Size", style="yellow")
    table.add_column("Type", style="magenta")
    table.add_column("Indexed", style="green")
    
    for file_row in files:
        indexed_str = "✓" if file_row["indexed"] else "✗"
        size_str = f"{file_row['file_size'] / 1024:.1f} KB"
        
        table.add_row(
            file_row["name"],
            file_row["path"][:40],
            size_str,
            file_row["mime_type"] or "unknown",
            indexed_str,
        )
    
    console.print(table)


@app.command()
def stats(
    data_dir: Path = typer.Argument(
        ...,
        help="Directory to analyze",
        exists=True,
        file_okay=False,
        dir_okay=True,
    ),
    db_path: Path = typer.Option(
        Path(".rag_metadata.db"),
        "--db",
        help="Path to metadata database"
    ),
):
    """Show detailed statistics."""
    monitor = FilesystemMonitor(data_dir, db_path)
    
    # If database doesn't exist, scan first
    if not db_path.exists():
        console.print("[yellow]Database not found. Scanning...[/yellow]")
        monitor.scan()
    
    stats = monitor.tracker.get_statistics()
    
    # Overview
    console.print("\n[bold]📊 Filesystem Statistics[/bold]\n")
    
    overview_table = Table(show_header=False)
    overview_table.add_row("Total Files:", f"[green]{stats['total_files']}[/green]")
    overview_table.add_row("Indexed:", f"[green]{stats['indexed_files']}[/green]")
    overview_table.add_row("Pending:", f"[yellow]{stats['unindexed_files']}[/yellow]")
    overview_table.add_row("Total Size:", f"[blue]{stats['total_size_bytes'] / 1024 / 1024:.1f} MB[/blue]")
    overview_table.add_row("MIME Types:", f"[cyan]{stats['unique_mime_types']}[/cyan]")
    
    console.print(overview_table)
    
    # Progress
    indexed_pct = stats['indexing_percentage']
    bar_length = 30
    filled = int(bar_length * indexed_pct / 100)
    bar = "█" * filled + "░" * (bar_length - filled)
    
    console.print(f"\nIndexing Progress: [green]{bar}[/green] {indexed_pct:.1f}%\n")


@app.command()
def watch(
    data_dir: Path = typer.Argument(
        ...,
        help="Directory to watch",
        exists=True,
        file_okay=False,
        dir_okay=True,
    ),
    db_path: Path = typer.Option(
        Path(".rag_metadata.db"),
        "--db",
        help="Path to metadata database"
    ),
):
    """Watch directory for changes."""
    console.print(f"[bold blue]Watching:[/bold blue] {data_dir}")
    console.print("[yellow]Press Ctrl+C to stop[/yellow]\n")
    
    change_count = 0
    
    async def on_change(file_path: Path, change_type: FileChangeType):
        nonlocal change_count
        change_count += 1
        
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # Determine emoji
        emoji = {
            FileChangeType.CREATED: "✨",
            FileChangeType.MODIFIED: "📝",
            FileChangeType.DELETED: "🗑️",
        }.get(change_type, "📋")
        
        console.print(
            f"[dim]{timestamp}[/dim] {emoji} {change_type.value:8} [cyan]{file_path.name}[/cyan]"
        )
        
        # Record change
        tracker = MetadataTracker(db_path)
        file_id = FilesystemTraversal.compute_path_hash(file_path)
        tracker.record_change(
            file_id=file_id,
            path=str(file_path),
            change_type=change_type,
        )
    
    # Create monitor with watching
    monitor = FilesystemMonitor(data_dir, db_path, watch=True)
    monitor.set_change_callback(on_change)
    
    try:
        with monitor:
            # Initial scan
            stats = monitor.scan()
            console.print(f"[green]Indexed {stats['total_files']} files[/green]\n")
            
            # Keep watching
            while True:
                asyncio.sleep(1)
    except KeyboardInterrupt:
        console.print(f"\n[yellow]Stopped. Detected {change_count} changes[/yellow]")


@app.command()
def changes(
    data_dir: Path = typer.Argument(
        ...,
        help="Directory context",
        exists=True,
        file_okay=False,
        dir_okay=True,
    ),
    db_path: Path = typer.Option(
        Path(".rag_metadata.db"),
        "--db",
        help="Path to metadata database"
    ),
    process: bool = typer.Option(
        False,
        "--process",
        help="Mark all changes as processed"
    ),
):
    """Show unprocessed file changes."""
    tracker = MetadataTracker(db_path)
    changes_list = tracker.get_unprocessed_changes()
    
    if not changes_list:
        console.print("[green]✓ No unprocessed changes[/green]")
        return
    
    # Display changes
    table = Table(title="Unprocessed Changes")
    table.add_column("ID", style="cyan")
    table.add_column("Path", style="blue")
    table.add_column("Type", style="yellow")
    table.add_column("Detected", style="magenta")
    
    for change in changes_list:
        table.add_row(
            str(change["id"]),
            change["path"][:40],
            change["change_type"],
            change["detected_at"][:19],
        )
    
    console.print(table)
    
    # Process if requested
    if process:
        console.print(f"\n[bold]Processing {len(changes_list)} changes...[/bold]")
        
        for change in changes_list:
            tracker.mark_change_processed(change["id"])
            console.print(f"  ✓ {change['path']}")
        
        console.print(f"\n[green]✓ All changes processed[/green]")


@app.command()
def clean(
    db_path: Path = typer.Option(
        Path(".rag_metadata.db"),
        "--db",
        help="Path to metadata database"
    ),
    confirm: bool = typer.Option(
        False,
        "--yes",
        help="Skip confirmation"
    ),
):
    """Clean metadata database."""
    if not db_path.exists():
        console.print("[yellow]Database not found[/yellow]")
        return
    
    if not confirm:
        console.print(f"[yellow]Delete {db_path}?[/yellow]")
        if not typer.confirm("Continue?"):
            console.print("[yellow]Cancelled[/yellow]")
            return
    
    db_path.unlink()
    console.print(f"[green]✓ Deleted {db_path}[/green]")


@app.command()
def formats():
    """Show supported file formats."""
    from src.ingestion.filesystem import DOCLING_FORMATS
    
    console.print("\n[bold]📄 Supported Formats ({}):[/bold]\n".format(len(DOCLING_FORMATS)))
    
    # Categorize formats
    documents = [f for f in DOCLING_FORMATS if f in {'pdf', 'docx', 'doc', 'pptx', 'ppt', 'xlsx', 'xls', 'html', 'htm', 'txt', 'md', 'markdown', 'rst', 'latex', 'tex', 'xml', 'json', 'asciidoc', 'adoc'}]
    images = [f for f in DOCLING_FORMATS if f in {'jpg', 'jpeg', 'png', 'gif', 'bmp', 'tiff', 'tif', 'webp'}]
    videos = [f for f in DOCLING_FORMATS if f in {'mp4', 'avi', 'mov', 'mkv', 'flv', 'wmv', 'webm', 'm4v'}]
    audio = [f for f in DOCLING_FORMATS if f in {'mp3', 'wav', 'aac', 'flac', 'm4a', 'ogg', 'wma', 'opus'}]
    
    console.print("[cyan]📋 Documents:[/cyan]")
    console.print(f"  {', '.join(sorted(documents))}\n")
    
    console.print("[green]🖼️  Images:[/green]")
    console.print(f"  {', '.join(sorted(images))}\n")
    
    console.print("[blue]🎬 Videos:[/blue]")
    console.print(f"  {', '.join(sorted(videos))}\n")
    
    console.print("[magenta]🔊 Audio:[/magenta]")
    console.print(f"  {', '.join(sorted(audio))}\n")


if __name__ == "__main__":
    app()
