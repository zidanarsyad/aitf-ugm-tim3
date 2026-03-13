# -*- coding: utf-8 -*-
"""
Refactored Press Release Data Cleaner
Cleans and merges press release data from Komdigi and general sources.
Output: db/siaran_pers_cleaning.json
"""

import pandas as pd
import json
import re
import os
import numpy as np
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class PressReleaseCleaner:
    """
    A class to clean and process Indonesian press release data.
    """
    
    def __init__(self, output_path):
        self.output_path = output_path
        self.bulan_map = {
            'Januari': '01', 'Februari': '02', 'Pebruari': '02', 'Maret': '03',
            'April': '04', 'Mei': '05', 'Juni': '06', 'Juli': '07', 'Agustus': '08',
            'September': '09', 'Oktober': '10', 'November': '11', 'Desember': '12'
        }
        self.footer_markers = [
            "Kontak media",
            "Untuk Informasi lebih lanjut",
            "Dapatkan informasi lainnya",
            "Biro Humas Kementerian Kominfo",
            "Humas BAKTI Kominfo",
        ]

    def clean_date(self, date_str):
        """
        Converts Indonesian verbal dates or DD-MM-YYYY to YYYY-MM-DD.
        """
        if not date_str or not isinstance(date_str, str):
            return None

        # Try DD-MM-YYYY or DD/MM/YYYY format
        match = re.search(r'(\d{1,2})[-/](\d{1,2})[-/](\d{4})', date_str)
        if match:
            day, month, year = match.groups()
            return f"{year}-{month.zfill(2)}-{day.zfill(2)}"

        # Try Indonesian verbal date (e.g., '28 Februari 2026')
        try:
            # Remove day names (e.g., 'Selasa, ')
            clean_str = re.sub(r'^[A-Za-z]+,\s*', '', date_str)
            parts = clean_str.split()
            
            if len(parts) >= 3:
                day = parts[0].zfill(2)
                # Map month name or use as-is if numeric
                month = self.bulan_map.get(parts[1], None)
                if not month and parts[1].isdigit():
                    month = parts[1].zfill(2)
                
                year = parts[2]
                if month:
                    return f"{year}-{month}-{day}"
        except Exception:
            pass
            
        return None

    def clean_all_noise(self, text, judul=''):
        """
        Removes noise such as headers, datelines, footers, and redundant symbols.
        Inspired by the original clean_press_release script.
        """
        if not text or not isinstance(text, str):
            return ""

        # 1. Normalization: Unicode, Whitespace, & Junk Characters
        text = re.sub(r'[\u00ad\u200b\u200c\u200d\u2060\ufeff]', '', text)
        text = re.sub(r'[\s\u00a0\u202f\u2009]+', ' ', text)
        
        # Add spaces between letters and numbers where they might be stuck
        text = re.sub(r'([a-zA-Z])(\d)', r'\1 \2', text)
        text = re.sub(r'(\d)([a-zA-Z])', r'\1 \2', text)
        text = re.sub(r'(NO\.?)(\d)', r'\1 \2', text, flags=re.IGNORECASE)

        # 2. Header and Dateline Stripping
        # Strip "Siaran Pers... Tentang" header
        text = re.sub(r'^\s*Siaran\s*Pers.*?Tentang\s*', '', text, flags=re.IGNORECASE)
        # Strip dateline like "(Jakarta, 13 Juni 2016–)"
        text = re.sub(r'^\(\s*[^)]{3,120}\)\.?\s*', '', text)

        # 3. Footer Removal
        for marker in self.footer_markers:
            # Take everything before the footer marker
            parts = re.split(re.escape(marker), text, flags=re.IGNORECASE)
            text = parts[0]

        # Strip standard press release sign-off at the end
        text = re.sub(r'Siaran\s+Pers\s+No\.\s*[\w\-/]+.*?\d{4}\s*$', '', text, flags=re.IGNORECASE)

        # 4. Punctuation and Detail Cleanup
        text = re.sub(r'\s*\(\)\s*$', '', text) # Remove empty parentheses at end
        text = re.sub(r'([a-z])\.([A-Z])', r'\1. \2', text) # Fix glued sentences
        text = re.sub(r',([^\s\d])', r', \1', text)        # Fix glued commas
        
        # Cleanup leading garbage characters
        text = re.sub(r'^[ \.,\-–—\(\)\d/]+', '', text)
        
        # Split by horizontal line markers and take the first part
        text = re.split(r'(?=\*{3,}|-{3,}|_{3,})', text)[0]
        
        # Final formatting
        text = text.replace('*', '').strip()
        text = re.sub(r'\s+', ' ', text) # Final whitespace collapse
        
        # Optional: long non-word symbol sequence at the end
        text = re.sub(r'[\(\[\{]?[^\w\s]{3,}[\)\]\}]?\s*$', '', text)

        # Quality check: Minimum length
        if len(text) < 50:
            return None
            
        return text

    def process(self, input_files):
        """
        Loads, merges, and cleans data from multiple JSON sources.
        """
        all_dfs = []
        
        for file_path in input_files:
            if not os.path.exists(file_path):
                logging.warning(f"File not found: {file_path}")
                continue
            
            logging.info(f"Loading data from {file_path}...")
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                df = pd.DataFrame(data)
                
                # Normalize source column
                if 'source' not in df.columns:
                    if 'komdigi' in file_path.lower():
                        df['source'] = 'KOMDIGI'
                    else:
                        df['source'] = 'GENERAL'
                
                all_dfs.append(df)
            except Exception as e:
                logging.error(f"Error loading {file_path}: {e}")

        if not all_dfs:
            logging.error("No valid data files were processed.")
            return

        # Merge all data
        combined_df = pd.concat(all_dfs, ignore_index=True)
        logging.info(f"Total records loaded: {len(combined_df)}")

        # Clean dates
        logging.info("Cleaning dates...")
        combined_df['tanggal_clean'] = combined_df['date'].apply(self.clean_date)

        # Clean text noise
        logging.info("Cleaning text content...")
        combined_df['text_clean'] = combined_df.apply(
            lambda row: self.clean_all_noise(row['text'], row.get('title', '')), 
            axis=1
        )

        # Filter out rows with empty or too short text
        original_count = len(combined_df)
        combined_df = combined_df.dropna(subset=['text_clean'])
        filtered_count = len(combined_df)
        logging.info(f"Filtered out {original_count - filtered_count} records due to low quality or empty text.")

        # Final column selection and renaming
        df_final = combined_df[[
            'title',
            'tanggal_clean',
            'link',
            'source',
            'text',
            'text_clean'
        ]].rename(columns={
            'title': 'judul',
            'link': 'link_sumber',
            'text': 'text_raw'
        })

        # Save to JSON
        try:
            os.makedirs(os.path.dirname(self.output_path), exist_ok=True)
            df_final.to_json(self.output_path, orient='records', indent=4, force_ascii=False)
            logging.info(f"Successfully saved {len(df_final)} cleaned records to {self.output_path}")
        except Exception as e:
            logging.error(f"Error saving output: {e}")

if __name__ == "__main__":
    # Define absolute paths based on user environment
    BASE_DIR = r"d:\1_projects\aitf-ugm-tim3"
    INPUT_FILE_1 = os.path.join(BASE_DIR, "db", "siaran_pers_komdigi_all.json")
    INPUT_FILE_2 = os.path.join(BASE_DIR, "db", "siaran_pers_general.json")
    OUTPUT_FILE = os.path.join(BASE_DIR, "db", "siaran_pers_cleaning.json")

    cleaner = PressReleaseCleaner(OUTPUT_FILE)
    cleaner.process([INPUT_FILE_1, INPUT_FILE_2])