import sys
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QLabel, QLineEdit, QPushButton, 
                            QTextEdit, QGroupBox, QMessageBox, QSplitter,
                            QFileDialog, QTableView)
from PyQt6.QtCore import Qt, QAbstractTableModel
from PyQt6.QtGui import QAction, QKeySequence
import pandas as pd
from parser2 import get_tables
import requests
import traceback

class PandasModel(QAbstractTableModel):
    """Model to display a pandas DataFrame in a QTableView"""
    def __init__(self, data):
        super().__init__()
        self._data = data

    def rowCount(self, parent=None):
        return len(self._data.index)

    def columnCount(self, parent=None):
        return len(self._data.columns)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole:
            value = self._data.iloc[index.row(), index.column()]
            return str(value)
        return None

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole:
            if orientation == Qt.Orientation.Horizontal:
                return str(self._data.columns[section])
            if orientation == Qt.Orientation.Vertical:
                return str(self._data.index[section])
        return None

class ParserUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MegaParse - Web Parser Generator")
        self.setMinimumSize(800, 600)
        
        # Create central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Input section
        input_group = QGroupBox("Input")
        input_layout = QVBoxLayout()
        
        # URL input
        url_layout = QHBoxLayout()
        url_label = QLabel("URL:")
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://example.com")
        self.url_input.setText("https://www.finn.no/realestate/homes/search.html?filters=&location=0.20061")
        url_layout.addWidget(url_label)
        url_layout.addWidget(self.url_input)
        input_layout.addLayout(url_layout)
        
        # Examples input
        examples_label = QLabel("Examples (one per line):")
        self.examples_input = QTextEdit()
        example_text = "3&nbsp;700&nbsp;000&nbsp;kr\n10&nbsp;900&nbsp;000&nbsp;kr\n19&nbsp;900&nbsp;000&nbsp;kr"
        self.examples_input.setPlaceholderText(example_text)
        self.examples_input.setText(example_text)
        input_layout.addWidget(examples_label)
        input_layout.addWidget(self.examples_input)
        
        # Buttons layout
        buttons_layout = QHBoxLayout()
        
        # Parse button
        self.parse_button = QPushButton("Parse")
        self.parse_button.clicked.connect(self.parse_content)
        buttons_layout.addWidget(self.parse_button)
        
        # Generate code button
        self.generate_button = QPushButton("Generate Parser Code")
        self.generate_button.clicked.connect(self.generate_parser_code)
        self.generate_button.setEnabled(False)  # Disabled until parsing is successful
        buttons_layout.addWidget(self.generate_button)
        
        input_layout.addLayout(buttons_layout)
        
        input_group.setLayout(input_layout)
        main_layout.addWidget(input_group)
        
        # Results section
        results_splitter = QSplitter(Qt.Orientation.Vertical)
        
        # DataFrame result
        df_group = QGroupBox("DataFrame Result")
        df_layout = QVBoxLayout()
        
        # Create table view for DataFrame
        self.table_view = QTableView()
        df_layout.addWidget(self.table_view)
        
        # Add text representation for copying
        self.df_result = QTextEdit()
        self.df_result.setReadOnly(True)
        self.df_result.setMaximumHeight(100)
        df_layout.addWidget(self.df_result)
        
        # Add copy buttons
        copy_buttons_layout = QHBoxLayout()
        copy_df_button = QPushButton("Copy DataFrame")
        copy_df_button.clicked.connect(self.copy_dataframe)
        copy_buttons_layout.addWidget(copy_df_button)
        df_layout.addLayout(copy_buttons_layout)
        
        df_group.setLayout(df_layout)
        results_splitter.addWidget(df_group)
        
        # Regex result
        regex_group = QGroupBox("Regex Pattern")
        regex_layout = QVBoxLayout()
        self.regex_result = QTextEdit()
        self.regex_result.setReadOnly(True)
        
        # Add copy regex button
        copy_regex_button = QPushButton("Copy Regex")
        copy_regex_button.clicked.connect(self.copy_regex)
        regex_layout.addWidget(self.regex_result)
        regex_layout.addWidget(copy_regex_button)
        
        regex_group.setLayout(regex_layout)
        results_splitter.addWidget(regex_group)
        
        main_layout.addWidget(results_splitter)
        
        # Store results for code generation
        self.current_url = ""
        self.current_regex = ""
        self.current_examples = []
        self.current_df = None
        
        # Set up keyboard shortcuts
        self.setup_shortcuts()
        
    def setup_shortcuts(self):
        # Add keyboard shortcuts
        shortcut_parse = QAction("Parse", self)
        shortcut_parse.setShortcut(QKeySequence("Ctrl+Return"))
        shortcut_parse.triggered.connect(self.parse_content)
        self.addAction(shortcut_parse)
        
    def copy_dataframe(self):
        if self.current_df is not None:
            clipboard = QApplication.clipboard()
            clipboard.setText(self.current_df.to_string())
            QMessageBox.information(self, "Copied", "DataFrame copied to clipboard")
    
    def copy_regex(self):
        regex_text = self.regex_result.toPlainText()
        if regex_text:
            clipboard = QApplication.clipboard()
            clipboard.setText(regex_text)
            QMessageBox.information(self, "Copied", "Regex pattern copied to clipboard")
        
    def parse_content(self):
        url = self.url_input.text().strip()
        examples_text = self.examples_input.toPlainText().strip()
        
        if not url:
            QMessageBox.warning(self, "Input Error", "Please enter a URL.")
            return
        
        if not examples_text:
            QMessageBox.warning(self, "Input Error", "Please enter at least one example.")
            return
        
        examples = [line.strip() for line in examples_text.split('\n') if line.strip()]
        
        try:
            # Show "working" status
            self.parse_button.setEnabled(False)
            self.parse_button.setText("Parsing...")
            QApplication.processEvents()
            
            # Fetch content
            content = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}).text
            
            # Process with parser2.py
            df, regex = get_tables(content, examples)
            
            # Store results for code generation
            self.current_url = url
            self.current_regex = regex
            self.current_examples = examples
            self.current_df = df
            
            # Display results in table view
            model = PandasModel(df)
            self.table_view.setModel(model)
            self.table_view.resizeColumnsToContents()
            
            # Display results in text areas
            self.df_result.setPlainText(df.to_string())
            self.regex_result.setPlainText(regex)
            
            # Enable generate code button
            self.generate_button.setEnabled(True)
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred while parsing:\n{str(e)}\n\n{traceback.format_exc()}")
            self.generate_button.setEnabled(False)
        finally:
            # Reset button
            self.parse_button.setEnabled(True)
            self.parse_button.setText("Parse")
    
    def generate_parser_code(self):
        if not self.current_url or not self.current_regex:
            QMessageBox.warning(self, "Generation Error", "Please parse a URL first.")
            return
        
        try:
            # Ask for save location
            file_path, _ = QFileDialog.getSaveFileName(
                self, "Save Parser Code", "parse_site.py", "Python Files (*.py)"
            )
            
            if not file_path:
                return  # User cancelled
            
            # Generate code content
            code = f"""import requests
import pandas as pd
import re
from bs4 import BeautifulSoup

url = "{self.current_url}"
content = requests.get(url, headers={{"User-Agent": "Mozilla/5.0"}}).text

print(re.findall(r"{self.current_regex}", content))
"""
            
            # Write to file
            with open(file_path, "w") as f:
                f.write(code)
            
            QMessageBox.information(
                self, "Success", f"Parser code generated and saved to {file_path}"
            )
            
        except Exception as e:
            QMessageBox.critical(
                self, "Error", f"An error occurred while generating code:\n{str(e)}"
            )

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ParserUI()
    window.show()
    sys.exit(app.exec()) 