"""
Image processing module for NikiVibes Image Processor.
"""
import logging
from typing import Dict, List, Any, Optional
import pandas as pd
from pathlib import Path
import re
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
                raw_id = row.get(self.config.media_id_column, '')
                # Normalize ID: extract digits only, handle floats like 12345.0
                id_str = '' if raw_id is None else str(raw_id).strip()
                digits = re.sub(r"\D", "", id_str)
                if not digits:
                    continue
                # Clean URL/ALT, guard against NaN/None
                raw_url = row.get(self.config.media_url_column, '')
                raw_alt = row.get(self.config.media_alt_column, '')
                url = '' if pd.isna(raw_url) else str(raw_url)
                alt = '' if pd.isna(raw_alt) else str(raw_alt)
                alt = alt.strip()
                if alt.lower() in {'nan', 'none'}:
                    alt = ''
                self.media_cache[digits] = {
                    'url': url,
                    'alt': alt,
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
        
        # Get the original dtypes for boolean columns
        bool_columns = products_df.select_dtypes(include=['bool']).columns.tolist()
        
        # Process each product
        for _, product_row in products_df.iterrows():
            # Always keep the original row first
            processed_rows.append(dict(product_row))
            
            # Get the image IDs for this product
            variant_images = str(product_row.get(self.config.variant_images_column, '')).strip()
            
            if not variant_images or variant_images.lower() in ('', 'nan', 'none'):
                # If no images, just keep the original row (already added)
                continue
                
            # Process each image ID to create additional rows (normalize IDs to digits only)
            tokens = [t.strip() for t in variant_images.split(',') if t.strip()]
            image_ids = []
            for t in tokens:
                digits = re.sub(r"\D", "", t)
                if digits:
                    image_ids.append(digits)
            
            for img_id in image_ids:
                # Create a copy of the product data for the new row
                new_row = dict(product_row)
                
                # Update the image data for the new row
                media_data = self.media_cache.get(img_id, {})
                new_row[self.config.variant_images_column] = img_id
                new_row[self.config.image_src_column] = media_data.get('url', '')
                
                # Build the alt text for the new row using the required formula
                color = str(product_row.get(self.config.option1_value_column, '')).strip()
                alt_text = str(media_data.get('alt', '')).strip()
                if alt_text.lower() in {'nan', 'none'}:
                    alt_text = ''
                
                if color and alt_text:
                    new_row[self.config.image_alt_text_column] = f"color:{color} | {alt_text}"
                elif alt_text:
                    new_row[self.config.image_alt_text_column] = alt_text
                elif color:
                    new_row[self.config.image_alt_text_column] = f"color:{color}"
                
                # Add the new row with image data
                processed_rows.append(new_row)
        
        # Create a new DataFrame with the processed rows
        result_df = pd.DataFrame(processed_rows)

        # Validation & auto-fix: ensure Image Src is set when we have a valid image id in cache
        fixed_count = 0
        missing_count = 0
        if not result_df.empty and self.config.variant_images_column in result_df.columns:
            def fill_url(row):
                nonlocal fixed_count, missing_count
                vid_raw = str(row.get(self.config.variant_images_column, '')).strip()
                if not vid_raw:
                    return row
                vid = re.sub(r"\D", "", vid_raw)
                if not vid:
                    return row
                current_url = str(row.get(self.config.image_src_column, '')).strip()
                media = self.media_cache.get(vid)
                if media and (not current_url):
                    row[self.config.image_src_column] = media.get('url', '')
                    if row[self.config.image_src_column]:
                        fixed_count += 1
                elif not media:
                    missing_count += 1
                return row

            result_df = result_df.apply(fill_url, axis=1)
            self.logger.info(f"URL валидация: попълнени липсващи URL: {fixed_count}, липсващи в медийния файл ID: {missing_count}")
        
        # Clean up any temporary columns
        if '_original_index' in result_df.columns:
            result_df = result_df.drop(columns=['_original_index'])
        
        self.logger.info(f"Завършена обработка. Общо {len(result_df)} реда.")
        return result_df
