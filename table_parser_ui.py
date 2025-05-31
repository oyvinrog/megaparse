from PyQt6.QtWidgets import (
    QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QPushButton,
    QLineEdit, QLabel, QListWidget, QListWidgetItem, QMessageBox,
    QTableWidget, QTableWidgetItem, QSplitter, QFileDialog,
    QComboBox, QCheckBox, QGroupBox, QTextBrowser, QProgressBar, QMenu,
    QInputDialog
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
        # Enable multi-select mode
        self.tables_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        # Enable context menu
        self.tables_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tables_list.customContextMenuRequested.connect(self.show_context_menu)
        # Enable key press events
        self.tables_list.keyPressEvent = self.handle_key_press
        layout.addWidget(self.tables_list)
        
        # Table info section
        self.table_info = QTextBrowser()
        self.table_info.setMaximumHeight(100)
        layout.addWidget(QLabel("Table Information:"))
        layout.addWidget(self.table_info)
        
        # Button layout
        button_layout = QHBoxLayout()
        
        # Delete button
        self.delete_button = QPushButton("Delete Selected")
        self.delete_button.setEnabled(False)
        self.delete_button.clicked.connect(self.delete_selected_tables)
        button_layout.addWidget(self.delete_button)
        
        # Download button
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
    
    def on_selection_changed(self):
        """Handle selection changes"""
        selected_items = self.tables_list.selectedItems()
        self.delete_button.setEnabled(len(selected_items) > 0)
        self.download_button.setEnabled(len(selected_items) == 1)
    
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
        self.setWindowTitle("Table Parser")
        self.setGeometry(100, 100, 1200, 800)
        
        # Main layout
        main_layout = QVBoxLayout()
        
        # URL input section
        url_layout = QHBoxLayout()
        url_layout.addWidget(QLabel("URL:"))
        self.url_input = QLineEdit()
        self.url_input.setText(self.model.get_last_url())
        url_layout.addWidget(self.url_input)
        
        # Fetch button
        self.fetch_button = QPushButton("Fetch Tables")
        self.fetch_button.clicked.connect(self.fetch_tables)
        url_layout.addWidget(self.fetch_button)
        
        # Project buttons
        self.new_project_button = QPushButton("New Project")
        self.new_project_button.clicked.connect(self.new_project)
        url_layout.addWidget(self.new_project_button)
        
        self.save_project_button = QPushButton("Save Project")
        self.save_project_button.clicked.connect(self.save_project)
        url_layout.addWidget(self.save_project_button)
        
        self.load_project_button = QPushButton("Load Project")
        self.load_project_button.clicked.connect(self.load_project)
        url_layout.addWidget(self.load_project_button)
        
        main_layout.addLayout(url_layout)
        
        # Table type selection
        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("Table Types:"))
        
        self.standard_table_check = QCheckBox("Standard Tables")
        self.standard_table_check.setChecked(True)
        type_layout.addWidget(self.standard_table_check)
        
        self.advanced_table_check = QCheckBox("Advanced Tables")
        self.advanced_table_check.setChecked(True)
        type_layout.addWidget(self.advanced_table_check)
        
        self.div_table_check = QCheckBox("Div-based Tables")
        self.div_table_check.setChecked(True)
        type_layout.addWidget(self.div_table_check)
        
        # Add remove low score button
        self.remove_low_score_button = QPushButton("Remove Low Score Tables")
        self.remove_low_score_button.clicked.connect(self.remove_low_score_tables)
        type_layout.addWidget(self.remove_low_score_button)
        
        main_layout.addLayout(type_layout)
        
        # Column similarity input
        similarity_layout = QHBoxLayout()
        similarity_layout.addWidget(QLabel("Color by Similarity (comma-separated column names):"))
        self.similarity_input = QLineEdit()
        self.similarity_input.setPlaceholderText("e.g., price, date, name")
        similarity_layout.addWidget(self.similarity_input)
        
        # Add a button to apply similarity coloring
        self.apply_similarity_button = QPushButton("Apply Similarity")
        self.apply_similarity_button.clicked.connect(self.update_table_colors)
        similarity_layout.addWidget(self.apply_similarity_button)
        
        main_layout.addLayout(similarity_layout)
        
        # Splitter for tables list, preview, and steps
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Initialize components
        self.table_list_widget = TableListWidget()
        self.preview_widget = TablePreviewWidget()
        
        # Create steps list widget
        steps_widget = QWidget()
        steps_layout = QVBoxLayout(steps_widget)
        steps_layout.addWidget(QLabel("Operation History:"))
        self.steps_list = QListWidget()
        steps_layout.addWidget(self.steps_list)
        steps_widget.setMaximumWidth(300)
        
        # Connect signals
        self.table_list_widget.tables_list.itemClicked.connect(self.on_table_selected)
        self.table_list_widget.tables_list.currentItemChanged.connect(self.on_table_selected)
        self.table_list_widget.download_button.clicked.connect(self.save_table)
        
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
        
        # Status
        self.statusBar().showMessage("Ready")
        
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
        
        # Configure which table types to extract
        extraction_config = {
            "standard": self.standard_table_check.isChecked(),
            "advanced": self.advanced_table_check.isChecked(),
            "div": self.div_table_check.isChecked()
        }
        
        success, message = self.model.load_url(url, extraction_config)
        if success:
            self.update_ui()
            self.update_steps_list()  # Update steps list after fetching
            self.statusBar().showMessage(message)
        else:
            self.show_error(message)
            self.statusBar().showMessage("Error: " + message)
    
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
        # Get all tables
        tables = self.model.get_tables()
        if not tables:
            return
        for table in tables:
            table_id = table["id"]
            df = self.model.get_table_preview(table_id)
            if df is not None:
                # Use best-matching header row for similarity
                best_header, best_scores, best_row = self.model.best_header_similarity(df, target_columns)
                # If this is the currently selected table, update the preview
                if table_id == self.current_table_id:
                    self.preview_widget.display_dataframe_with_similarity(df, best_scores, header_labels=best_header, header_row_index=best_row)
                # Update the table list item with similarity information (now using target_column_match_score)
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
    
    def remove_low_score_tables(self):
        """Remove tables with low entropy or similarity scores"""
        # Get all tables
        tables = self.model.get_tables()
        if not tables:
            return
            
        # Get target columns for similarity if any
        target_columns = [col.strip() for col in self.similarity_input.text().split(',') if col.strip()]
        
        # Get entropy scores
        scores = self.model.get_table_scores()
        if not scores:
            return
            
        # Create a mapping of table IDs to their entropy scores
        score_map = {score["id"]: score["entropy"] for score in scores}
        
        # Filter tables with low scores
        low_score_tables = []
        for table in tables:
            table_id = table["id"]
            df = self.model.get_table_preview(table_id)
            if df is not None:
                # Check both entropy and similarity scores if target columns are specified
                entropy_score = score_map.get(table_id, 0)
                similarity_score = 0
                
                if target_columns:
                    similarity_score = self.model.target_column_match_score(df, target_columns)
                    # If we have similarity scores, use those instead of entropy
                    if similarity_score < 0.3:
                        low_score_tables.append(table)
                else:
                    # If no similarity targets, use entropy scores
                    if entropy_score < 0.3:
                        low_score_tables.append(table)
        
        if not low_score_tables:
            return
            
        # Remove tables with low scores
        for table in low_score_tables:
            self.model.remove_table(table["id"])
            
        self.update_ui()
        # Update the message based on which type of score was used
        if target_columns:
            self.statusBar().showMessage("Low similarity score tables removed")
        else:
            self.statusBar().showMessage("Low entropy score tables removed")
    
    def show_error(self, message):
        """Show error message"""
        QMessageBox.critical(self, "Error", message)
    
    def save_project(self):
        """Save current project state"""
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
                self.update_ui()
                self.statusBar().showMessage(message)
                QMessageBox.information(self, "Success", message)
            else:
                self.show_error(message)
    
    def new_project(self):
        """Create a new project by clearing all tables and steps"""
        reply = QMessageBox.question(
            self,
            "New Project",
            "Are you sure you want to create a new project? This will clear all current tables and steps.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.model.clear_all()
            self.url_input.clear()
            self.table_list_widget.tables_list.clear()
            self.preview_widget.table_preview.clear()
            self.table_list_widget.table_info.clear()
            self.steps_list.clear()
            self.statusBar().showMessage("New project created") 