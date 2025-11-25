"""
Image processing module for NikiVibes Image Processor.
"""
import logging
from typing import Dict, List, Any, Optional
import pandas as pd
from pathlib import Path
from ..config.config import Config


class ImageProcessor:
    """Handles processing of image data."""
    
    def __init__(self, config: Config):
        """
        Initialize the ImageProcessor.
        
        Args:
            config: Application configuration
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.media_cache = {}
    
    def _build_media_cache(self, media_export_df: pd.DataFrame) -> None:
        """
        Build a cache of media data for faster lookups.
        
        Args:
            media_export_df: DataFrame containing media export data
        """
        self.media_cache = {}
        if not media_export_df.empty:
            for _, row in media_export_df.iterrows():
                media_id = str(row.get(self.config.media_id_column, '')).strip()
                if media_id and media_id.isdigit():
                    self.media_cache[media_id] = {
                        'url': str(row.get(self.config.media_url_column, '')),
                        'alt': str(row.get(self.config.media_alt_column, ''))
                    }
    
    def process(self, products_df: pd.DataFrame, media_export_df: pd.DataFrame) -> pd.DataFrame:
        """
        Process the images for products.
        
        Args:
            products_df: Processed products DataFrame
            media_export_df: DataFrame containing media export data
            
        Returns:
            DataFrame with processed image data
        """
        self.logger.info("Започва обработка на изображения...")
        
        # Build media cache for faster lookups
        self._build_media_cache(media_export_df)
        
        # Create a list to store processed rows
        processed_rows = []
        
        # Process each product
        for _, product_row in products_df.iterrows():
            # Get the image IDs for this product
            variant_images = str(product_row.get(self.config.variant_images_column, '')).strip()
            
            if not variant_images or variant_images.lower() in ('', 'nan', 'none'):
                # If no images, keep the original row
                processed_rows.append(product_row.to_dict())
                continue
                
            # Process each image ID
            image_ids = [img_id.strip() for img_id in variant_images.split(',') if img_id.strip().isdigit()]
            
            for img_id in image_ids:
                # Create a copy of the product data
                new_row = product_row.copy()
                
                # Update the image data
                media_data = self.media_cache.get(img_id, {})
                new_row[self.config.variant_images_column] = img_id
                new_row[self.config.image_src_column] = media_data.get('url', '')
                
                # Build the alt text
                color = str(product_row.get(self.config.option1_value_column, '')).strip()
                alt_text = media_data.get('alt', '').strip()
                
                if color and alt_text:
                    new_row[self.config.image_alt_text_column] = f"{color} | {alt_text}"
                elif alt_text:
                    new_row[self.config.image_alt_text_column] = alt_text
                elif color:
                    new_row[self.config.image_alt_text_column] = color
                
                processed_rows.append(new_row.to_dict())
        
        # Create a new DataFrame with the processed rows
        result_df = pd.DataFrame(processed_rows)
        
        # Clean up any temporary columns
        if '_original_index' in result_df.columns:
            result_df = result_df.drop(columns=['_original_index'])
        
        self.logger.info(f"Завършена обработка. Общо {len(result_df)} реда.")
        return result_df
