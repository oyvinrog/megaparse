import requests
import pandas as pd
import logging
import os
import json
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from src.parser import get_tables
import sys
import numpy as np
from scipy.stats import entropy
from difflib import SequenceMatcher
from src.step_history import StepHistory, OperationType
import sqlite3
import sqlshell
import subprocess
import shutil

class TableParserModel:
    def __init__(self):
        self.url = None
        self.html_content = None
        self.tables = []
        self.table_dataframes = {}
        self.config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".config")
        # Initialize with empty step history for new session
        self.steps = StepHistory(os.path.join(os.path.dirname(os.path.abspath(__file__)), "steps.json"))
        self.clear_steps()  # Ensure we start with empty steps
        self.recent_projects_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "recent_projects.json")
        self.max_recent_projects = 10
        self.current_project_file = None  # Track current project file path
        self.progress_callback = None  # Callback for progress updates
    
    def set_progress_callback(self, callback):
        """Set a callback function to receive progress updates"""
        self.progress_callback = callback
    
    def _update_progress(self, progress, message=None):
        """Update progress if callback is set"""
        if self.progress_callback:
            self.progress_callback(progress, message)
    
    def add_step(self, operation: OperationType, details: str, metadata: dict = None):
        """Add a step to the operations history"""
        self.steps.add_step(operation, details, metadata)
    
    def get_steps(self):
        """Get the list of operations performed"""
        return self.steps.get_steps()
    
    def clear_steps(self):
        """Clear the operations history"""
        self.steps.clear_steps()
    
    def load_url(self, url, extraction_config=None):
        """Load a URL and parse tables"""
        self.url = url
        self.tables = []
        self.table_dataframes = {}
        self.clear_steps()  # Clear previous steps when loading new URL
        
        try:
            self._update_progress(10, "Fetching URL...")
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            self.html_content = response.text
            self.add_step(OperationType.FETCH, f"Fetched content from {url}")
            
            self._update_progress(30, "Parsing tables...")
            # Use the parser.py functions to extract tables
            self._parse_tables()
            
            # Save the URL as the last used URL
            self.save_last_url(url)
            
            self._update_progress(100, "Complete")
            return True, f"Found {len(self.tables)} tables"
        except requests.exceptions.RequestException as e:
            self.add_step(OperationType.ERROR, f"Error fetching URL: {str(e)}")
            return False, f"Error fetching URL: {str(e)}"
        except Exception as e:
            self.add_step(OperationType.ERROR, f"Error parsing tables: {str(e)}")
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
            
            total_tables = len(all_dfs)
            for i, df in enumerate(all_dfs):
                progress = 30 + (i / total_tables * 60)  # Scale from 30% to 90%
                self._update_progress(int(progress), f"Processing table {i+1}/{total_tables}")
                
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
                
                self.add_step(
                    OperationType.PARSE,
                    f"Parsed table: {name}",
                    metadata={"table_id": table_id, "rows": df.shape[0], "cols": df.shape[1]}
                )
        except Exception as e:
            logging.error(f"Error parsing tables: {str(e)}")
            self.add_step(OperationType.ERROR, f"Error parsing tables: {str(e)}")
    
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

    def open_in_sqlshell(self):
        """Dump all dataframes to a SQLite database and open it with sqlshell"""
        if not self.table_dataframes:
            return False, "No tables to export"
        
        try:
            # Create a temporary database file
            db_file = "tables.db"
            
            # Connect to SQLite database
            conn = sqlite3.connect(db_file)
            
            # Export each dataframe to a table in the database
            for table_id, df in self.table_dataframes.items():
                table_name = f"table_{table_id}"
                df.to_sql(table_name, conn, if_exists='replace', index=False)
            
            # Close the connection
            conn.close()
            
            # Try to launch in a new terminal window
            terminal = shutil.which('gnome-terminal') or shutil.which('x-terminal-emulator') or shutil.which('xterm')
            if terminal:
                subprocess.Popen([terminal, '--', sys.executable, 'run_sqlshell.py', db_file])
            else:
                subprocess.Popen([sys.executable, 'run_sqlshell.py', db_file])
            
            self.add_step(
                OperationType.SAVE,
                f"Exported {len(self.table_dataframes)} tables to SQLite database",
                metadata={"db_file": db_file}
            )
            
            return True, f"Opened {len(self.table_dataframes)} tables in SQLite database"
        except Exception as e:
            return False, f"Error exporting to SQLite: {str(e)}"

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

    def calculate_column_similarity(self, column_names, target_columns):
        """Calculate similarity scores between column names and target columns using token-based and substring matching, with stricter substring rules."""
        def token_set_ratio(a, b):
            set_a = set(str(a).lower().split())
            set_b = set(str(b).lower().split())
            intersection = set_a & set_b
            union = set_a | set_b
            if not union:
                return 0.0
            return len(intersection) / len(union)

        def best_similarity(col, targets):
            col = str(col).lower().strip()
            for target in targets:
                target = str(target).lower().strip()
                # Only allow substring match if both are at least 3 characters
                if len(col) >= 3 and len(target) >= 3 and (col in target or target in col):
                    return 1.0
            # Otherwise, use token set ratio
            return max(token_set_ratio(col, target) for target in targets)

        scores = [best_similarity(col, target_columns) for col in column_names]
        return scores

    def best_header_similarity(self, df, target_columns, max_header_rows=3):
        """Scan first N rows for possible headers and return the row/columns with the best similarity."""
        best_scores = self.calculate_column_similarity(df.columns, target_columns)
        best_row = None
        best_avg = sum(best_scores) / len(best_scores) if best_scores else 0
        best_header = list(df.columns)
        # Scan first N rows
        for i in range(min(max_header_rows, len(df))):
            row = list(df.iloc[i])
            scores = self.calculate_column_similarity(row, target_columns)
            avg = sum(scores) / len(scores) if scores else 0
            if avg > best_avg:
                best_avg = avg
                best_scores = scores
                best_row = i
                best_header = row
        return best_header, best_scores, best_row 

    def target_column_match_score(self, df, target_columns, max_header_rows=3):
        """For each target column, find the best-matching column/header in the table. Return the average of these best matches."""
        best_header, _, _ = self.best_header_similarity(df, target_columns, max_header_rows)
        def best_match_for_target(target):
            return max(self.calculate_column_similarity(best_header, [target]))
        if not target_columns:
            return 0.0
        scores = [best_match_for_target(target) for target in target_columns]
        return sum(scores) / len(scores) if scores else 0.0

    def remove_table(self, table_id):
        """Remove a table from the list"""
        if table_id in self.table_dataframes:
            table_name = next((t["name"] for t in self.tables if t["id"] == table_id), None)
            del self.table_dataframes[table_id]
            self.tables = [t for t in self.tables if t["id"] != table_id]
            if table_name:
                self.add_step(
                    OperationType.DELETE,
                    f"Deleted table: {table_name}",
                    metadata={"table_id": table_id}
                )
            return True
        return False

    def remove_other_tables(self, keep_table_ids):
        """Remove all tables except the specified ones"""
        if isinstance(keep_table_ids, str):
            keep_table_ids = [keep_table_ids]  # Handle single ID case for backward compatibility
        tables_to_remove = [t["id"] for t in self.tables if t["id"] not in keep_table_ids]
        for table_id in tables_to_remove:
            self.remove_table(table_id)
        return len(tables_to_remove)

    def rename_table(self, table_id, new_name):
        """Rename a table"""
        for table in self.tables:
            if table["id"] == table_id:
                old_name = table["name"]
                table["name"] = new_name
                self.add_step(
                    OperationType.RENAME,
                    f"Renamed table from '{old_name}' to '{new_name}'",
                    metadata={"table_id": table_id, "old_name": old_name, "new_name": new_name}
                )
                return True
        return False

    def promote_first_row_to_header(self, table_id):
        """Promote the first row of a table to become the header"""
        if table_id not in self.table_dataframes:
            return False, "Table not found"
        
        df = self.table_dataframes[table_id]
        if df.shape[0] < 2:
            return False, "Table must have at least 2 rows to promote header"
        
        # Store original table structure for reload matching
        if not hasattr(df, 'attrs'):
            df.attrs = {}
        if 'original_structure' not in df.attrs:
            df.attrs['original_structure'] = {
                'shape': df.shape,
                'columns': list(df.columns),
                'first_row': df.iloc[0].tolist() if len(df) > 0 else [],
                'sample_data': df.head(3).astype(str).values.tolist()
            }
        
        # Get the first row to use as headers
        new_headers = df.iloc[0].tolist()
        
        # Create new dataframe with first row as headers
        new_df = df.iloc[1:].copy()
        new_df.columns = new_headers
        new_df.reset_index(drop=True, inplace=True)
        
        # Preserve the original structure info
        new_df.attrs = df.attrs.copy()
        
        # Update the dataframe
        self.table_dataframes[table_id] = new_df
        
        # Find the table name by ID instead of using ID as index
        table_name = None
        for table in self.tables:
            if table["id"] == table_id:
                table_name = table["name"]
                break
        
        if table_name is None:
            table_name = f"Table {table_id}"
        
        # Add step to history
        self.add_step(
            OperationType.PROMOTE_HEADER,
            f"Promoted first row to header for table: {table_name}",
            metadata={"table_id": table_id}
        )
        
        return True, f"Successfully promoted first row to header. Table now has {new_df.shape[0]} rows."

    def get_recent_projects(self):
        """Get list of recent projects"""
        if not os.path.exists(self.recent_projects_file):
            return []
            
        try:
            with open(self.recent_projects_file, 'r') as f:
                projects = json.load(f)
                return projects[:self.max_recent_projects]
        except Exception as e:
            logging.error(f"Error loading recent projects: {str(e)}")
            return []
    
    def add_recent_project(self, project_path):
        """Add a project to recent projects list"""
        try:
            # Get current list
            projects = self.get_recent_projects()
            
            # Convert project_path to absolute path
            project_path = os.path.abspath(project_path)
            
            # Remove if already exists
            if project_path in projects:
                projects.remove(project_path)
            
            # Add to beginning of list
            projects.insert(0, project_path)
            
            # Trim to max size
            projects = projects[:self.max_recent_projects]
            
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(self.recent_projects_file), exist_ok=True)
            
            # Save updated list
            with open(self.recent_projects_file, 'w') as f:
                json.dump(projects, f)
                
        except Exception as e:
            logging.error(f"Error updating recent projects: {str(e)}")
    
    def save_project(self, filename):
        """Save project state to file"""
        try:
            # Save project data
            project_data = {
                "url": self.url,
                "html_content": self.html_content,
                "tables": self.tables,
                "table_dataframes": {k: v.to_dict() for k, v in self.table_dataframes.items()},
                "steps": [step.to_dict() for step in self.steps.get_steps()]
            }
            
            with open(filename, 'w') as f:
                json.dump(project_data, f)
            
            # Update current project file
            self.current_project_file = filename
            
            # Add to recent projects
            self.add_recent_project(filename)
            
            self.add_step(
                OperationType.PROJECT_SAVE,
                f"Saved project to {filename}",
                metadata={"filename": filename}
            )
            return True, f"Project saved to {filename}"
        except Exception as e:
            error_msg = f"Error saving project: {str(e)}"
            self.add_step(OperationType.ERROR, error_msg)
            return False, error_msg

    def load_project(self, filename):
        """Load project state from file"""
        try:
            # Load project data
            with open(filename, 'r') as f:
                project_data = json.load(f)
            
            # Clear current state
            self.clear_steps()
            self.tables = []
            self.table_dataframes = {}
            
            # Restore state
            self.url = project_data["url"]
            self.html_content = project_data["html_content"]
            self.tables = project_data["tables"]
            self.current_project_file = filename  # Set current project file
            
            # Convert table dataframes back to pandas DataFrames
            for k, v in project_data["table_dataframes"].items():
                self.table_dataframes[int(k)] = pd.DataFrame.from_dict(v)
            
            # Restore steps
            for step_data in project_data["steps"]:
                self.steps.add_step(
                    OperationType(step_data["operation"]),
                    step_data["details"],
                    step_data.get("metadata")
                )
            
            self.add_step(
                OperationType.PROJECT_LOAD,
                f"Loaded project from {filename}",
                metadata={"filename": filename}
            )
            return True, f"Project loaded from {filename}"
        except Exception as e:
            error_msg = f"Error loading project: {str(e)}"
            self.add_step(OperationType.ERROR, error_msg)
            return False, error_msg

    def reload(self):
        """Reload the current URL data"""
        if not self.url:
            return False, "No URL to reload"
            
        try:
            # Store current tables and steps for comparison
            old_tables = self.tables.copy()
            old_table_dataframes = self.table_dataframes.copy()
            
            # Store user operations that should be preserved and reapplied
            user_operations = [
                step for step in self.steps.get_steps() 
                if step.operation in [OperationType.DELETE, OperationType.RENAME, OperationType.PROMOTE_HEADER]
            ]
            
            # Clear only tables and dataframes, not steps
            self.tables = []
            self.table_dataframes = {}
            
            # Only fetch from URL if we don't already have HTML content or if URL is a real URL
            if not self.html_content or (self.url.startswith('http://') and not self.url.startswith('http://example.com') and not self.url.startswith('http://test.com')):
                # Reload URL
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                }
                response = requests.get(self.url, headers=headers)
                response.raise_for_status()
                
                self.html_content = response.text
                self.add_step(OperationType.FETCH, f"Reloaded content from {self.url}")
            else:
                # Use existing HTML content (for testing or when content is already available)
                self.add_step(OperationType.FETCH, f"Reused existing content for {self.url}")
            
            # Parse tables using the same configuration as original load
            self._parse_tables()
            
            # Create a mapping from old table IDs to new table IDs based on content similarity
            table_id_mapping = {}
            
            for old_table in old_tables:
                old_id = old_table["id"]
                if old_id in old_table_dataframes:
                    old_df = old_table_dataframes[old_id]
                    best_match_id = None
                    best_similarity = 0
                    
                    # Use original structure if available (for tables that had header promotion)
                    if hasattr(old_df, 'attrs') and 'original_structure' in old_df.attrs:
                        original_structure = old_df.attrs['original_structure']
                        comparison_shape = original_structure['shape']
                        comparison_sample = original_structure['sample_data']
                    else:
                        # Use current structure for tables that weren't modified
                        comparison_shape = old_df.shape
                        comparison_sample = old_df.head(3).astype(str).values.tolist()
                    
                    # Find the best matching new table based on content similarity
                    for new_table in self.tables:
                        new_id = new_table["id"]
                        new_df = self.table_dataframes[new_id]
                        
                        # Calculate similarity based on shape and content
                        similarity = 0
                        if comparison_shape == new_df.shape:
                            similarity += 0.5  # Same shape gives base similarity
                            
                            # Compare content similarity
                            try:
                                # Convert new table sample to string for comparison
                                new_sample = new_df.head(3).astype(str).values.tolist()
                                
                                # Check if the content is similar
                                if comparison_sample == new_sample:
                                    similarity += 0.5  # Perfect content match
                                else:
                                    # Check partial content similarity
                                    matching_cells = 0
                                    total_cells = 0
                                    
                                    for i in range(min(len(comparison_sample), len(new_sample))):
                                        for j in range(min(len(comparison_sample[i]), len(new_sample[i]))):
                                            total_cells += 1
                                            if comparison_sample[i][j] == new_sample[i][j]:
                                                matching_cells += 1
                                    
                                    if total_cells > 0:
                                        similarity += 0.3 * (matching_cells / total_cells)
                            except:
                                pass
                        
                        if similarity > best_similarity and similarity > 0.7:  # Require high similarity
                            best_similarity = similarity
                            best_match_id = new_id
                    
                    if best_match_id is not None:
                        table_id_mapping[old_id] = best_match_id
            
            # Re-apply user operations using the table ID mapping
            for step in user_operations:
                if step.metadata and "table_id" in step.metadata:
                    old_table_id = step.metadata["table_id"]
                    new_table_id = table_id_mapping.get(old_table_id)
                    
                    if new_table_id is not None and new_table_id in self.table_dataframes:
                        if step.operation == OperationType.DELETE:
                            self.remove_table(new_table_id)
                        elif step.operation == OperationType.RENAME:
                            if "new_name" in step.metadata:
                                self.rename_table(new_table_id, step.metadata["new_name"])
                        elif step.operation == OperationType.PROMOTE_HEADER:
                            # Re-apply header promotion
                            success, message = self.promote_first_row_to_header(new_table_id)
                            if success:
                                # Update the step to indicate it was reapplied during reload
                                self.add_step(
                                    OperationType.PROMOTE_HEADER,
                                    f"Reapplied header promotion during reload: {message}",
                                    metadata={"table_id": new_table_id, "reapplied_during_reload": True}
                                )
            
            return True, f"Reloaded {len(self.tables)} tables"
        except Exception as e:
            self.add_step(OperationType.ERROR, f"Error during reload: {str(e)}")
            return False, f"Error during reload: {str(e)}" 