"""
Configuration settings and constants for NikiVibes Image Processor
"""
import os
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass
from typing import Dict, List, Optional

@dataclass
class Config:
    """Main configuration class for the application"""
    # File paths
    base_dir: Path = Path(__file__).parent.parent.parent
    input_dir: Path = base_dir / "data"
    output_dir: Path = base_dir / "data" / "processed"
    log_dir: Path = base_dir / "logs"
    backup_dir: Path = base_dir / "backup"
    media_export_path_full: Optional[Path] = None
    
    # File names
    input_filename: str = "products.xlsx"
    media_export_filename: str = "nikivibes media export.xlsx"
    
    # Sheet and column names
    products_sheet_name: str = "Products"
    handle_column: str = "Handle"
    variant_images_column: str = "Variant Metafield: woo._wc_additional_variation_images"
    image_src_column: str = "Image Src"
    image_alt_text_column: str = "Image Alt Text"
    option1_value_column: str = "Option1 Value"
    
    # Media export file columns
    media_id_column: str = "ID"
    media_url_column: str = "URL"
    media_alt_column: str = "Alt"
    
    # Logging
    log_level: str = "INFO"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Output settings
    date_format: str = "%d-%m-%Y-%H-%M-%S"
    
    @property
    def input_file_path(self) -> Path:
        """Get the full path to the input file"""
        return self.input_dir / self.input_filename
    
    @input_file_path.setter
    def input_file_path(self, value: Path):
        """Set the input file path and update input_dir and input_filename"""
        value = Path(value)
        self.input_dir = value.parent
        self.input_filename = value.name
    
    @property
    def media_export_path(self) -> Path:
        """Get the full path to the media export file"""
        return self.base_dir / self.media_export_filename
        
    @media_export_path.setter
    def media_export_path(self, value: Path):
        """Set the media export file path and update media_export_filename"""
        value = Path(value)
        self.media_export_filename = value.name
        if value.parent != self.base_dir:
            self.media_export_path_full = value
    
    @property
    def output_filename(self) -> str:
        """Generate output filename with timestamp"""
        timestamp = datetime.now().strftime(self.date_format)
        name, ext = os.path.splitext(self.input_filename)
        return f"{name}-{timestamp}{ext}"
    
    @property
    def output_file_path(self) -> Path:
        """Get the full path to the output file"""
        return self.output_dir / self.output_filename
    
    @property
    def log_file_path(self) -> Path:
        """Get the full path to the log file"""
        timestamp = datetime.now().strftime("%Y%m%d")
        return self.log_dir / f"nikivibes_processor_{timestamp}.log"


def load_config(env_path: Optional[Path] = None) -> Config:
    """
    Load configuration from environment variables and return a Config instance.
    
    Args:
        env_path: Optional path to .env file. If None, looks for .env in base directory.
    """
    from dotenv import load_dotenv
    
    # Load environment variables from .env file
    if env_path is None:
        env_path = Config().base_dir / ".env"
    
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
    
    config = Config()
    
    # Update configuration from environment variables if they exist
    if os.getenv('INPUT_DIR'):
        config.input_dir = Path(os.getenv('INPUT_DIR'))
    if os.getenv('OUTPUT_DIR'):
        config.output_dir = Path(os.getenv('OUTPUT_DIR'))
    if os.getenv('LOG_DIR'):
        config.log_dir = Path(os.getenv('LOG_DIR'))
    if os.getenv('LOG_LEVEL'):
        config.log_level = os.getenv('LOG_LEVEL', 'INFO')
    
    # Create necessary directories
    for directory in [config.input_dir, config.output_dir, config.log_dir]:
        directory.mkdir(parents=True, exist_ok=True)
    
    return config
