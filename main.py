import sys
from PyQt6.QtWidgets import QApplication
from table_parser_model import TableParserModel
from table_parser_ui import TableParserUI

def main():
    app = QApplication(sys.argv)
    
    # Initialize model
    model = TableParserModel()
    
    # Initialize UI with model
    ui = TableParserUI(model)
    ui.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main() 