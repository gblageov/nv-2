"""
File utility functions for the NikiVibes Image Processor.
"""
import os
import shutil
from pathlib import Path
from typing import Optional, Union, List
import pandas as pd
from ..config.config import Config


def create_directory(directory: Union[str, Path]) -> Path:
    """
    Create a directory if it doesn't exist.
    
    Args:
        directory: Path to the directory to create
        
    Returns:
        Path: The path to the created directory
    """
    path = Path(directory)
    path.mkdir(parents=True, exist_ok=True)
    return path


def generate_output_filename(input_path: Union[str, Path], suffix: str = "") -> str:
    """
    Generate an output filename with optional suffix and timestamp.
    
    Args:
        input_path: Path to the input file
        suffix: Optional suffix to add before the extension
        
    Returns:
        str: Generated output filename
    """
    path = Path(input_path)
    name_parts = path.stem.split('.')
    timestamp = pd.Timestamp.now().strftime(Config().date_format)
    
    if suffix:
        return f"{name_parts[0]}-{suffix}-{timestamp}{path.suffix}"
    return f"{name_parts[0]}-{timestamp}{path.suffix}"


def read_excel_file(file_path: Union[str, Path], sheet_name: str = None) -> pd.DataFrame:
    """
    Read an Excel file into a pandas DataFrame.
    
    Args:
        file_path: Path to the Excel file
        sheet_name: Name of the sheet to read (if None, reads the first sheet)
        
    Returns:
        pd.DataFrame: The data from the Excel file
    """
    try:
        if sheet_name:
            return pd.read_excel(file_path, sheet_name=sheet_name, engine='openpyxl')
        return pd.read_excel(file_path, engine='openpyxl')
    except Exception as e:
        raise Exception(f"Error reading Excel file {file_path}: {str(e)}")


def save_to_excel(df: pd.DataFrame, file_path: Union[str, Path], sheet_name: str = "Sheet1") -> None:
    """
    Save a DataFrame to an Excel file.
    
    Args:
        df: DataFrame to save
        file_path: Path where to save the Excel file
        sheet_name: Name of the sheet
    """
    try:
        df.to_excel(file_path, sheet_name=sheet_name, index=False, engine='openpyxl')
    except Exception as e:
        raise Exception(f"Error saving to Excel file {file_path}: {str(e)}")


def backup_file(file_path: Union[str, Path], backup_dir: Optional[Union[str, Path]] = None) -> Path:
    """
    Create a backup of a file.
    
    Args:
        file_path: Path to the file to back up
        backup_dir: Directory to store the backup (default: 'backup' in the same directory)
        
    Returns:
        Path: Path to the backup file
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File {file_path} does not exist")
    
    if backup_dir is None:
        backup_dir = path.parent / "backup"
    
    backup_dir = create_directory(backup_dir)
    backup_path = backup_dir / f"{path.stem}_backup_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}{path.suffix}"
    
    shutil.copy2(path, backup_path)
    return backup_path