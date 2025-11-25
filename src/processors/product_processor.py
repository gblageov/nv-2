"""
Product processing module for NikiVibes Image Processor.
"""
import logging
from typing import Dict, List, Set, Any, Optional
import pandas as pd
from ..config.config import Config


class ProductProcessor:
    """Handles processing of product data."""
    
    def __init__(self, config: Config):
        """
        Initialize the ProductProcessor.
        
        Args:
            config: Application configuration
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
    
    def process(self, products_df: pd.DataFrame) -> pd.DataFrame:
        """
        Process the products DataFrame.
        
        Args:
            products_df: DataFrame containing product data
            
        Returns:
            Processed DataFrame with additional columns
        """
        self.logger.info("Започва обработка на продуктите...")
        
        # Make a copy to avoid modifying the original DataFrame
        df = products_df.copy()
        
        # Add a column to track original row indices
        df['_original_index'] = df.index
        
        # Ensure required columns exist
        required_columns = [
            self.config.handle_column,
            self.config.variant_images_column,
            self.config.image_src_column,
            self.config.image_alt_text_column,
            self.config.option1_value_column
        ]
        
        for col in required_columns:
            if col not in df.columns:
                df[col] = ''
                self.logger.warning(f"Липсва колона '{col}'. Добавена е празна колона.")
        
        self.logger.info(f"Обработени {len(df)} продукта")
        return df
    
    def get_unique_image_ids(self, df: pd.DataFrame) -> Dict[str, Set[str]]:
        """
        Get unique image IDs for each product handle.
        
        Args:
            df: Processed products DataFrame
            
        Returns:
            Dictionary mapping handles to sets of unique image IDs
        """
        self.logger.info("Извличане на уникални ID на изображения...")
        image_ids = {}
        
        for _, row in df.iterrows():
            handle = str(row[self.config.handle_column])
            variant_images = str(row.get(self.config.variant_images_column, ''))
            
            # Skip empty or NaN values
            if not variant_images or variant_images.lower() == 'nan' or variant_images.lower() == 'none':
                continue
                
            # Split the comma-separated IDs and clean them up
            ids = [str(id_).strip() for id_ in variant_images.split(',') if str(id_).strip().isdigit()]
            
            # Add to the dictionary
            if handle not in image_ids:
                image_ids[handle] = set()
            image_ids[handle].update(ids)
        
        self.logger.info(f"Намерени {len(image_ids)} продукта с изображения")
        return image_ids
    
    def prepare_product_rows(self, handle: str, image_ids: Set[str], product_data: pd.Series) -> List[Dict[str, Any]]:
        """
        Prepare product rows for each image ID.
        
        Args:
            handle: Product handle
            image_ids: Set of image IDs for the product
            product_data: Original product data
            
        Returns:
            List of dictionaries representing product rows
        """
        rows = []
        base_data = product_data.to_dict()
        
        # Keep track of the original row
        if image_ids:
            for img_id in image_ids:
                row = base_data.copy()
                row[self.config.variant_images_column] = img_id
                rows.append(row)
        else:
            # If no image IDs, keep the original row
            rows.append(base_data)
            
        return rows
