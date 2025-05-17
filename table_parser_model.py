import requests
from bs4 import BeautifulSoup
import pandas as pd
import os
from urllib.parse import urlparse

class TableParserModel:
    def __init__(self):
        self.url = ""
        self.tables = []
        self.table_dataframes = {}
    
    def load_url(self, url):
        """Load a URL and parse tables"""
        self.url = url
        self.tables = []
        self.table_dataframes = {}
        
        try:
            response = requests.get(url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'lxml')
            tables = soup.find_all('table')
            
            for i, table in enumerate(tables):
                # Create a descriptive name based on table headers or position
                headers = table.find_all('th')
                if headers:
                    name = f"Table {i+1}: {' '.join([h.get_text().strip()[:10] for h in headers[:3]])}"
                else:
                    name = f"Table {i+1}"
                
                self.tables.append({"id": i, "name": name})
                # Parse the table to DataFrame
                df = pd.read_html(str(table))[0]
                self.table_dataframes[i] = df
                
            return True, f"Found {len(self.tables)} tables"
        except requests.exceptions.RequestException as e:
            return False, f"Error fetching URL: {str(e)}"
        except Exception as e:
            return False, f"Error parsing tables: {str(e)}"
    
    def get_tables(self):
        """Return list of available tables"""
        return self.tables
    
    def get_table_preview(self, table_id, max_rows=5):
        """Get preview of a specific table"""
        if table_id in self.table_dataframes:
            return self.table_dataframes[table_id].head(max_rows)
        return None
    
    def save_table(self, table_id, filename=None):
        """Save table to parquet file"""
        if table_id not in self.table_dataframes:
            return False, "Table not found"
        
        if filename is None:
            # Create filename from URL and table ID
            domain = urlparse(self.url).netloc.replace(".", "_")
            filename = f"{domain}_table_{table_id}.parquet"
        
        try:
            df = self.table_dataframes[table_id]
            df.to_parquet(filename)
            return True, f"Table saved to {filename}"
        except Exception as e:
            return False, f"Error saving table: {str(e)}" 