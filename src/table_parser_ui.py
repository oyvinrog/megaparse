from PyQt6.QtWidgets import (
    QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QPushButton,
    QLineEdit, QLabel, QListWidget, QListWidgetItem, QMessageBox,
    QTableWidget, QTableWidgetItem, QSplitter, QFileDialog,
    QComboBox, QCheckBox, QGroupBox, QTextBrowser, QProgressBar, QMenu,
    QInputDialog, QMenuBar
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPainter, QColor, QPen, QPalette, QFont, QIcon
import pandas as pd
import numpy as np
from scipy.stats import entropy
import os

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
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Title with modern styling
        title_label = QLabel("Available Tables")
        title_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        layout.addWidget(title_label)
        
        self.tables_list = QListWidget()
        self.tables_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self.tables_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tables_list.customContextMenuRequested.connect(self.show_context_menu)
        self.tables_list.keyPressEvent = self.handle_key_press
        layout.addWidget(self.tables_list)
        
        # Table info section with modern styling
        info_label = QLabel("Table Information")
        info_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        layout.addWidget(info_label)
        
        self.table_info = QTextBrowser()
        self.table_info.setMaximumHeight(100)
        self.table_info.setStyleSheet("""
            QTextBrowser {
                background-color: #3b3b3b;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 10px;
                color: #ffffff;
                font-size: 12px;
            }
        """)
        layout.addWidget(self.table_info)
        
        # Button layout with modern styling
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        # Delete button
        self.delete_button = QPushButton("Delete Selected")
        self.delete_button.setEnabled(False)
        self.delete_button.setMinimumHeight(35)
        self.delete_button.clicked.connect(self.delete_selected_tables)
        button_layout.addWidget(self.delete_button)
        
        # Add SQLite button
        self.sqlite_button = QPushButton("Open in SQLite")
        self.sqlite_button.setMinimumHeight(35)
        button_layout.addWidget(self.sqlite_button)
        
        # Remove others button
        self.remove_others_button = QPushButton("Remove Other Tables")
        self.remove_others_button.setEnabled(False)
        self.remove_others_button.setMinimumHeight(35)
        self.remove_others_button.clicked.connect(self.remove_other_tables)
        button_layout.addWidget(self.remove_others_button)
        
        # Download button
        self.download_button = QPushButton("Save Selected Table")
        self.download_button.setEnabled(False)
        self.download_button.setMinimumHeight(35)
        button_layout.addWidget(self.download_button)
        
        # Format selection with modern styling
        format_layout = QHBoxLayout()
        format_layout.setSpacing(10)
        
        format_label = QLabel("Format:")
        format_label.setFont(QFont("Arial", 12))
        format_layout.addWidget(format_label)
        
        self.format_combo = QComboBox()
        self.format_combo.setMinimumHeight(35)
        self.format_combo.addItems(["Parquet", "CSV", "Excel"])
        format_layout.addWidget(self.format_combo)
        
        button_layout.addLayout(format_layout)
        layout.addLayout(button_layout)
        
        # Connect selection changed signal
        self.tables_list.itemSelectionChanged.connect(self.on_selection_changed)
    
    def show_context_menu(self, position):
        """Show context menu for table list"""
        menu = QMenu()
        rename_action = menu.addAction("Rename")
        rename_action.triggered.connect(self.rename_selected_table)
        menu.addSeparator()
        delete_action = menu.addAction("Delete Selected")
        delete_action.triggered.connect(self.delete_selected_tables)
        menu.addSeparator()
        remove_others_action = menu.addAction("Remove Other Tables")
        remove_others_action.triggered.connect(self.remove_other_tables)
        menu.exec(self.tables_list.mapToGlobal(position))
    
    def delete_selected_tables(self):
        """Delete selected tables"""
        selected_items = self.tables_list.selectedItems()
        if not selected_items:
            return
            
        # Get parent window to access model
        parent = self.window()
        if not isinstance(parent, TableParserUI):
            return
            
        # Delete tables
        count = len(selected_items)
        for item in selected_items:
            table_id = item.data(Qt.ItemDataRole.UserRole)
            parent.model.remove_table(table_id)
        
        # Update UI
        parent.update_ui()
        parent.statusBar().showMessage(f"Deleted {count} table{'s' if count > 1 else ''}")
        
        # Clear preview if current table was deleted
        if parent.current_table_id not in [table["id"] for table in parent.model.get_tables()]:
            parent.preview_widget.table_preview.clear()
            self.table_info.clear()
            parent.current_table_id = None
    
    def remove_other_tables(self):
        """Remove all tables except the selected ones"""
        selected_items = self.tables_list.selectedItems()
        if not selected_items:
            return
            
        # Get parent window to access model
        parent = self.window()
        if not isinstance(parent, TableParserUI):
            return
            
        # Get the selected table IDs
        table_ids = [item.data(Qt.ItemDataRole.UserRole) for item in selected_items]
        
        # Remove other tables
        count = parent.model.remove_other_tables(table_ids)
        
        # Update UI
        parent.update_ui()
        parent.statusBar().showMessage(f"Removed {count} other table{'s' if count > 1 else ''}")
    
    def on_selection_changed(self):
        """Handle selection changes"""
        selected_items = self.tables_list.selectedItems()
        self.delete_button.setEnabled(len(selected_items) > 0)
        self.download_button.setEnabled(len(selected_items) == 1)
        self.remove_others_button.setEnabled(len(selected_items) > 0)
    
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
    
    def handle_key_press(self, event):
        """Handle key press events"""
        if event.key() == Qt.Key.Key_Delete:
            self.delete_selected_tables()
        elif event.key() == Qt.Key.Key_F2:
            self.rename_selected_table()
        else:
            # Call the original keyPressEvent for other keys
            QListWidget.keyPressEvent(self.tables_list, event)

    def rename_selected_table(self):
        """Rename the selected table"""
        selected_items = self.tables_list.selectedItems()
        if not selected_items:
            return
            
        # Get parent window to access model
        parent = self.window()
        if not isinstance(parent, TableParserUI):
            return
            
        # Get the first selected item
        item = selected_items[0]
        table_id = item.data(Qt.ItemDataRole.UserRole)
        current_name = item.text().split(' ', 2)[-1]  # Remove icons and get just the name
        
        # Show rename dialog
        new_name, ok = QInputDialog.getText(
            self, "Rename Table", "Enter new name:", 
            QLineEdit.EchoMode.Normal, current_name
        )
        
        if ok and new_name and new_name != current_name:
            # Update model
            if parent.model.rename_table(table_id, new_name):
                # Update UI
                parent.update_ui()
                parent.statusBar().showMessage(f"Table renamed to: {new_name}")
            else:
                QMessageBox.warning(self, "Error", "Failed to rename table")

    def reload_data(self):
        """Reload the current URL data"""
        if not self.model.url:
            self.show_error("No URL to reload")
            return
            
        self.statusBar().showMessage("Reloading data...")
        self.table_list_widget.tables_list.clear()
        self.preview_widget.table_preview.clear()
        self.table_list_widget.table_info.clear()
        self.table_list_widget.download_button.setEnabled(False)
        
        success, message = self.model.reload()
        if success:
            self.update_ui()
            self.update_steps_list()
            self.statusBar().showMessage(message)
        else:
            self.show_error(message)
            self.statusBar().showMessage("Error: " + message)

class TablePreviewWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        self.max_columns_for_full_processing = 50  # Threshold for full header processing
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Title with modern styling
        title_label = QLabel("Table Preview")
        title_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        layout.addWidget(title_label)
        
        # Add numeric column highlighting checkbox
        self.highlight_numeric_check = QCheckBox("Highlight Numeric Columns")
        self.highlight_numeric_check.setChecked(True)
        self.highlight_numeric_check.stateChanged.connect(self.on_highlight_numeric_changed)
        layout.addWidget(self.highlight_numeric_check)
        
        self.table_preview = QTableWidget()
        self.table_preview.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.table_preview.setStyleSheet("""
            QTableWidget {
                background-color: #3b3b3b;
                border: 1px solid #555555;
                border-radius: 4px;
                gridline-color: #555555;
            }
            QTableWidget::item {
                padding: 8px;
                color: #ffffff;
            }
            QTableWidget::item:selected {
                background-color: #1565c0;
            }
            QHeaderView::section {
                background-color: #424242;
                color: white;
                padding: 8px;
                border: 1px solid #555555;
                font-weight: bold;
            }
            QScrollBar:vertical {
                border: none;
                background: #3b3b3b;
                width: 10px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #555555;
                min-height: 20px;
                border-radius: 5px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QScrollBar:horizontal {
                border: none;
                background: #3b3b3b;
                height: 10px;
                margin: 0px;
            }
            QScrollBar::handle:horizontal {
                background: #555555;
                min-width: 20px;
                border-radius: 5px;
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                width: 0px;
            }
        """)
        layout.addWidget(self.table_preview)
    
    def is_numeric_column(self, series):
        """Check if a column has a high percentage of numeric values"""
        if not isinstance(series, pd.Series):
            return False
            
        total_values = len(series)
        if total_values == 0:
            return False
            
        # Try to convert to numeric, non-numeric values will become NaN
        try:
            numeric_values = pd.to_numeric(series, errors='coerce')
            numeric_count = numeric_values.notna().sum()
            numeric_percentage = numeric_count / total_values
            return numeric_percentage >= 0.7  # 70% threshold for numeric columns
        except:
            return False
    
    def on_highlight_numeric_changed(self, state):
        """Handle numeric highlighting checkbox state change"""
        if hasattr(self, 'current_df'):
            self.display_dataframe(self.current_df)
    
    def display_dataframe(self, df):
        """Display pandas DataFrame in the table widget with numeric column highlighting"""
        self.table_preview.clear()
        self.current_df = df  # Store current dataframe
        
        if df is None:
            return
            
        # Set table dimensions
        rows, cols = df.shape
        self.table_preview.setRowCount(rows)
        self.table_preview.setColumnCount(cols)
        
        # For tables with many columns, use simplified header processing
        if cols > self.max_columns_for_full_processing:
            # Set simple headers without entropy/numeric processing
            headers = []
            for col in df.columns:
                header_item = QTableWidgetItem(str(col))
                header_item.setBackground(QColor(200, 255, 200))  # Light green for all headers
                headers.append(header_item)
        else:
            # Calculate entropy and numeric status for each column
            column_entropies = []
            numeric_columns = []
            for col in df.columns:
                # Calculate entropy
                try:
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
                
                # Check if column is numeric
                is_numeric = self.is_numeric_column(df[col])
                numeric_columns.append(is_numeric)
            
            # Set headers with entropy and numeric information
            headers = []
            for j, col in enumerate(df.columns):
                # Create header text with entropy score and numeric indicator
                entropy_score = column_entropies[j]
                is_numeric = numeric_columns[j]
                header_text = f"{col}\n{entropy_score:.2f}"
                if is_numeric and self.highlight_numeric_check.isChecked():
                    header_text += " 🔢"  # Add numeric indicator
                    
                # Create header item
                header_item = QTableWidgetItem(header_text)
                
                # Set background color based on entropy and numeric status
                if is_numeric and self.highlight_numeric_check.isChecked():
                    color = QColor(200, 200, 255)  # Light blue for numeric columns
                elif entropy_score < 0.3:
                    color = QColor(255, 200, 200)  # Light red for low entropy
                elif entropy_score < 0.7:
                    color = QColor(255, 255, 200)  # Light yellow for medium entropy
                else:
                    color = QColor(200, 255, 200)  # Light green for high entropy
                
                header_item.setBackground(color)
                headers.append(header_item)
        
        # Set headers
        self.table_preview.setHorizontalHeaderLabels([""] * cols)
        for j, header_item in enumerate(headers):
            self.table_preview.setHorizontalHeaderItem(j, header_item)
        
        # Populate data with numeric column highlighting
        for i in range(rows):
            for j in range(cols):
                value = df.iloc[i, j]
                item = QTableWidgetItem(str(value))
                
                # Only apply numeric highlighting if we did full processing
                if cols <= self.max_columns_for_full_processing and numeric_columns[j] and self.highlight_numeric_check.isChecked():
                    try:
                        float(str(value))  # Try to convert to float
                        item.setForeground(QColor(150, 200, 255))  # Light blue text for numeric values
                    except (ValueError, TypeError):
                        pass  # Not a numeric value, keep default color
                
                self.table_preview.setItem(i, j, item)
        
        # Adjust header height to accommodate entropy score and numeric indicator
        header = self.table_preview.horizontalHeader()
        current_size = header.defaultSectionSize()
        header.setDefaultSectionSize(int(current_size * 1.5))
        
        # Only resize columns if we have a reasonable number of columns
        if cols <= self.max_columns_for_full_processing:
            self.table_preview.resizeColumnsToContents()
        else:
            # Set a reasonable default width for many columns
            header.setDefaultSectionSize(100)
    
    def display_dataframe_with_similarity(self, df, similarity_scores, header_labels=None, header_row_index=None):
        """Display pandas DataFrame with similarity-based coloring and custom header labels if provided."""
        self.table_preview.clear()
        if df is None:
            return
        rows, cols = df.shape
        self.table_preview.setRowCount(rows)
        self.table_preview.setColumnCount(cols)
        # Set headers with similarity information
        headers = []
        labels = header_labels if header_labels is not None else df.columns
        for j, col in enumerate(labels):
            similarity_score = similarity_scores[j]
            header_text = f"{col}\n{similarity_score:.2f}"
            header_item = QTableWidgetItem(header_text)
            if similarity_score < 0.3:
                color = QColor(255, 200, 200)
            elif similarity_score < 0.7:
                color = QColor(255, 255, 200)
            else:
                color = QColor(200, 255, 200)
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
        # Adjust header height
        header = self.table_preview.horizontalHeader()
        current_size = header.defaultSectionSize()
        header.setDefaultSectionSize(int(current_size * 1.5))
        self.table_preview.resizeColumnsToContents()
        # Show a note if header row is not the default
        if header_row_index is not None:
            note = QLabel(f"Header row detected at row {header_row_index+1} (highlighted above)")
            note.setStyleSheet("color: #888; font-size: 11px;")
            layout = self.layout()
            if layout.count() < 3:
                layout.addWidget(note)
            else:
                # Replace previous note
                layout.itemAt(2).widget().setText(note.text())

    def display_dataframe_with_numeric(self, df, numeric_scores):
        """Display pandas DataFrame with numeric-based coloring"""
        self.table_preview.clear()
        if df is None:
            return
            
        rows, cols = df.shape
        self.table_preview.setRowCount(rows)
        self.table_preview.setColumnCount(cols)
        
        # Set headers with numeric information
        headers = []
        for j, col in enumerate(df.columns):
            numeric_score = numeric_scores[j]
            header_text = f"{col}\n{numeric_score:.2f}"
            if numeric_score >= 0.7:
                header_text += " 🔢"  # Add numeric indicator
                
            header_item = QTableWidgetItem(header_text)
            
            # Set background color based on numeric score
            if numeric_score >= 0.7:
                color = QColor(200, 200, 255)  # Light blue for high numeric percentage
            elif numeric_score >= 0.3:
                color = QColor(255, 255, 200)  # Light yellow for medium numeric percentage
            else:
                color = QColor(255, 200, 200)  # Light red for low numeric percentage
            
            header_item.setBackground(color)
            headers.append(header_item)
        
        self.table_preview.setHorizontalHeaderLabels([""] * cols)
        for j, header_item in enumerate(headers):
            self.table_preview.setHorizontalHeaderItem(j, header_item)
        
        # Populate data with numeric highlighting
        for i in range(rows):
            for j in range(cols):
                value = df.iloc[i, j]
                item = QTableWidgetItem(str(value))
                
                # Color numeric values in numeric columns
                if numeric_scores[j] >= 0.7:
                    try:
                        float(str(value))  # Try to convert to float
                        item.setForeground(QColor(150, 200, 255))  # Light blue text for numeric values
                    except (ValueError, TypeError):
                        pass  # Not a numeric value, keep default color
                
                self.table_preview.setItem(i, j, item)
        
        # Adjust header height
        header = self.table_preview.horizontalHeader()
        current_size = header.defaultSectionSize()
        header.setDefaultSectionSize(int(current_size * 1.5))
        
        self.table_preview.resizeColumnsToContents()

class TableParserUI(QMainWindow):
    def __init__(self, model):
        super().__init__()
        self.model = model
        self.setup_style()
        self.init_ui()
        
        # Load URL into the URL textbox, prioritizing model's URL over last used URL
        if self.model.url:
            self.url_input.setText(self.model.url)
        else:
            last_url = self.model.get_last_url()
            if last_url:
                self.url_input.setText(last_url)
        
        # Connect table selection signals
        self.table_list_widget.tables_list.itemClicked.connect(self.on_table_selected)
        self.table_list_widget.tables_list.currentItemChanged.connect(self.on_table_selected)
        self.table_list_widget.download_button.clicked.connect(self.save_table)
        self.table_list_widget.sqlite_button.clicked.connect(self.open_in_sqlite)
        
        # Create progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.statusBar().addPermanentWidget(self.progress_bar)

    def setup_style(self):
        """Setup modern dark theme and styling"""
        # Set window icon
        self.setWindowIcon(QIcon.fromTheme("document-open"))
        
        # Set dark theme colors
        self.setStyleSheet("""
            QMainWindow {
                background-color: #2b2b2b;
            }
            QWidget {
                background-color: #2b2b2b;
                color: #ffffff;
            }
            QLabel {
                color: #ffffff;
                font-size: 12px;
            }
            QLineEdit {
                background-color: #3b3b3b;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 5px;
                color: #ffffff;
                font-size: 12px;
            }
            QPushButton {
                background-color: #0d47a1;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1565c0;
            }
            QPushButton:disabled {
                background-color: #424242;
                color: #757575;
            }
            QListWidget {
                background-color: #3b3b3b;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 5px;
            }
            QListWidget::item {
                padding: 5px;
                border-bottom: 1px solid #555555;
            }
            QListWidget::item:selected {
                background-color: #1565c0;
            }
            QTableWidget {
                background-color: #3b3b3b;
                border: 1px solid #555555;
                border-radius: 4px;
                gridline-color: #555555;
            }
            QTableWidget::item {
                padding: 5px;
            }
            QTableWidget::item:selected {
                background-color: #1565c0;
            }
            QHeaderView::section {
                background-color: #424242;
                color: white;
                padding: 5px;
                border: 1px solid #555555;
            }
            QComboBox {
                background-color: #3b3b3b;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 5px;
                color: white;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                image: none;
                border: none;
            }
            QCheckBox {
                color: white;
                spacing: 5px;
            }
            QCheckBox::indicator {
                width: 15px;
                height: 15px;
            }
            QCheckBox::indicator:unchecked {
                border: 1px solid #555555;
                background-color: #3b3b3b;
            }
            QCheckBox::indicator:checked {
                background-color: #0d47a1;
                border: 1px solid #0d47a1;
            }
            QTextBrowser {
                background-color: #3b3b3b;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 5px;
            }
            QMenuBar {
                background-color: #2b2b2b;
                color: white;
            }
            QMenuBar::item {
                background-color: #2b2b2b;
                color: white;
                padding: 5px 10px;
            }
            QMenuBar::item:selected {
                background-color: #1565c0;
            }
            QMenu {
                background-color: #3b3b3b;
                color: white;
                border: 1px solid #555555;
            }
            QMenu::item {
                padding: 5px 20px;
            }
            QMenu::item:selected {
                background-color: #1565c0;
            }
            QStatusBar {
                background-color: #1a1a1a;
                color: #ffffff;
                border-top: 1px solid #555555;
                padding: 5px;
                font-size: 12px;
                font-weight: bold;
            }
        """)

    def init_ui(self):
        """Initialize user interface"""
        self.setWindowTitle("Table Parser")
        self.setGeometry(100, 100, 1200, 800)
        
        # Create menu bar with modern styling
        self.menubar = self.menuBar()
        self.menubar.setNativeMenuBar(False)
        
        # Initialize status bar with a permanent message
        self.statusBar().setStyleSheet("""
            QStatusBar {
                background-color: #1a1a1a;
                color: #ffffff;
                border-top: 1px solid #555555;
                padding: 5px;
                font-size: 12px;
                font-weight: bold;
            }
        """)
        self.statusBar().showMessage("Ready")
        
        # File menu
        file_menu = self.menubar.addMenu("&File")
        
        # Add menu items with icons
        new_action = file_menu.addAction(QIcon.fromTheme("document-new"), "&New Project")
        new_action.setShortcut("Ctrl+N")
        new_action.triggered.connect(self.new_project)
        
        open_action = file_menu.addAction(QIcon.fromTheme("document-open"), "&Open Project...")
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self.load_project)
        
        save_action = file_menu.addAction(QIcon.fromTheme("document-save"), "&Save Project")
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self.save_project)
        
        save_as_action = file_menu.addAction(QIcon.fromTheme("document-save-as"), "Save Project &As...")
        save_as_action.setShortcut("Ctrl+Shift+S")
        save_as_action.triggered.connect(self.save_project_as)
        
        reload_action = file_menu.addAction(QIcon.fromTheme("view-refresh"), "&Reload All")
        reload_action.setShortcut("Ctrl+R")
        reload_action.triggered.connect(self.reload_all)
        
        file_menu.addSeparator()
        
        self.recent_menu = file_menu.addMenu(QIcon.fromTheme("document-open-recent"), "Recent &Projects")
        self.update_recent_projects()
        
        file_menu.addSeparator()
        
        exit_action = file_menu.addAction(QIcon.fromTheme("application-exit"), "E&xit")
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)

        # Main layout with modern spacing
        main_layout = QVBoxLayout()
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # URL input section with modern styling
        url_layout = QHBoxLayout()
        url_layout.setSpacing(10)
        
        url_label = QLabel("URL:")
        url_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        url_layout.addWidget(url_label)
        
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Enter URL to parse tables from...")
        self.url_input.setMinimumHeight(35)
        url_layout.addWidget(self.url_input)
        
        # Modern button styling
        self.fetch_button = QPushButton("Fetch Tables")
        self.fetch_button.setMinimumHeight(35)
        self.fetch_button.clicked.connect(self.fetch_tables)
        url_layout.addWidget(self.fetch_button)
        
        # Project buttons with consistent styling
        self.new_project_button = QPushButton("New Project")
        self.new_project_button.setMinimumHeight(35)
        self.new_project_button.clicked.connect(self.new_project)
        url_layout.addWidget(self.new_project_button)
        
        self.save_project_button = QPushButton("Save Project")
        self.save_project_button.setMinimumHeight(35)
        self.save_project_button.clicked.connect(self.save_project)
        url_layout.addWidget(self.save_project_button)
        
        self.load_project_button = QPushButton("Load Project")
        self.load_project_button.setMinimumHeight(35)
        self.load_project_button.clicked.connect(self.load_project)
        url_layout.addWidget(self.load_project_button)
        
        # Add Reload All button
        self.reload_all_button = QPushButton("Reload All")
        self.reload_all_button.setMinimumHeight(35)
        self.reload_all_button.clicked.connect(self.reload_all)
        url_layout.addWidget(self.reload_all_button)
        
        main_layout.addLayout(url_layout)
        
        # Table type selection with modern styling
        type_layout = QHBoxLayout()
        type_layout.setSpacing(15)
        
        type_label = QLabel("Table Types:")
        type_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        type_layout.addWidget(type_label)
        
        self.standard_table_check = QCheckBox("Standard Tables")
        self.standard_table_check.setChecked(True)
        type_layout.addWidget(self.standard_table_check)
        
        self.advanced_table_check = QCheckBox("Advanced Tables")
        self.advanced_table_check.setChecked(True)
        type_layout.addWidget(self.advanced_table_check)
        
        self.div_table_check = QCheckBox("Div-based Tables")
        self.div_table_check.setChecked(True)
        type_layout.addWidget(self.div_table_check)
        
        self.remove_low_score_button = QPushButton("Remove Low Score Tables")
        self.remove_low_score_button.setMinimumHeight(35)
        self.remove_low_score_button.clicked.connect(self.remove_low_score_tables)
        type_layout.addWidget(self.remove_low_score_button)
        
        main_layout.addLayout(type_layout)
        
        # Column similarity input with modern styling
        similarity_layout = QHBoxLayout()
        similarity_layout.setSpacing(10)
        
        similarity_label = QLabel("Color by Similarity:")
        similarity_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        similarity_layout.addWidget(similarity_label)
        
        self.similarity_input = QLineEdit()
        self.similarity_input.setPlaceholderText("e.g., price, date, name")
        self.similarity_input.setMinimumHeight(35)
        self.similarity_input.returnPressed.connect(self.update_table_colors)
        similarity_layout.addWidget(self.similarity_input)
        
        self.apply_similarity_button = QPushButton("Apply Similarity")
        self.apply_similarity_button.setMinimumHeight(35)
        self.apply_similarity_button.clicked.connect(self.update_table_colors)
        similarity_layout.addWidget(self.apply_similarity_button)
        
        main_layout.addLayout(similarity_layout)
        
        # Numeric column button with modern styling
        numeric_layout = QHBoxLayout()
        numeric_layout.setSpacing(10)
        
        numeric_label = QLabel("Highlight Numeric Tables:")
        numeric_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        numeric_layout.addWidget(numeric_label)
        
        self.apply_numeric_button = QPushButton("Apply Numeric Highlighting")
        self.apply_numeric_button.setMinimumHeight(35)
        self.apply_numeric_button.clicked.connect(self.update_numeric_colors)
        numeric_layout.addWidget(self.apply_numeric_button)
        
        main_layout.addLayout(numeric_layout)
        
        # Splitter with modern styling
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(2)
        splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: #555555;
            }
        """)
        
        # Initialize components with modern styling
        self.table_list_widget = TableListWidget()
        self.preview_widget = TablePreviewWidget()
        
        # Create steps list widget with modern styling
        steps_widget = QWidget()
        steps_layout = QVBoxLayout(steps_widget)
        steps_layout.setSpacing(10)
        
        steps_label = QLabel("Operation History:")
        steps_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        steps_layout.addWidget(steps_label)
        
        self.steps_list = QListWidget()
        self.steps_list.setMinimumWidth(250)
        steps_layout.addWidget(self.steps_list)
        
        # Add widgets to splitter
        splitter.addWidget(self.table_list_widget)
        splitter.addWidget(self.preview_widget)
        splitter.addWidget(steps_widget)
        splitter.setSizes([400, 1000, 300])
        
        main_layout.addWidget(splitter)
        
        # Set main widget
        central_widget = QWidget()
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)
        
        # Store current table ID for similarity coloring
        self.current_table_id = None
        
        # Update steps list
        self.update_steps_list()

    def update_steps_list(self):
        """Update the steps list widget with current steps"""
        self.steps_list.clear()
        for step in self.model.get_steps():
            display_text = f"[{step.timestamp}] {step.operation.value}: {step.details[:50]}{'...' if len(step.details) > 50 else ''}"
            item = QListWidgetItem(display_text)
            # Set the full text as tooltip
            item.setToolTip(f"[{step.timestamp}] {step.operation.value}: {step.details}")
            self.steps_list.addItem(item)
        # Scroll to bottom to show latest steps
        self.steps_list.scrollToBottom()
    
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
        
        # Show and reset progress bar
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        # Configure which table types to extract
        extraction_config = {
            "standard": self.standard_table_check.isChecked(),
            "advanced": self.advanced_table_check.isChecked(),
            "div": self.div_table_check.isChecked()
        }
        
        # Set up progress callback
        def progress_callback(progress, message=None):
            self.progress_bar.setValue(progress)
            if message:
                self.statusBar().showMessage(message)
        
        self.model.set_progress_callback(progress_callback)
        
        try:
            success, message = self.model.load_url(url, extraction_config)
            if success:
                self.update_ui()
                self.update_steps_list()  # Update steps list after fetching
                self.statusBar().showMessage(message)
            else:
                self.show_error(message)
                self.statusBar().showMessage("Error: " + message)
        finally:
            # Clean up progress bar
            self.model.set_progress_callback(None)
            self.progress_bar.setVisible(False)
    
    def update_ui(self):
        """Update all UI components with current model state"""
        tables = self.model.get_tables()
        scores = self.model.get_table_scores()
        
        self.table_list_widget.update_tables_list(tables, scores)
        self.update_steps_list()  # Update steps list when UI is updated
    
    def on_table_selected(self, item):
        """Handle table selection"""
        if not item:
            return
            
        table_id = item.data(Qt.ItemDataRole.UserRole)
        table_type = item.data(Qt.ItemDataRole.UserRole + 1)
        
        df = self.model.get_table_preview(table_id, max_rows=100)
        
        if df is not None:
            self.current_table_id = table_id
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
    
    def update_table_colors(self):
        """Update table colors based on column similarity for all tables, using best-matching header row if found. Table color is based on target column match score."""
        # Get target columns from input
        target_columns = [col.strip() for col in self.similarity_input.text().split(',') if col.strip()]
        if not target_columns:
            return
            
        # Show in progress status
        self.statusBar().showMessage("Applying similarity analysis...")
        self.apply_similarity_button.setEnabled(False)
        
        # Get all tables
        tables = self.model.get_tables()
        if not tables:
            self.statusBar().showMessage("No tables to analyze")
            self.apply_similarity_button.setEnabled(True)
            return
            
        try:
            for i, table in enumerate(tables):
                # Update progress
                progress = (i + 1) / len(tables) * 100
                self.statusBar().showMessage(f"Applying similarity analysis... {progress:.0f}%")
                
                table_id = table["id"]
                df = self.model.get_table_preview(table_id)
                if df is not None:
                    # Use best-matching header row for similarity
                    best_header, best_scores, best_row = self.model.best_header_similarity(df, target_columns)
                    # If this is the currently selected table, update the preview
                    if table_id == self.current_table_id:
                        self.preview_widget.display_dataframe_with_similarity(df, best_scores, header_labels=best_header, header_row_index=best_row)
                    # Update the table list item with similarity information
                    items = self.table_list_widget.tables_list.findItems(table["name"], Qt.MatchFlag.MatchContains)
                    if items:
                        item = items[0]
                        match_score = self.model.target_column_match_score(df, target_columns)
                        if match_score < 0.3:
                            similarity_indicator = "🔴"
                        elif match_score < 0.7:
                            similarity_indicator = "🟡"
                        else:
                            similarity_indicator = "🟢"
                        display_text = f"{item.text().split(' ', 2)[0]} {similarity_indicator} {table['name']} (target sim: {match_score:.2f})"
                        item.setText(display_text)
            
            self.statusBar().showMessage("Similarity analysis complete")
        except Exception as e:
            self.statusBar().showMessage(f"Error during similarity analysis: {str(e)}")
        finally:
            self.apply_similarity_button.setEnabled(True)
    
    def remove_low_score_tables(self):
        """Remove tables that are currently marked as red based on the active coloring scheme"""
        # Get all tables
        tables = self.model.get_tables()
        if not tables:
            return
            
        # Get target columns for similarity if any
        target_columns = [col.strip() for col in self.similarity_input.text().split(',') if col.strip()]
        
        # Filter tables with low scores based on current coloring scheme
        low_score_tables = []
        
        # First pass: identify red-marked tables from UI
        for i in range(self.table_list_widget.tables_list.count()):
            item = self.table_list_widget.tables_list.item(i)
            if "🔴" in item.text():
                table_id = item.data(Qt.ItemDataRole.UserRole)
                low_score_tables.append(table_id)
        
        if not low_score_tables:
            return
            
        # Remove tables with low scores in batch
        for table_id in low_score_tables:
            self.model.remove_table(table_id)
            
        self.update_ui()
        self.statusBar().showMessage(f"Removed {len(low_score_tables)} low score table{'s' if len(low_score_tables) > 1 else ''}")
    
    def show_error(self, message):
        """Show error message"""
        QMessageBox.critical(self, "Error", message)
    
    def save_project(self):
        """Save current project state"""
        # If we have a current project file, use it
        if self.model.current_project_file:
            success, message = self.model.save_project(self.model.current_project_file)
            if success:
                self.statusBar().showMessage(message)
                QMessageBox.information(self, "Success", message)
            else:
                self.show_error(message)
            return
            
        # Otherwise, prompt for a new file location
        filename, _ = QFileDialog.getSaveFileName(
            self, "Save Project", "", "Project Files (*.json)"
        )
        
        if filename:
            # Ensure it has the correct extension
            if not filename.lower().endswith('.json'):
                filename += '.json'
                
            success, message = self.model.save_project(filename)
            if success:
                self.statusBar().showMessage(message)
                QMessageBox.information(self, "Success", message)
            else:
                self.show_error(message)
    
    def load_project(self):
        """Load project state"""
        filename, _ = QFileDialog.getOpenFileName(
            self, "Load Project", "", "Project Files (*.json)"
        )
        
        if filename:
            success, message = self.model.load_project(filename)
            if success:
                # Update URL input with loaded project's URL
                self.url_input.setText(self.model.url)
                self.update_ui()
                self.update_steps_list()  # Also update steps list
                self.statusBar().showMessage(message)
                # Add to recent projects and update menu
                self.model.add_recent_project(filename)
                self.update_recent_projects()
            else:
                self.show_error(message)
    
    def new_project(self):
        """Create a new project"""
        # Clear current state
        self.model.clear_steps()
        self.model.tables = []
        self.model.table_dataframes = {}
        self.model.url = None
        self.model.html_content = None
        
        # Clear UI
        self.url_input.clear()
        self.table_list_widget.tables_list.clear()
        self.preview_widget.table_preview.clear()
        self.table_list_widget.table_info.clear()
        self.update_ui()
        
        self.statusBar().showMessage("New project created")
    
    def save_project_as(self):
        """Save current project state with a new filename"""
        filename, _ = QFileDialog.getSaveFileName(
            self, "Save Project As", "", "Project Files (*.json)"
        )
        
        if filename:
            # Ensure it has the correct extension
            if not filename.lower().endswith('.json'):
                filename += '.json'
                
            success, message = self.model.save_project(filename)
            if success:
                self.statusBar().showMessage(message)
                QMessageBox.information(self, "Success", message)
                self.update_recent_projects()  # Update recent projects list
            else:
                self.show_error(message)
    
    def update_recent_projects(self):
        """Update the recent projects menu"""
        self.recent_menu.clear()
        
        # Get recent projects from model
        recent_projects = self.model.get_recent_projects()
        
        if not recent_projects:
            action = self.recent_menu.addAction("No recent projects")
            action.setEnabled(False)
            return
            
        for project in recent_projects:
            action = self.recent_menu.addAction(project)
            action.triggered.connect(lambda checked, p=project: self.load_recent_project(p))
    
    def load_recent_project(self, project_path):
        """Load a project from the recent projects list"""
        if os.path.exists(project_path):
            success, message = self.model.load_project(project_path)
            if success:
                # Update URL input with loaded project's URL
                self.url_input.setText(self.model.url)
                self.update_ui()
                self.update_steps_list()  # Also update steps list
                self.statusBar().showMessage(message)
            else:
                self.show_error(message)
        else:
            self.show_error(f"Project file not found: {project_path}")
            self.update_recent_projects()  # Refresh the list

    def reload_all(self):
        """Reload the entire project"""
        if not self.model.url:
            self.show_error("No URL to reload")
            return
            
        self.statusBar().showMessage("Reloading project...")
        
        # Clear UI
        self.table_list_widget.tables_list.clear()
        self.preview_widget.table_preview.clear()
        self.table_list_widget.table_info.clear()
        self.table_list_widget.download_button.setEnabled(False)
        
        # Reload using the model's reload method
        success, message = self.model.reload()
        if success:
            self.update_ui()
            self.update_steps_list()
            self.statusBar().showMessage(message)
        else:
            self.show_error(message)
            self.statusBar().showMessage("Error: " + message)

    def open_in_sqlite(self):
        """Open all tables in SQLite shell"""
        success, message = self.model.open_in_sqlshell()
        if success:
            self.statusBar().showMessage(message)
        else:
            self.show_error(message)

    def update_numeric_colors(self):
        """Update table colors based on numeric content"""
        # Show in progress status
        self.statusBar().showMessage("Applying numeric analysis...")
        self.apply_numeric_button.setEnabled(False)
        
        # Get all tables
        tables = self.model.get_tables()
        if not tables:
            self.statusBar().showMessage("No tables to analyze")
            self.apply_numeric_button.setEnabled(True)
            return
            
        try:
            for i, table in enumerate(tables):
                # Update progress
                progress = (i + 1) / len(tables) * 100
                self.statusBar().showMessage(f"Applying numeric analysis... {progress:.0f}%")
                
                table_id = table["id"]
                df = self.model.get_table_preview(table_id)
                if df is not None:
                    # Calculate numeric scores for each column
                    numeric_scores = []
                    for col in df.columns:
                        try:
                            # Try to convert column to numeric
                            numeric_values = pd.to_numeric(df[col], errors='coerce')
                            numeric_percentage = numeric_values.notna().sum() / len(df)
                            numeric_scores.append(numeric_percentage)
                        except:
                            numeric_scores.append(0)
                    
                    # Get the highest numeric score for this table
                    max_numeric_score = max(numeric_scores) if numeric_scores else 0
                    
                    # If this is the currently selected table, update the preview
                    if table_id == self.current_table_id:
                        self.preview_widget.display_dataframe_with_numeric(df, numeric_scores)
                    
                    # Update the table list item with numeric information
                    items = self.table_list_widget.tables_list.findItems(table["name"], Qt.MatchFlag.MatchContains)
                    if items:
                        item = items[0]
                        if max_numeric_score < 0.3:
                            numeric_indicator = "🔴"
                        elif max_numeric_score < 0.7:
                            numeric_indicator = "🟡"
                        else:
                            numeric_indicator = "🟢"
                            
                        display_text = f"{item.text().split(' ', 2)[0]} {numeric_indicator} {table['name']} (numeric: {max_numeric_score:.2f})"
                        item.setText(display_text)
            
            self.statusBar().showMessage("Numeric analysis complete")
        except Exception as e:
            self.statusBar().showMessage(f"Error during numeric analysis: {str(e)}")
        finally:
            self.apply_numeric_button.setEnabled(True) 