"""
NikiVibes Image Processor - Main Application
"""
import sys
import logging
from pathlib import Path
from typing import Optional
import pandas as pd
from openpyxl.utils import get_column_letter
import re

# Add the src directory to the Python path
sys.path.append(str(Path(__file__).parent))

from src.config import load_config
from src.gui import NikiVibesGUI
from src.utils.file_utils import create_directory


def setup_logging(config) -> logging.Logger:
    """
    Set up logging configuration.
    
    Args:
        config: Application configuration
        
    Returns:
        Configured logger instance
    """
    # Create log directory if it doesn't exist
    create_directory(config.log_dir)
    
    # Configure root logger
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    # Clear any existing handlers to avoid duplicate logs
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Create formatter with timestamp and log level
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Add file handler
    file_handler = logging.FileHandler(config.log_file_path, encoding='utf-8')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # Add console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    return logger

def process_files(config):
    """
    Process the files (this will be called from the GUI).
    
    Args:
        config: Application configuration
    """
    # Import here to avoid circular imports
    from src.utils.file_utils import read_excel_file, backup_file
    from src.processors.product_processor import ProductProcessor
    from src.processors.image_processor import ImageProcessor

    logger = logging.getLogger(__name__)
    
    try:
        logger.info("Започва обработка на файловете...")
        
        # Create backup of input file
        try:
            backup_path = backup_file(config.input_file_path, config.backup_dir)
            logger.info(f"Създаден е архив на входния файл: {backup_path}")
        except Exception as e:
            logger.warning(f"Неуспешно създаване на архив на входния файл: {e}")
        
        # Read input files
        logger.info(f"Четене на входен файл: {config.input_file_path}")
        products_df = read_excel_file(
            config.input_file_path,
            sheet_name=config.products_sheet_name
        )
        
        logger.info(f"Четене на файл с медии: {config.media_export_path}")
        media_export_df = read_excel_file(config.media_export_path)
        
        # Process products
        logger.info("Започва обработка на продуктите...")
        product_processor = ProductProcessor(config)
        processed_products = product_processor.process(products_df)
        
        # Process images
        logger.info("Започва обработка на изображенията...")
        image_processor = ImageProcessor(config)
        result_df = image_processor.process(processed_products, media_export_df)
        
        # Save results
        output_path = config.output_dir / config.output_filename
        create_directory(config.output_dir)  # Ensure output directory exists
        
        logger.info(f"Запазване на резултатите във файл: {output_path}")
        
        # Detect Top Row column by normalized name
        def norm(name: str):
            return re.sub(r"[^a-z]", "", str(name).lower())
        top_col = None
        for col in list(result_df.columns):
            if norm(col) == 'toprow':
                top_col = col
                break

        # If Top Row exists: keep TRUE only on first row per product (by Handle), others blank
        if top_col is not None and config.handle_column in result_df.columns:
            # Normalize existing values to decide the first-row value
            def is_truthy(val):
                if isinstance(val, str):
                    v = val.strip().lower()
                    return v in {'true', '1', 'yes', 'y'}
                return bool(val)

            # Consider only rows with a non-empty handle as product rows
            handle_series = result_df[config.handle_column].astype(str).fillna('')
            product_mask = handle_series.str.strip() != ''

            # First, blank Top Row on all non-product rows (blank handle, message rows, etc.)
            result_df.loc[~product_mask, top_col] = ''

            # Apply per-handle only on product rows
            for handle, grp in result_df.loc[product_mask].groupby(config.handle_column, sort=False):
                idxs = list(grp.index)
                if not idxs:
                    continue
                first_idx = idxs[0]
                first_val = result_df.at[first_idx, top_col]
                # Set first row
                result_df.at[first_idx, top_col] = 'TRUE' if is_truthy(first_val) else ''
                # Blank all subsequent rows for this handle
                if len(idxs) > 1:
                    result_df.loc[idxs[1:], top_col] = ''

        # Convert other boolean dtype columns (excluding Top Row) to 'TRUE'/'FALSE'
        bool_cols = list(result_df.select_dtypes(include=['bool']).columns)
        if top_col in bool_cols:
            bool_cols.remove(top_col)
        for col in bool_cols:
            result_df[col] = result_df[col].map({True: 'TRUE', False: 'FALSE'})
        
        # Write to Excel with openpyxl engine
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            result_df.to_excel(writer, index=False, sheet_name='Products')
            
            # Set column widths for better readability
            worksheet = writer.sheets['Products']
            for idx, col in enumerate(result_df.columns):
                # Get the maximum length of the column
                max_length = max(
                    result_df[col].astype(str).apply(len).max(),
                    len(str(col))  # Length of column name
                )
                # Compute proper Excel column letter (A, B, ..., Z, AA, AB, ...)
                col_letter = get_column_letter(idx + 1)
                # Set column width (add a little extra space)
                worksheet.column_dimensions[col_letter].width = min(max_length + 2, 50)
        
        logger.info(f"Обработката завърши успешно. Резултатите са запазени в: {output_path}")
        return True
        
    except Exception as e:
        error_msg = f"Грешка при обработка на файловете: {str(e)}"
        logger.exception(error_msg)
        raise Exception(error_msg) from e

def main() -> int:
    """
    Main entry point for the application.
    
    Returns:
        int: Exit code (0 for success, 1 for error)
    """
    try:
        # Load configuration
        config = load_config()
        
        # Setup logging
        logger = setup_logging(config)
        logger.info("Стартиране на NikiVibes Image Processor")
        
        # Log configuration
        logger.info(f"Конфигурация: {vars(config)}")
        
        # Create and run the GUI
        app = NikiVibesGUI(config, process_files)
        app.run()
        
        logger.info("Приключване на програмата")
        return 0
        
    except Exception as e:
        error_msg = f"Възникна фатална грешка: {str(e)}"
        logging.exception(error_msg)
        
        # Try to log to console if logging setup failed
        print(f"\nГРЕШКА: {error_msg}")
        print(f"Допълнителна информация в лог файла: {getattr(config, 'log_file_path', 'неизвестен')}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
