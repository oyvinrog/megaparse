from PyQt6.QtWidgets import (
    QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QPushButton,
    QLineEdit, QLabel, QListWidget, QListWidgetItem, QMessageBox,
    QTableWidget, QTableWidgetItem, QSplitter, QFileDialog
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
        self.setGeometry(100, 100, 1000, 700)
        
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
        
        # Splitter for tables list and preview
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Tables list
        tables_widget = QWidget()
        tables_layout = QVBoxLayout(tables_widget)
        tables_layout.addWidget(QLabel("Available Tables:"))
        self.tables_list = QListWidget()
        self.tables_list.itemClicked.connect(self.on_table_selected)
        tables_layout.addWidget(self.tables_list)
        
        # Download button
        self.download_button = QPushButton("Save Selected Table")
        self.download_button.clicked.connect(self.save_table)
        self.download_button.setEnabled(False)
        tables_layout.addWidget(self.download_button)
        
        splitter.addWidget(tables_widget)
        
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
        self.download_button.setEnabled(False)
        
        success, message = self.model.load_url(url)
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
        
        for table in tables:
            item = QListWidgetItem(table["name"])
            item.setData(Qt.ItemDataRole.UserRole, table["id"])
            self.tables_list.addItem(item)
    
    def on_table_selected(self, item):
        """Handle table selection"""
        table_id = item.data(Qt.ItemDataRole.UserRole)
        df = self.model.get_table_preview(table_id)
        
        if df is not None:
            self.display_dataframe(df)
            self.download_button.setEnabled(True)
            self.download_button.setProperty("table_id", table_id)
            self.statusBar().showMessage(f"Table {table_id} selected")
        else:
            self.table_preview.clear()
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
        """Save the selected table to a parquet file"""
        table_id = self.download_button.property("table_id")
        
        if table_id is None:
            self.show_error("No table selected")
            return
        
        # Get save filename
        filename, _ = QFileDialog.getSaveFileName(
            self, "Save Table", "", "Parquet Files (*.parquet)"
        )
        
        if filename:
            success, message = self.model.save_table(table_id, filename)
            if success:
                self.statusBar().showMessage(message)
                QMessageBox.information(self, "Success", message)
            else:
                self.show_error(message)
    
    def show_error(self, message):
        """Show error message"""
        QMessageBox.critical(self, "Error", message) 