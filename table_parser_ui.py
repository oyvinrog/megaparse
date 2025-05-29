from PyQt6.QtWidgets import (
    QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QPushButton,
    QLineEdit, QLabel, QListWidget, QListWidgetItem, QMessageBox,
    QTableWidget, QTableWidgetItem, QSplitter, QFileDialog,
    QComboBox, QCheckBox, QGroupBox, QTextBrowser, QProgressBar
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPainter, QColor, QPen
import pandas as pd
import numpy as np
from scipy.stats import entropy

class ScoreBar(QWidget):
    def __init__(self, score, parent=None):
        super().__init__(parent)
        self.score = score
        self.setMinimumHeight(20)
        self.setMaximumHeight(20)
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw background
        painter.fillRect(self.rect(), QColor(240, 240, 240))
        
        # Draw score bar
        bar_width = int(self.width() * self.score)
        bar_rect = self.rect()
        bar_rect.setWidth(bar_width)
        
        # Color gradient based on score
        if self.score < 0.3:
            color = QColor(255, 100, 100)  # Red for low scores
        elif self.score < 0.7:
            color = QColor(255, 200, 100)  # Orange for medium scores
        else:
            color = QColor(100, 200, 100)  # Green for high scores
            
        painter.fillRect(bar_rect, color)
        
        # Draw score text
        painter.setPen(QPen(Qt.GlobalColor.black))
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, f"{self.score:.2f}")

class TableListWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Available Tables:"))
        
        self.tables_list = QListWidget()
        layout.addWidget(self.tables_list)
        
        # Table info section
        self.table_info = QTextBrowser()
        self.table_info.setMaximumHeight(100)
        layout.addWidget(QLabel("Table Information:"))
        layout.addWidget(self.table_info)
        
        # Download button
        button_layout = QHBoxLayout()
        self.download_button = QPushButton("Save Selected Table")
        self.download_button.setEnabled(False)
        button_layout.addWidget(self.download_button)
        
        # Format selection
        format_layout = QHBoxLayout()
        format_layout.addWidget(QLabel("Format:"))
        self.format_combo = QComboBox()
        self.format_combo.addItems(["Parquet", "CSV", "Excel"])
        format_layout.addWidget(self.format_combo)
        button_layout.addLayout(format_layout)
        
        layout.addLayout(button_layout)
    
    def update_tables_list(self, tables, scores):
        self.tables_list.clear()
        
        type_icons = {
            "standard": "🔵",  # Standard HTML Tables
            "pandas": "🟢",    # Advanced Tables via pandas
            "div": "🟠"        # Div-based Tables
        }
        
        # Create a mapping of table IDs to their entropy scores
        score_map = {score["id"]: score["entropy"] for score in scores}
        
        for table in tables:
            table_type = table.get("type", "unknown")
            icon = type_icons.get(table_type, "⚪")
            entropy_score = score_map.get(table["id"], 0)
            
            # Create a colored indicator based on entropy
            if entropy_score < 0.3:
                entropy_indicator = "🔴"  # Red for low entropy
            elif entropy_score < 0.7:
                entropy_indicator = "🟡"  # Yellow for medium entropy
            else:
                entropy_indicator = "🟢"  # Green for high entropy
                
            display_text = f"{icon} {entropy_indicator} {table['name']}"
            
            item = QListWidgetItem(display_text)
            item.setData(Qt.ItemDataRole.UserRole, table["id"])
            item.setData(Qt.ItemDataRole.UserRole + 1, table_type)
            self.tables_list.addItem(item)
    
    def update_table_info(self, df, table_type):
        if df is not None:
            rows, cols = df.shape
            
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
        else:
            self.table_info.clear()

class TablePreviewWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Table Preview:"))
        self.table_preview = QTableWidget()
        self.table_preview.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        layout.addWidget(self.table_preview)
    
    def display_dataframe(self, df):
        """Display pandas DataFrame in the table widget"""
        self.table_preview.clear()
        
        if df is None:
            return
            
        # Set table dimensions
        rows, cols = df.shape
        self.table_preview.setRowCount(rows)
        self.table_preview.setColumnCount(cols)
        
        # Calculate entropy for each column
        column_entropies = []
        for col in df.columns:
            try:
                # Convert column to string and count frequencies
                value_counts = df[col].fillna('').astype(str).value_counts()
                if len(value_counts) > 1:
                    e = entropy(value_counts)
                    max_entropy = np.log(len(value_counts))
                    normalized_entropy = e / max_entropy if max_entropy > 0 else 0
                else:
                    normalized_entropy = 0
            except:
                normalized_entropy = 0
            column_entropies.append(normalized_entropy)
        
        # Set headers with entropy information
        headers = []
        for j, col in enumerate(df.columns):
            # Create header text with entropy score
            entropy_score = column_entropies[j]
            header_text = f"{col}\n{entropy_score:.2f}"
            
            # Create header item
            header_item = QTableWidgetItem(header_text)
            
            # Set background color based on entropy
            if entropy_score < 0.3:
                color = QColor(255, 200, 200)  # Light red for low entropy
            elif entropy_score < 0.7:
                color = QColor(255, 255, 200)  # Light yellow for medium entropy
            else:
                color = QColor(200, 255, 200)  # Light green for high entropy
            
            header_item.setBackground(color)
            headers.append(header_item)
        
        self.table_preview.setHorizontalHeaderLabels([""] * cols)
        for j, header_item in enumerate(headers):
            self.table_preview.setHorizontalHeaderItem(j, header_item)
        
        # Populate data
        for i in range(rows):
            for j in range(cols):
                value = df.iloc[i, j]
                item = QTableWidgetItem(str(value))
                self.table_preview.setItem(i, j, item)
        
        # Adjust header height to accommodate entropy score
        header = self.table_preview.horizontalHeader()
        current_size = header.defaultSectionSize()
        header.setDefaultSectionSize(int(current_size * 1.5))
        
        self.table_preview.resizeColumnsToContents()

class TableParserUI(QMainWindow):
    def __init__(self, model):
        super().__init__()
        self.model = model
        self.init_ui()
        
        # Load previously used URL into the URL textbox
        last_url = self.model.get_last_url()
        if last_url:
            self.url_input.setText(last_url)
        
    def init_ui(self):
        """Initialize user interface"""
        self.setWindowTitle("Web Table Parser")
        self.setGeometry(100, 100, 1400, 800)
        
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
        
        # Splitter for tables list and preview (removed scores)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Initialize components
        self.table_list_widget = TableListWidget()
        self.preview_widget = TablePreviewWidget()
        
        # Connect signals
        self.table_list_widget.tables_list.itemClicked.connect(self.on_table_selected)
        self.table_list_widget.tables_list.currentItemChanged.connect(self.on_table_selected)
        self.table_list_widget.download_button.clicked.connect(self.save_table)
        
        # Add widgets to splitter (removed score_widget)
        splitter.addWidget(self.table_list_widget)
        splitter.addWidget(self.preview_widget)
        splitter.setSizes([400, 1000])
        
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
        self.table_list_widget.tables_list.clear()
        self.preview_widget.table_preview.clear()
        self.table_list_widget.table_info.clear()
        self.table_list_widget.download_button.setEnabled(False)
        
        # Configure which table types to extract
        extraction_config = {
            "standard": self.standard_table_check.isChecked(),
            "advanced": self.advanced_table_check.isChecked(),
            "div": self.div_table_check.isChecked()
        }
        
        success, message = self.model.load_url(url, extraction_config)
        if success:
            self.update_ui()
            self.statusBar().showMessage(message)
        else:
            self.show_error(message)
            self.statusBar().showMessage("Error: " + message)
    
    def update_ui(self):
        """Update all UI components with current model state"""
        tables = self.model.get_tables()
        scores = self.model.get_table_scores()
        
        self.table_list_widget.update_tables_list(tables, scores)
    
    def on_table_selected(self, item):
        """Handle table selection"""
        if not item:
            return
            
        table_id = item.data(Qt.ItemDataRole.UserRole)
        table_type = item.data(Qt.ItemDataRole.UserRole + 1)
        
        df = self.model.get_table_preview(table_id, max_rows=100)
        
        if df is not None:
            self.preview_widget.display_dataframe(df)
            self.table_list_widget.download_button.setEnabled(True)
            self.table_list_widget.download_button.setProperty("table_id", table_id)
            self.table_list_widget.update_table_info(df, table_type)
            self.statusBar().showMessage(f"Table {table_id} selected")
        else:
            self.preview_widget.table_preview.clear()
            self.table_list_widget.table_info.clear()
            self.table_list_widget.download_button.setEnabled(False)
            self.statusBar().showMessage("Error loading table preview")
    
    def save_table(self):
        """Save the selected table to a file"""
        table_id = self.table_list_widget.download_button.property("table_id")
        
        if table_id is None:
            self.show_error("No table selected")
            return
        
        selected_format = self.table_list_widget.format_combo.currentText()
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