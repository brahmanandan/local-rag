"""Logging configuration"""
import logging
import sys
from typing import Optional
from rich.logging import RichHandler
from rich.console import Console


def setup_logging(
    level: str = "INFO",
    log_file: Optional[str] = None,
    rich_tracebacks: bool = True
) -> logging.Logger:
    log_level = getattr(logging, level.upper(), logging.INFO)
    
    handlers = [
        RichHandler(
            console=Console(stderr=True),
            rich_tracebacks=rich_tracebacks,
            tracebacks_show_locals=True,
            markup=True
        )
    ]
    
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(
            logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
        )
        handlers.append(file_handler)
    
    logging.basicConfig(
        level=log_level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=handlers
    )
    
    return logging.getLogger("rag")
