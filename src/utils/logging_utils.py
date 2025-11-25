"""
Logging utilities for the NikiVibes Image Processor.
"""
import logging
from pathlib import Path
from typing import Optional


def setup_logger(
    name: str,
    log_file: Optional[Path] = None,
    log_level: str = "INFO",
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
) -> logging.Logger:
    """
    Set up and configure a logger.
    
    Args:
        name: Logger name
        log_file: Path to the log file (if None, logs only to console)
        log_level: Logging level (default: INFO)
        log_format: Log message format
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    
    # Convert string log level to logging constant
    level = getattr(logging, log_level.upper(), logging.INFO)
    logger.setLevel(level)
    
    # Create formatter
    formatter = logging.Formatter(log_format)
    
    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    
    # Add console handler to logger
    logger.addHandler(console_handler)
    
    # Create file handler if log file is specified
    if log_file:
        # Ensure the log directory exists
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger
