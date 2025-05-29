import requests
import pandas as pd
import logging
import os
import json
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from parser import get_tables
import sys
import numpy as np
from scipy.stats import entropy

class TableParserModel:
    def __init__(self):
        self.url = None
        self.html_content = None
        self.tables = []
        self.table_dataframes = {}
        self.config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".config")
    
    def load_url(self, url, extraction_config=None):
        """Load a URL and parse tables"""
        self.url = url
        self.tables = []
        self.table_dataframes = {}
        
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            self.html_content = response.text
            
            # Use the parser.py functions to extract tables
            self._parse_tables()
            
            # Save the URL as the last used URL
            self.save_last_url(url)
            
            return True, f"Found {len(self.tables)} tables"
        except requests.exceptions.RequestException as e:
            return False, f"Error fetching URL: {str(e)}"
        except Exception as e:
            return False, f"Error parsing tables: {str(e)}"
    
    def save_last_url(self, url):
        """Save the last used URL to config file"""
        config = {}
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
            except:
                config = {}
        
        config['last_url'] = url
        
        try:
            with open(self.config_file, 'w') as f:
                json.dump(config, f)
        except Exception as e:
            logging.error(f"Error saving config: {str(e)}")
    
    def get_last_url(self):
        """Get the last used URL from config file"""
        if not os.path.exists(self.config_file):
            return ""
            
        try:
            with open(self.config_file, 'r') as f:
                config = json.load(f)
                return config.get('last_url', "")
        except Exception as e:
            logging.error(f"Error loading config: {str(e)}")
            return ""
    
    def _parse_tables(self):
        """Parse tables using parser.py functions"""
        try:
            # Get all tables using the parser.py get_tables function
            all_dfs = get_tables(self.html_content)
            
            for i, df in enumerate(all_dfs):
                # Skip tables that are empty, contain only empty rows, or have columns but no actual data
                if df.empty or df.dropna(how='all').empty:
                    continue
                    
                # Also skip tables that have columns but all cells are empty or NaN
                if not df.empty and df.shape[0] > 0 and df.shape[1] > 0:
                    # Convert all values to string and check if any non-empty cell exists
                    # (excluding column headers)
                    has_data = False
                    for _, row in df.iterrows():
                        if not row.dropna().empty and any(str(val).strip() != '' for val in row.dropna()):
                            has_data = True
                            break
                    
                    if not has_data:
                        continue
                    
                table_id = len(self.tables)
                
                # Create a descriptive name based on table columns or position
                if len(df.columns) > 0:
                    column_preview = " ".join([str(col)[:10] for col in df.columns[:3]])
                    name = f"Table {table_id+1}: {column_preview}"
                else:
                    name = f"Table {table_id+1}"
                
                # Determine type based on shape and structure
                table_type = "standard"
                
                self.tables.append({"id": table_id, "name": name, "type": table_type})
                self.table_dataframes[table_id] = df
        except Exception as e:
            logging.error(f"Error parsing tables: {str(e)}")
    
    def get_tables(self):
        """Return list of available tables"""
        return self.tables
    
    def get_table_preview(self, table_id, max_rows=100):
        """Get preview of a specific table"""
        if table_id in self.table_dataframes:
            return self.table_dataframes[table_id].head(max_rows)
        return None
    
    def save_table(self, table_id, filename=None, format="parquet"):
        """Save table to file in specified format"""
        if table_id not in self.table_dataframes:
            return False, "Table not found"
        
        if filename is None:
            # Create filename from URL and table ID
            domain = urlparse(self.url).netloc.replace(".", "_")
            extension = ".parquet" if format == "parquet" else ".csv" if format == "csv" else ".xlsx"
            filename = f"{domain}_table_{table_id}{extension}"
        
        try:
            df = self.table_dataframes[table_id]
            
            if format == "parquet":
                df.to_parquet(filename)
            elif format == "csv":
                df.to_csv(filename, index=False)
            elif format == "excel":
                df.to_excel(filename, index=False)
            else:
                return False, f"Unsupported format: {format}"
                
            return True, f"Table saved to {filename}"
        except Exception as e:
            return False, f"Error saving table: {str(e)}"

    def calculate_table_entropy(self, df):
        """Calculate entropy score for a table based on column data distribution."""
        scores = []
        for col in df.columns:
            try:
                # Handle multi-dimensional data by converting to string representation
                if isinstance(df[col].iloc[0], (list, dict, tuple)):
                    # Convert complex objects to string representation
                    value_counts = df[col].apply(str).value_counts()
                else:
                    # For regular data, convert to string and count frequencies
                    value_counts = df[col].fillna('').astype(str).value_counts()
                
                # Calculate entropy only if we have more than one unique value
                if len(value_counts) > 1:
                    e = entropy(value_counts)
                    # Normalize entropy to 0-1 range
                    max_entropy = np.log(len(value_counts))
                    normalized_entropy = e / max_entropy if max_entropy > 0 else 0
                    scores.append(normalized_entropy)
            except Exception as e:
                # Skip columns that cause errors in entropy calculation
                logging.warning(f"Could not calculate entropy for column {col}: {str(e)}")
                continue
        
        # Return average entropy across columns, or 0 if no valid scores
        return np.mean(scores) if scores else 0

    def get_table_scores(self):
        """Get entropy scores for all tables."""
        scores = []
        for table in self.tables:
            table_id = table["id"]
            if table_id in self.table_dataframes:
                df = self.table_dataframes[table_id]
                entropy_score = self.calculate_table_entropy(df)
                scores.append({
                    "id": table_id,
                    "name": table["name"],
                    "entropy": entropy_score,
                    "rows": df.shape[0],
                    "cols": df.shape[1]
                })
        return scores 