# Web Table Parser

A PyQt6 application for parsing HTML tables from web pages and saving them as Parquet files.

## Design goals

The parser in `parser.py`should be the best parser available for extracting relational tables from HTML

## Features

- Load any webpage and extract tables
- View a list of available tables
- Preview table content before downloading
- Save selected tables as Parquet files

## Requirements

- Python 3.8+
- Dependencies listed in `requirements.txt`

## Installation

1. Clone this repository
2. Install dependencies:

```bash
pip install -r requirements.txt
```

## Usage

1. Run the application:

```bash
python main.py
```

2. Enter a URL in the input field and click "Fetch Tables"
3. Select a table from the list to preview its contents
4. Click "Save Selected Table" to save the table as a Parquet file

## Structure

- `main.py` - Main application entry point
- `table_parser_model.py` - Model for web table parsing and data handling
- `table_parser_ui.py` - PyQt6 user interface components 