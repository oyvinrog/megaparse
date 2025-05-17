from PyQt6.QtWidgets import (
    QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QPushButton,
    QLineEdit, QLabel, QListWidget, QListWidgetItem, QMessageBox,
    QTableWidget, QTableWidgetItem, QSplitter, QFileDialog,
    QComboBox, QCheckBox, QGroupBox, QTextBrowser
)
from PyQt6.QtCore import Qt
import pandas as pd

class TableParserUI(QMainWindow):
    def __init__(self, model):
        super().__init__()
        self.model = model
        self.init_ui()
        
    def init_ui(self):
        """Initialize user interface"""
        self.setWindowTitle("Web Table Parser")
        self.setGeometry(100, 100, 1200, 800)
        
        # Main layout
        main_layout = QVBoxLayout()
        
        # URL input
        url_layout = QHBoxLayout()
        url_layout.addWidget(QLabel("URL:"))
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Enter webpage URL")
        url_layout.addWidget(self.url_input)
        self.fetch_button = QPushButton("Fetch Tables")
        self.fetch_button.clicked.connect(self.fetch_tables)
        url_layout.addWidget(self.fetch_button)
        main_layout.addLayout(url_layout)
        
        # Options for parsing
        options_layout = QHBoxLayout()
        
        # Table types group
        table_types_group = QGroupBox("Table Types to Extract")
        table_types_layout = QHBoxLayout()
        
        self.standard_table_check = QCheckBox("Standard HTML Tables")
        self.standard_table_check.setChecked(True)
        table_types_layout.addWidget(self.standard_table_check)
        
        self.advanced_table_check = QCheckBox("Advanced Tables")
        self.advanced_table_check.setChecked(True)
        table_types_layout.addWidget(self.advanced_table_check)
        
        self.div_table_check = QCheckBox("Div-Based Tables")
        self.div_table_check.setChecked(True)
        table_types_layout.addWidget(self.div_table_check)
        
        table_types_group.setLayout(table_types_layout)
        options_layout.addWidget(table_types_group)
        
        main_layout.addLayout(options_layout)
        
        # Splitter for tables list and preview
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Tables list and info
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.addWidget(QLabel("Available Tables:"))
        
        self.tables_list = QListWidget()
        self.tables_list.itemClicked.connect(self.on_table_selected)
        left_layout.addWidget(self.tables_list)
        
        # Table info section
        self.table_info = QTextBrowser()
        self.table_info.setMaximumHeight(100)
        left_layout.addWidget(QLabel("Table Information:"))
        left_layout.addWidget(self.table_info)
        
        # Download button
        button_layout = QHBoxLayout()
        self.download_button = QPushButton("Save Selected Table")
        self.download_button.clicked.connect(self.save_table)
        self.download_button.setEnabled(False)
        button_layout.addWidget(self.download_button)
        
        # Format selection
        format_layout = QHBoxLayout()
        format_layout.addWidget(QLabel("Format:"))
        self.format_combo = QComboBox()
        self.format_combo.addItems(["Parquet", "CSV", "Excel"])
        format_layout.addWidget(self.format_combo)
        button_layout.addLayout(format_layout)
        
        left_layout.addLayout(button_layout)
        
        splitter.addWidget(left_widget)
        
        # Table preview
        preview_widget = QWidget()
        preview_layout = QVBoxLayout(preview_widget)
        preview_layout.addWidget(QLabel("Table Preview:"))
        self.table_preview = QTableWidget()
        preview_layout.addWidget(self.table_preview)
        
        splitter.addWidget(preview_widget)
        splitter.setSizes([300, 700])
        
        main_layout.addWidget(splitter)
        
        # Set main widget
        central_widget = QWidget()
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)
        
        # Status
        self.statusBar().showMessage("Ready")
    
    def fetch_tables(self):
        """Fetch tables from the URL"""
        url = self.url_input.text().strip()
        if not url:
            self.show_error("Please enter a URL")
            return
            
        self.statusBar().showMessage("Fetching tables...")
        self.tables_list.clear()
        self.table_preview.clear()
        self.table_info.clear()
        self.download_button.setEnabled(False)
        
        # Configure which table types to extract
        extraction_config = {
            "standard": self.standard_table_check.isChecked(),
            "advanced": self.advanced_table_check.isChecked(),
            "div": self.div_table_check.isChecked()
        }
        
        success, message = self.model.load_url(url, extraction_config)
        if success:
            self.update_tables_list()
            self.statusBar().showMessage(message)
        else:
            self.show_error(message)
            self.statusBar().showMessage("Error: " + message)
    
    def update_tables_list(self):
        """Update the tables list widget"""
        tables = self.model.get_tables()
        self.tables_list.clear()
        
        type_icons = {
            "standard": "🔵",  # Standard HTML Tables
            "pandas": "🟢",    # Advanced Tables via pandas
            "div": "🟠"        # Div-based Tables
        }
        
        for table in tables:
            table_type = table.get("type", "unknown")
            icon = type_icons.get(table_type, "⚪")
            display_text = f"{icon} {table['name']}"
            
            item = QListWidgetItem(display_text)
            item.setData(Qt.ItemDataRole.UserRole, table["id"])
            # Store the table type for displaying info later
            item.setData(Qt.ItemDataRole.UserRole + 1, table_type)
            self.tables_list.addItem(item)
    
    def on_table_selected(self, item):
        """Handle table selection"""
        table_id = item.data(Qt.ItemDataRole.UserRole)
        table_type = item.data(Qt.ItemDataRole.UserRole + 1)
        
        df = self.model.get_table_preview(table_id)
        
        if df is not None:
            self.display_dataframe(df)
            self.download_button.setEnabled(True)
            self.download_button.setProperty("table_id", table_id)
            
            # Display table information
            rows, cols = df.shape
            self.table_info.clear()
            
            type_descriptions = {
                "standard": "Standard HTML Table - Extracted from <table> elements in the page",
                "pandas": "Advanced Table - Detected by pandas read_html",
                "div": "Structured Content - Extracted from div-based layouts resembling tables"
            }
            
            type_desc = type_descriptions.get(table_type, "Unknown table type")
            
            info_html = f"""
            <p><b>Type:</b> {type_desc}</p>
            <p><b>Dimensions:</b> {rows} rows × {cols} columns</p>
            <p><b>Column Names:</b> {', '.join(str(col) for col in df.columns[:5])}{' ...' if len(df.columns) > 5 else ''}</p>
            """
            self.table_info.setHtml(info_html)
            
            self.statusBar().showMessage(f"Table {table_id} selected")
        else:
            self.table_preview.clear()
            self.table_info.clear()
            self.download_button.setEnabled(False)
            self.statusBar().showMessage("Error loading table preview")
    
    def display_dataframe(self, df):
        """Display pandas DataFrame in the table widget"""
        self.table_preview.clear()
        
        # Set table dimensions
        rows, cols = df.shape
        self.table_preview.setRowCount(rows)
        self.table_preview.setColumnCount(cols)
        
        # Set headers
        headers = df.columns.tolist()
        self.table_preview.setHorizontalHeaderLabels([str(h) for h in headers])
        
        # Populate data
        for i in range(rows):
            for j in range(cols):
                value = df.iloc[i, j]
                item = QTableWidgetItem(str(value))
                self.table_preview.setItem(i, j, item)
        
        self.table_preview.resizeColumnsToContents()
    
    def save_table(self):
        """Save the selected table to a file"""
        table_id = self.download_button.property("table_id")
        
        if table_id is None:
            self.show_error("No table selected")
            return
        
        selected_format = self.format_combo.currentText()
        file_filter = ""
        file_extension = ""
        
        if selected_format == "Parquet":
            file_filter = "Parquet Files (*.parquet)"
            file_extension = ".parquet"
        elif selected_format == "CSV":
            file_filter = "CSV Files (*.csv)"
            file_extension = ".csv"
        elif selected_format == "Excel":
            file_filter = "Excel Files (*.xlsx)"
            file_extension = ".xlsx"
        
        # Get save filename
        filename, _ = QFileDialog.getSaveFileName(
            self, "Save Table", "", file_filter
        )
        
        if filename:
            # Ensure it has the correct extension
            if not filename.lower().endswith(file_extension.lower()):
                filename += file_extension
                
            success, message = self.model.save_table(table_id, filename, selected_format.lower())
            if success:
                self.statusBar().showMessage(message)
                QMessageBox.information(self, "Success", message)
            else:
                self.show_error(message)
    
    def show_error(self, message):
        """Show error message"""
        QMessageBox.critical(self, "Error", message) 