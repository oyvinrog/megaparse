# MegaParse - Generic HTML Structure Extractor

MegaParse is a powerful, generic HTML data extraction tool that can identify and extract structured data from any HTML page without requiring site-specific scraping rules.

## Features

- **Generic extraction**: Works on any website without site-specific rules
- **Pattern recognition**: Identifies common data patterns like prices, dates, areas, and more
- **Structural analysis**: Detects repeated patterns and table-like structures
- **Key-value identification**: Extracts property-value pairs regardless of HTML structure
- **CSV export**: Saves all extracted data in organized CSV files

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/megaparse.git
cd megaparse

# Install dependencies
pip install -r requirements.txt
```

## Usage

### Command-line Interface

```bash
./megaparse_demo.py [URL or HTML file] [options]
```

**Arguments:**
- `source`: URL or local HTML file to parse

**Options:**
- `--output`, `-o`: Output directory for CSV files (default: 'output')
- `--min-rows`, `-m`: Minimum rows to save a table (default: 3)
- `--verbose`, `-v`: Show detailed output

### Examples

```bash
# Parse a website
./megaparse_demo.py https://www.example.com/

# Parse a local HTML file
./megaparse_demo.py local_file.html

# Save output to a custom directory
./megaparse_demo.py https://www.example.com/ --output my_data

# Show detailed information during extraction
./megaparse_demo.py https://www.example.com/ --verbose
```

### Using the Library in Your Code

```python
from parser import get_tables
import requests

# Fetch HTML content
response = requests.get('https://www.example.com/')
content = response.text

# Extract structured data
tables = get_tables(content)

# Process the tables
for i, df in enumerate(tables, 1):
    print(f"Table #{i}: shape={df.shape}")
    if 'pattern_type' in df.attrs:
        print(f"Type: {df.attrs['pattern_type']}")
    print(df.head())
```

## How It Works

MegaParse uses several different approaches to extract structured data:

1. **HTML Tables**: Extracts data from standard HTML tables
2. **Pattern Detection**: Identifies common data patterns like prices, dates, areas, etc.
3. **Repeated Structures**: Finds groups of sibling elements with similar structure
4. **Visual Blocks**: Detects repeated elements with similar content density
5. **Class-based Blocks**: Identifies elements with the same CSS classes that contain structured data
6. **Semantic Analysis**: Groups elements with similar internal structure
7. **Key-Value Extraction**: Identifies content in various formats that represent property-value pairs

## Requirements

- Python 3.6+
- beautifulsoup4
- pandas
- requests

## License

MIT 