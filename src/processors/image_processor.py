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
        self._id_len: int = 5  # default fallback
    
    def _build_media_cache(self, media_export_df: pd.DataFrame) -> None:
        """
        Build a cache of media data for faster lookups.
        
        Args:
            media_export_df: DataFrame containing media export data
        """
        self.media_cache = {}

        if media_export_df is None or media_export_df.empty:
            return

        # Resolve column names robustly (case-insensitive, strip spaces)
        def norm(name: str) -> str:
            return re.sub(r"\s+", "", str(name).strip().lower())

        cols_norm = {norm(c): c for c in media_export_df.columns}

        def resolve(preferred: str, candidates: list[str]) -> Optional[str]:
            all_cands = [preferred] + candidates
            for cand in all_cands:
                ckey = norm(cand)
                if ckey in cols_norm:
                    return cols_norm[ckey]
            return None

        id_col = resolve(self.config.media_id_column, ["id", "media id", "image id"])
        url_col = resolve(self.config.media_url_column, ["url", "image url", "link", "source", "src", "image src"]) 
        alt_col = resolve(self.config.media_alt_column, ["alt", "alt text", "image alt text", "image alt"]) 

        if id_col is None:
            self.logger.warning("В медийния файл не е открита ID колона. Провери заглавките.")
            return
        if url_col is None:
            self.logger.warning("В медийния файл не е открита URL колона. Провери заглавките.")
        if alt_col is None:
            self.logger.warning("В медийния файл не е открита ALT колона. Провери заглавките.")

        id_lengths = []
        for _, row in media_export_df.iterrows():
            raw_id = row.get(id_col, '')
            # Normalize ID: extract digits only, handle floats like 12345.0
            id_str = '' if raw_id is None else str(raw_id).strip()
            digits = re.sub(r"\D", "", id_str)
            if not digits:
                continue
            id_lengths.append(len(digits))
            # Clean URL/ALT, guard against NaN/None
            raw_url = row.get(url_col, '') if url_col is not None else ''
            raw_alt = row.get(alt_col, '') if alt_col is not None else ''
            url = '' if pd.isna(raw_url) else str(raw_url)
            alt = '' if pd.isna(raw_alt) else str(raw_alt)
            alt = alt.strip()
            if alt.lower() in {'nan', 'none'}:
                alt = ''
            self.media_cache[digits] = {
                'url': url,
                'alt': alt,
            }

        # Infer typical ID length from media cache keys
        if id_lengths:
            try:
                import statistics
                # Use the mode of lengths; if fails, use median
                self._id_len = int(statistics.mode(id_lengths))
            except Exception:
                try:
                    self._id_len = int(statistics.median(id_lengths))
                except Exception:
                    self._id_len = self._id_len
        # Sanity clamp
        if self._id_len <= 0 or self._id_len > 20:
            self._id_len = 5
    
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
                
            # Process each image ID to create additional rows
            # 1) split by common delimiters, 2) normalize to digits, 3) split concatenated sequences by inferred id length
            raw_tokens = re.split(r"[\s,;]+", variant_images)
            raw_tokens = [t for t in raw_tokens if t]
            image_ids = []
            for t in raw_tokens:
                digits = re.sub(r"\D", "", t)
                if not digits:
                    continue
                # If length matches expected -> add
                if len(digits) == self._id_len:
                    image_ids.append(digits)
                    continue
                # If concatenated (multiple of expected) -> chunk
                if self._id_len > 0 and len(digits) % self._id_len == 0 and len(digits) > self._id_len:
                    chunks = [digits[i:i+self._id_len] for i in range(0, len(digits), self._id_len)]
                    image_ids.extend(chunks)
                    self.logger.debug(f"Намерена конкатенация на ID за '{variant_images}': {chunks}")
                    continue
                # Fallback: if we can't confidently split, skip to avoid wrong matches
                self.logger.warning(f"Пропуснато ID '{t}' (дължина {len(digits)} не съвпада с очакваната {self._id_len})")
            # Deduplicate while preserving order
            seen = set()
            image_ids = [x for x in image_ids if not (x in seen or seen.add(x))]
            
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
        missing_ids: list[str] = []
        if not result_df.empty and self.config.variant_images_column in result_df.columns:
            def fill_url(row):
                nonlocal fixed_count, missing_ids
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
                    if len(missing_ids) < 50:
                        missing_ids.append(vid)
                return row

            result_df = result_df.apply(fill_url, axis=1)
            miss_count = len(missing_ids)
            self.logger.info(f"URL валидация: попълнени липсващи URL: {fixed_count}, липсващи в медийния файл ID: {miss_count}")
            if miss_count:
                self.logger.warning(f"Примери за липсващи ID (до 50): {', '.join(missing_ids)}")
        
        # Clean up any temporary columns
        if '_original_index' in result_df.columns:
            result_df = result_df.drop(columns=['_original_index'])
        
        self.logger.info(f"Завършена обработка. Общо {len(result_df)} реда.")
        return result_df
