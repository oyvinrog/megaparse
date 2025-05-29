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
        
        # Splitter for tables list, scores, and preview
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Tables list and info
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.addWidget(QLabel("Available Tables:"))
        
        self.tables_list = QListWidget()
        self.tables_list.itemClicked.connect(self.on_table_selected)
        self.tables_list.currentItemChanged.connect(self.on_table_selected)
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
        
        # Score visualization panel
        score_widget = QWidget()
        score_layout = QVBoxLayout(score_widget)
        score_layout.addWidget(QLabel("Table Entropy Scores:"))
        
        self.score_list = QListWidget()
        score_layout.addWidget(self.score_list)
        
        splitter.addWidget(score_widget)
        
        # Table preview
        preview_widget = QWidget()
        preview_layout = QVBoxLayout(preview_widget)
        preview_layout.addWidget(QLabel("Table Preview:"))
        self.table_preview = QTableWidget()
        self.table_preview.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        preview_layout.addWidget(self.table_preview)
        
        splitter.addWidget(preview_widget)
        splitter.setSizes([300, 200, 700])
        
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
        self.score_list.clear()
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
            self.update_score_list()
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
        if not item:
            return
            
        table_id = item.data(Qt.ItemDataRole.UserRole)
        table_type = item.data(Qt.ItemDataRole.UserRole + 1)
        
        df = self.model.get_table_preview(table_id, max_rows=100)
        
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
        
        self.table_preview.setHorizontalHeaderLabels([""] * cols)  # Set empty labels first
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

    def update_score_list(self):
        """Update the score visualization panel"""
        self.score_list.clear()
        scores = self.model.get_table_scores()
        
        for score_info in scores:
            item = QListWidgetItem()
            widget = QWidget()
            layout = QVBoxLayout(widget)
            
            # Table name and dimensions
            info_label = QLabel(f"{score_info['name']} ({score_info['rows']}×{score_info['cols']})")
            layout.addWidget(info_label)
            
            # Score bar
            score_bar = ScoreBar(score_info['entropy'])
            layout.addWidget(score_bar)
            
            widget.setLayout(layout)
            item.setSizeHint(widget.sizeHint())
            
            self.score_list.addItem(item)
            self.score_list.setItemWidget(item, widget) 