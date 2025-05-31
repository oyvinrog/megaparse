import requests
from bs4 import BeautifulSoup
from bs4.element import Comment, Doctype, ProcessingInstruction
import pandas as pd
from collections import Counter, defaultdict
import sys
import tty
import termios
import os
import hashlib
import re
from io import StringIO
# Add color constants
GREEN = '\033[92m'
BOLD = '\033[1m'
END = '\033[0m'

# File to store the previously entered URL
URL_HISTORY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".url_history")

# Load the previously entered URL
previous_url = None
try:
    if os.path.exists(URL_HISTORY_FILE):
        with open(URL_HISTORY_FILE, 'r') as f:
            previous_url = f.read().strip()
except Exception:
    # If there's any error reading the file, just continue without a previous URL
    pass

def getch():
    """Get a single character from the user without requiring Enter."""
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    return ch

def extract_html_tables(soup):
    """Use pandas to pull out all genuine <table> elements."""
    dfs = []
    for tbl in soup.find_all("table"):
        try:
            dfs += pd.read_html(StringIO(str(tbl)))
        except ValueError:
            continue
    return dfs

def find_dense_blocks(soup, min_text_elements=5):
    """
    Detects standalone blocks (e.g., real estate cards) that have dense structured content,
    even if they are not siblings or do not share classes.
    """
    blocks = []
    for tag in soup.find_all("div"):
        strings = [s.strip() for s in tag.stripped_strings if s.strip()]
        if len(strings) >= min_text_elements:
            blocks.append(strings)

    # Group similar-length blocks to guess they belong together
    grouped = {}
    for row in blocks:
        key = len(row)
        grouped.setdefault(key, []).append(row)

    dfs = []
    for rows in grouped.values():
        if len(rows) >= 3:
            max_len = max(len(r) for r in rows)
            normalized = [r + [''] * (max_len - len(r)) for r in rows]
            df = pd.DataFrame(normalized)
            dfs.append(df)
    return dfs


def find_repeated_structures(soup, min_repeats=3):
    """Find groups of sibling elements with repeated tag signatures."""
    tables = []
    for parent in soup.find_all():
        sigs = [tuple(child.name for child in child_el.find_all(recursive=False))
                for child_el in parent.find_all(recursive=False)]
        counts = Counter(sigs)
        for sig, cnt in counts.items():
            if cnt >= min_repeats and sig:
                rows = []
                cols = list(sig)
                for sibling in parent.find_all(recursive=False):
                    if tuple(child.name for child in sibling.find_all(recursive=False)) == sig:
                        row = [sibling.find(col).get_text(strip=True) if sibling.find(col) else "" for col in cols]
                        rows.append(row)
                df = pd.DataFrame(rows, columns=cols)
                tables.append(df)
    return tables

def find_visual_blocks(soup, min_repeats=3, min_text_elements=3):
    """Detect repeated sibling visual blocks with similar content density."""
    blocks = []
    for parent in soup.find_all():
        children = parent.find_all(recursive=False)
        if len(children) < min_repeats:
            continue

        tag_name = children[0].name
        if not all(c.name == tag_name for c in children):
            continue

        candidate_rows = []
        for child in children:
            strings = [s.strip() for s in child.stripped_strings if s.strip()]
            if len(strings) >= min_text_elements:
                candidate_rows.append(strings)

        if len(candidate_rows) >= min_repeats:
            max_len = max(len(row) for row in candidate_rows)
            normalized_rows = [row + [''] * (max_len - len(row)) for row in candidate_rows]
            df = pd.DataFrame(normalized_rows)
            blocks.append(df)

    return blocks


def structure_hash(tag, max_depth=3):
    """
    Generate a hashable structure signature of the element's tag tree.
    """
    def recurse(el, depth):
        if depth == 0 or not el or not hasattr(el, 'children'):
            return []
        return [el.name] + [recurse(c, depth - 1) for c in el.find_all(recursive=False)]
    
    def flatten(tree):
        if isinstance(tree, list):
            return [i for subtree in tree for i in flatten(subtree)]
        else:
            return [tree]
    
    tree = recurse(tag, max_depth)
    flat = flatten(tree)
    return hashlib.md5(">".join(flat).encode()).hexdigest()

def find_semantically_similar_blocks(soup, min_group_size=3, min_text_items=3):
    """
    Detect groups of <div> elements that share similar internal tag structures and
    contain enough textual content to be treated as records.
    """
    block_map = {}
    
    for div in soup.find_all("div"):
        strings = [s.strip() for s in div.stripped_strings if s.strip()]
        if len(strings) < min_text_items:
            continue

        sig = structure_hash(div)
        if sig not in block_map:
            block_map[sig] = []
        block_map[sig].append(strings)

    tables = []
    for group in block_map.values():
        if len(group) >= min_group_size:
            max_len = max(len(row) for row in group)
            normalized = [r + [''] * (max_len - len(r)) for r in group]
            df = pd.DataFrame(normalized)
            tables.append(df)
    return tables


def find_repeated_class_blocks(soup, min_repeats=3, min_text_elements=3):
    """
    Find repeated class-based elements that look like content cards (e.g., real estate listings).
    """
    class_map = defaultdict(list)
    for tag in soup.find_all(True):
        class_attr = tag.get("class")
        if class_attr:
            class_name = " ".join(class_attr)
            class_map[class_name].append(tag)

    blocks = []
    for class_name, tags in class_map.items():
        if len(tags) < min_repeats:
            continue

        rows = []
        for tag in tags:
            strings = [s.strip() for s in tag.stripped_strings if s.strip()]
            if len(strings) >= min_text_elements:
                rows.append(strings)

        if len(rows) >= min_repeats:
            max_len = max(len(row) for row in rows)
            normalized_rows = [r + [''] * (max_len - len(r)) for r in rows]
            df = pd.DataFrame(normalized_rows)
            df.attrs['source_class'] = class_name  # Optional metadata
            blocks.append(df)

    return blocks

def find_data_patterns(soup, min_matches=3):
    """
    A generic function to identify and extract data patterns from any webpage.
    This approach doesn't rely on specific tags or classes, but instead looks for 
    patterns in the data itself, like prices, measurements, dates, etc.
    
    Parameters:
    -----------
    soup : BeautifulSoup
        The parsed HTML content
    min_matches : int
        Minimum occurrences needed to consider a pattern
        
    Returns:
    --------
    list of DataFrames
        Each DataFrame contains a different type of structured data
    """
    all_text = soup.get_text()
    
    # Define pattern detectors with their regexes
    pattern_detectors = {
        'prices': [
            # Price patterns with currency
            r'(\d[\d\s]*[.,]?\d*)\s*(?:kr|€|£|\$|USD|EUR|NOK|SEK|DKK)',  # General price with currency
            r'(?:kr|€|£|\$|USD|EUR|NOK|SEK|DKK)\s*(\d[\d\s]*[.,]?\d*)',  # Currency first then amount
            
            # Price with context
            r'(?:pris|price|cost|total)(?:\w*)\s*(?:\:|\-|\.|\s)\s*(\d[\d\s]*[.,]?\d*)',  # Price labels
            r'(?:Prisantydning|Totalpris|Fellesutgifter|Fellesutg\.|Omkostninger|Omkost\.)\s*(?:\:|\-|\.|\s)?\s*(\d[\d\s]*[.,]?\d*)',  # Norwegian price labels
            
            # Price ranges
            r'(\d[\d\s]*[.,]?\d*)\s*(?:-|–|to|til)\s*(\d[\d\s]*[.,]?\d*)\s*(?:kr|€|£|\$|USD|EUR|NOK|SEK|DKK)',  # Price ranges
            
            # Numbers that look like prices (large numbers with proper formatting)
            r'(?<!\w)(\d{1,3}(?:\s*\d{3})+)(?!\w)',  # Large numbers with space separators
            r'(?<!\w)(\d{1,3}(?:,\d{3})+)(?!\w)',     # Large numbers with comma separators
            r'(?<!\w)(\d{1,3}(?:\.\d{3})+)(?:,\d+)?(?!\w)',  # European style numbers
        ],
        'areas': [
            r'(\d+[\d\s]*[.,]?\d*)\s*(?:m²|kvm|m2|sq\.ft|sqft)',  # Area measurements
            r'(\d+[\d\s]*[.,]?\d*)\s*(?:kvadratmeter|square\s+meters?)',  # Written out area
            r'(?:areal|area|størrelse|size)\s*(?:\:|\-|\.|\s)?\s*(\d+[\d\s]*[.,]?\d*)\s*(?:m²|kvm|m2)',  # Area with label
        ],
        'dates': [
            r'\d{1,2}\.\d{1,2}\.\d{2,4}',  # European date format
            r'\d{1,2}/\d{1,2}/\d{2,4}',    # US date format
            r'\d{4}-\d{1,2}-\d{1,2}',      # ISO date format
            r'(?:mandag|tirsdag|onsdag|torsdag|fredag|lørdag|søndag)\s+\d{1,2}\.\s+\w+',  # Norwegian weekday format
        ],
        'phone_numbers': [
            r'(?:\+\d{1,3}\s?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}',  # Generic phone number format
            r'(?:\+\d{1,3}\s?)?\d{8}',  # Norway phone number format (8 digits)
        ],
        'postal_codes': [
            r'\b\d{4,5}\b\s+\w+',  # Postal code + city name
            r'\b\w+\s+\d{4,5}\b',  # City name + postal code
        ]
    }
    
    results = {}
    
    # Extract text elements
    text_elements = []
    for el in soup.find_all(text=True):
        text = el.strip()
        if text and not isinstance(el, (Comment, Doctype, ProcessingInstruction)):
            # Find parent element to provide context
            parent = el.parent
            text_elements.append((text, parent.name))
    
    # Look for patterns in text elements
    for pattern_type, regexes in pattern_detectors.items():
        matches = []
        
        for text, parent_tag in text_elements:
            for regex in regexes:
                found = re.findall(regex, text)
                for match in found:
                    # Skip if match is just a single digit
                    if isinstance(match, str) and match.strip().isdigit() and len(match.strip()) <= 1:
                        continue
                    
                    # Clean up the match
                    if isinstance(match, tuple):
                        # If it's a tuple, it means we captured multiple groups
                        # For price ranges, create a formatted string
                        if pattern_type == 'prices' and len(match) == 2:
                            match = f"{match[0]} - {match[1]}"  # Price range
                        else:
                            match = match[0]  # Take first capture group
                    
                    # Extract surrounding context to help identify what the data means
                    if isinstance(match, str):
                        text_pos = text.find(match)
                        if text_pos >= 0:
                            # Get text before the match (for context)
                            before_text = text[:text_pos].strip()
                            # Get text after the match (sometimes contains units or other info)
                            after_text = text[text_pos + len(match):].strip()
                            
                            # Keep at most 5 words of context before and 3 words after
                            before_words = before_text.split()[-5:]
                            after_words = after_text.split()[:3]
                            context = ' '.join(before_words + ["|"] + after_words)
                        else:
                            context = ""
                    else:
                        context = ""
                    
                    matches.append({
                        'value': str(match).strip(),
                        'context': context,
                        'parent_tag': parent_tag
                    })
        
        # Remove duplicates
        unique_matches = []
        seen_values = set()
        for match in matches:
            if match['value'] not in seen_values:
                unique_matches.append(match)
                seen_values.add(match['value'])
        
        if len(unique_matches) >= min_matches:
            results[pattern_type] = unique_matches
    
    # Convert results to DataFrames
    dfs = []
    for pattern_type, matches in results.items():
        df = pd.DataFrame(matches)
        df.attrs['pattern_type'] = pattern_type
        dfs.append(df)
    
    # Try to find structured data like key-value pairs
    # This works in both definition lists and various labeling patterns
    key_value_pairs = find_key_value_structure(soup)
    if key_value_pairs and len(key_value_pairs) >= 2:  # At least 2 pairs to be useful
        df = pd.DataFrame(key_value_pairs)
        df.attrs['pattern_type'] = 'key_value_pairs'
        dfs.append(df)
    
    return dfs

def find_key_value_structure(soup):
    """
    Looks for key-value pairs in the document regardless of the specific HTML structure.
    Works for various ways of representing data like definition lists, tables, or labeled content.
    """
    pairs = []
    
    # Process definition lists
    for dl in soup.find_all('dl'):
        dts = dl.find_all('dt')
        dds = dl.find_all('dd')
        
        # Match dt elements with their corresponding dd elements
        for i, dt in enumerate(dts):
            if i < len(dds):
                key = dt.get_text(strip=True)
                value = dds[i].get_text(strip=True)
                if key and value:
                    pairs.append({'key': key, 'value': value})
    
    # Process tables that might contain key-value data
    for table in soup.find_all('table'):
        for row in table.find_all('tr'):
            cells = row.find_all(['th', 'td'])
            if len(cells) >= 2:
                key = cells[0].get_text(strip=True)
                value = cells[1].get_text(strip=True)
                if key and value:
                    pairs.append({'key': key, 'value': value})
    
    # Look for labeled content with strong, span, etc.
    for selector in ["strong", "b", "span", "label", "dt", "th"]:
        for tag in soup.find_all(selector):
            text = tag.get_text(strip=True)
            if not text or len(text) > 50:  # Skip if empty or too long
                continue
            
            # Check for tags that have a label-like format
            if text.endswith(':') or text.endswith('='):
                next_sib = tag.find_next_sibling()
                if next_sib:
                    value = next_sib.get_text(strip=True)
                    if value and not value.endswith(':') and not value.endswith('='):
                        pairs.append({'key': text.rstrip(':='), 'value': value})
                # Also try to find the value in the next text node
                elif tag.next_sibling and isinstance(tag.next_sibling, str):
                    value = tag.next_sibling.strip()
                    if value:
                        pairs.append({'key': text.rstrip(':='), 'value': value})
                # Try to find the value in the parent's next sibling
                elif tag.parent and tag.parent.next_sibling:
                    next_parent_sib = tag.parent.next_sibling
                    if isinstance(next_parent_sib, str):
                        value = next_parent_sib.strip()
                    else:
                        value = next_parent_sib.get_text(strip=True) if hasattr(next_parent_sib, 'get_text') else ""
                    
                    if value and not value.endswith(':') and not value.endswith('='):
                        pairs.append({'key': text.rstrip(':='), 'value': value})
    
    # Look for divs that might contain key-value pairs
    for div in soup.find_all('div'):
        # Check if it has exactly two children, one might be a key and one might be a value
        children = list(div.children)
        filtered_children = [c for c in children if not (isinstance(c, str) and c.strip() == '')]
        if len(filtered_children) == 2:
            first_text = filtered_children[0].get_text(strip=True) if hasattr(filtered_children[0], 'get_text') else str(filtered_children[0]).strip()
            second_text = filtered_children[1].get_text(strip=True) if hasattr(filtered_children[1], 'get_text') else str(filtered_children[1]).strip()
            
            if first_text and second_text:
                # Heuristics to identify if the first child is a key
                if len(first_text) < 50 and first_text.endswith(':'):
                    pairs.append({'key': first_text.rstrip(':'), 'value': second_text})
                # Or if the second looks like a value (numbers, units, etc.)
                elif re.search(r'\d', second_text) or re.search(r'(kr|m²|kvm|sqft|\$|€)', second_text):
                    pairs.append({'key': first_text, 'value': second_text})
    
    # Find common labeling patterns in any element
    for p in soup.find_all(['p', 'div', 'li', 'span']):
        text = p.get_text(strip=True)
        
        # Skip very short or very long texts
        if len(text) <= 3 or len(text) > 200:
            continue
            
        # Look for patterns like "Key: Value" or "Key - Value"
        for pattern in [r'^([^:]+):\s*(.*?)(?:\s*\||$)', r'^([^-]+)\s*-\s*(.*?)(?:\s*\||$)']: 
            match = re.match(pattern, text)
            if match:
                key, value = match.groups()
                key = key.strip()
                value = value.strip()
                if key and value and len(key) < 50:  # Avoid capturing entire paragraphs
                    pairs.append({'key': key, 'value': value})
    
    # Clean up duplicates
    unique_pairs = []
    seen = set()
    for pair in pairs:
        pair_id = (pair['key'], pair['value'])
        if pair_id not in seen:
            unique_pairs.append(pair)
            seen.add(pair_id)
    
    return unique_pairs

def find_text_numeric_tables(soup, min_rows=3, min_cols=2):
    """
    Identifies HTML structures that appear to be tables with a mix of text and numeric columns.
    This function analyzes the data types in sibling elements to detect tabular structures,
    even when they don't use traditional table HTML tags.
    
    Parameters:
    -----------
    soup : BeautifulSoup
        The parsed HTML content
    min_rows : int
        Minimum number of rows to consider a valid table
    min_cols : int
        Minimum number of columns to consider a valid table
        
    Returns:
    --------
    list of DataFrames
        Each DataFrame represents a detected table with text and numeric columns
    """
    tables = []
    
    # Look for potential containers that might hold table-like data
    for container in soup.find_all(['div', 'ul', 'section', 'article']):
        # Skip small containers
        if len(container.get_text()) < 100:
            continue
        
        # Find repeating elements that might be rows
        child_tags = [child.name for child in container.find_all(recursive=False) 
                      if child.name and not isinstance(child, (Comment, Doctype, ProcessingInstruction))]
        
        # Skip if no children or all children are different types
        if not child_tags or len(set(child_tags)) == len(child_tags):
            continue
        
        # Find the most common tag - likely to be row elements
        most_common_tag = Counter(child_tags).most_common(1)[0][0]
        potential_rows = container.find_all(most_common_tag, recursive=False)
        
        if len(potential_rows) < min_rows:
            continue
        
        # For each potential row, extract text content
        row_data = []
        for row in potential_rows:
            # Find elements that might be cells
            cells = row.find_all(recursive=False)
            if len(cells) < min_cols:
                # Try to extract text nodes that might be separated by <br> tags or other inline elements
                cell_contents = []
                text_chunks = [t.strip() for t in row.get_text().split('\n') if t.strip()]
                if len(text_chunks) >= min_cols:
                    cell_contents = text_chunks
            else:
                cell_contents = [cell.get_text(strip=True) for cell in cells]
            
            if len(cell_contents) >= min_cols:
                row_data.append(cell_contents)
        
        if len(row_data) < min_rows:
            continue
        
        # Normalize row lengths
        max_cols = max(len(row) for row in row_data)
        normalized_rows = [row + [''] * (max_cols - len(row)) for row in row_data]
        
        # Check if we have a mix of text and numeric columns
        has_numeric_column = False
        has_text_column = False
        
        for col_idx in range(max_cols):
            column_values = [row[col_idx] for row in normalized_rows if col_idx < len(row)]
            
            # Check if column has numeric values
            numeric_count = sum(1 for val in column_values if val and re.match(r'^\s*[+-]?\d+[\d.,\s]*\s*%?\s*$', val))
            
            # Column is primarily numeric if more than 70% of values are numeric
            if numeric_count > 0.7 * len(column_values):
                has_numeric_column = True
            elif sum(1 for val in column_values if val and len(val) > 1 and not val.isdigit()) > 0.5 * len(column_values):
                has_text_column = True
                
        # If we have both text and numeric columns, we've found a table
        if has_numeric_column and has_text_column:
            df = pd.DataFrame(normalized_rows)
            df.attrs['source'] = 'text_numeric_detection'
            
            # Try to determine header row if first row is different
            if row_data and len(row_data) > 1:
                first_row = row_data[0]
                other_rows = row_data[1:]
                
                # Check if first row contains different data types than other rows
                first_row_numeric = sum(1 for cell in first_row if cell and re.match(r'^\s*[+-]?\d+[\d.,\s]*\s*%?\s*$', cell))
                other_rows_numeric = sum(1 for row in other_rows for cell in row 
                                        if cell and re.match(r'^\s*[+-]?\d+[\d.,\s]*\s*%?\s*$', cell))
                
                # If first row has significantly fewer numerics, it might be a header
                if first_row_numeric == 0 and other_rows_numeric > 0:
                    header_row = normalized_rows[0]
                    df.columns = header_row
                    df = df.iloc[1:].reset_index(drop=True)
            
            tables.append(df)
    
    # Look for scattered but aligned data that might form a table
    # This handles cases where table cells are not properly contained within a single parent
    text_elements = []
    for el in soup.find_all(text=True):
        if el.strip() and not isinstance(el.parent, (Comment, Doctype, ProcessingInstruction)):
            # Get the element's coordinates by traversing its parents
            parent = el.parent
            x_pos = 0
            y_pos = 0
            
            # Use a simple heuristic - count siblings as y coordinate
            siblings = list(parent.previous_siblings)
            y_pos = len(siblings)
            
            # Calculate x position based on parent tags
            ancestor = parent
            while ancestor and ancestor != soup:
                siblings = list(ancestor.previous_siblings)
                x_pos += len(siblings) * 10  # Weight by depth
                ancestor = ancestor.parent
            
            text_elements.append({
                'text': el.strip(),
                'x': x_pos,
                'y': y_pos,
                'is_numeric': bool(re.match(r'^\s*[+-]?\d+[\d.,\s]*\s*%?\s*$', el.strip()))
            })
    
    # Group text elements by y-coordinate (potential rows)
    y_groups = defaultdict(list)
    for el in text_elements:
        y_groups[el['y']].append(el)
    
    # Keep only rows with multiple elements
    rows = [elements for y, elements in y_groups.items() if len(elements) >= min_cols]
    
    if len(rows) >= min_rows:
        # Sort each row by x-coordinate
        for row in rows:
            row.sort(key=lambda el: el['x'])
        
        # Check if we have text and numeric columns
        has_numeric_column = False
        has_text_column = False
        
        # Transpose to check columns
        max_cols = max(len(row) for row in rows)
        columns = [[] for _ in range(max_cols)]
        
        for row in rows:
            for i, el in enumerate(row):
                if i < max_cols:
                    columns[i].append(el)
        
        for column in columns:
            # Count numeric elements in the column
            numeric_count = sum(1 for el in column if el.get('is_numeric', False))
            
            if numeric_count > 0.7 * len(column):
                has_numeric_column = True
            elif sum(1 for el in column if not el.get('is_numeric', True) and len(el['text']) > 1) > 0.5 * len(column):
                has_text_column = True
        
        if has_numeric_column and has_text_column:
            # Create DataFrame from the aligned text elements
            normalized_rows = []
            for row in rows:
                row_data = [el['text'] for el in row]
                row_data += [''] * (max_cols - len(row_data))
                normalized_rows.append(row_data)
            
            df = pd.DataFrame(normalized_rows)
            df.attrs['source'] = 'aligned_text_detection'
            tables.append(df)
    
    return tables

def find_relations(soup):
    import pandas as pd
    from collections import Counter

    relations = []

    def extract_card_data(card):
        """Extract key-value text content from visible card elements"""
        data = {}
        all_text = card.get_text(separator="\n", strip=True).split("\n")
        # Try to identify values like price, location, title heuristically
        for i, line in enumerate(all_text):
            if "kr" in line.lower():
                if "total" in line.lower():
                    data["total_price"] = line
                elif "kr" in line:
                    data["price"] = line
            elif i == 0:
                data["location"] = line
            elif i == 1:
                data["title"] = line
            else:
                data[f"text_{i}"] = line
        return data

    # Find potential containers with repeating child structure
    for container in soup.find_all(["div", "section"], recursive=True):
        children = container.find_all(recursive=False)
        if len(children) < 3:
            continue

        tag_counts = Counter(child.name for child in children)
        most_common_tag, count = tag_counts.most_common(1)[0]

        if count >= 3:
            blocks = [child for child in children if child.name == most_common_tag]
            block_data = [extract_card_data(block) for block in blocks if block.get_text(strip=True)]

            # Heuristic: ensure data has some 'price' content and is not just text
            if any("price" in row for row in block_data):
                df = pd.DataFrame(block_data)
                relations.append(df)

    return relations

def score_table(table):
    """Score table based on presence of numeric columns."""
    # Check each column
    for col in table.columns:
        # Check if the column is numeric or can be converted to numeric
        try:
            # Try to see if the column is already numeric
            if pd.api.types.is_numeric_dtype(table[col]):
                return 1
            
            # If not, try to convert to numeric
            pd.to_numeric(table[col])
            return 1
        except:
            pass
    return 0

def get_tables(content):
    """
    Parses arbitrary HTML and returns a list of pandas.DataFrame,
    including real <table>s, repeated-tag pseudo-tables, visual blocks, and repeated class blocks.
    """
    soup = BeautifulSoup(content, "lxml")
    
    tables = []
    # clear the scores.log
    with open("scores.log", "w") as f:
        f.write("")
    # Later, we will use these functions and score which is the best 
    functions = [find_repeated_structures, find_visual_blocks, \
                 find_repeated_class_blocks, find_dense_blocks, find_semantically_similar_blocks, \
                    find_data_patterns, find_text_numeric_tables, find_relations]

    for function in functions:
        tables += function(soup)

        # Score the function. If this is a table with atomic values (i.e. only numbers or only strings), it is good.
        # If it is a table with mixed values, it is bad.
        # If it is a table with non-tabular data, it is bad.

        score = sum([score_table(table) for table in tables]) 
        
        # Log to scores.log
        with open("scores.log", "a") as f:
            f.write(f"{function.__name__}: {score}\n")

        print(f"{function.__name__}: {score}")



    # Filter out tables with only one row or one column
    filtered_tables = [df for df in tables if df.shape[0] > 1 and df.shape[1] > 1]
    
    return filtered_tables

def test(url: str):
    """Fetch HTML from the URL and print summary of detected tables."""
    print(f"Fetching {url}...")
    response = requests.get(url)
    if response.status_code != 200:
        print(f"Failed to fetch page: status code {response.status_code}")
        return
    content = response.text
    tables = get_tables(content)
    print(f"Found {len(tables)} tables/pseudo-tables.")
    for i, df in enumerate(tables, 1):
        print(f"\nTable #{i}: shape={df.shape}")
        if 'source_class' in df.attrs:
            print(f"(Detected from repeated class: '{df.attrs['source_class']}')")
        print(df.head())

def sanity_checks():
    """Verify that the parser is working as expected."""
    url = "https://www.finn.no/realestate/homes/ad.html?finnkode=408006385"

    print(f"Fetching {url}...")
    response = requests.get(url)
    if response.status_code != 200:
        print(f"Failed to fetch page: status code {response.status_code}")
        return
    content = response.text
    tables = get_tables(content)
    print(f"Found {len(tables)} tables/pseudo-tables.")
    assert len(tables) >= 10
    print("Sanity check passed for number of tables")

    df = tables[0]
    assert isinstance(df, pd.DataFrame)
    print("Sanity check passed for DataFrame")

    print("Checking for Boligtype value")
    for df in tables:
        if "dt" in df.columns and "dd" in df.columns:
            if df["dt"].iloc[0] == "Boligtype" and df["dd"].iloc[0] == "Leilighet":
                print("Found the expected table with columns dt and dd and boligtype=Leilighet")
                break
    else:
        raise ValueError("No table with the expected columns found")
    print("Sanity check passed for expected column values")

    expected_totalpris = "4 104 417 kr"
    print("Checking for Totalpris value")
    totalpris_found = False
    for df in tables:
        if "dt" in df.columns and "dd" in df.columns:
            if df["dt"].iloc[0] == "Totalpris":
                totalpris_found = True
                print(f"Found table with Totalpris value: '{df['dd'].iloc[0]}'")
                if df["dd"].iloc[0] == expected_totalpris:
                    print(f"Found the expected table with totalpris={expected_totalpris}")
                    break
    if not totalpris_found:
        raise ValueError("No table with the Totalpris column found")
    print("Sanity check passed for expected totalpris value")

    print(f"\n{GREEN}{BOLD}✓ ALL SANITY CHECKS PASSED SUCCESSFULLY! ✓{END}\n")

if __name__ == "__main__":
    # Check if command line argument is provided
    if len(sys.argv) > 1:
        if sys.argv[1] == "sanity":
            sanity_checks()
        elif sys.argv[1].startswith("http"):
            # Treat the argument as a URL
            url = sys.argv[1]
            # Save the URL for future runs
            try:
                with open(URL_HISTORY_FILE, 'w') as f:
                    f.write(url)
            except Exception:
                # If we can't save the URL, just continue
                pass
            test(url)
        else:
            print(f"Invalid argument: {sys.argv[1]}")
            print("Usage: python parser.py [sanity|URL]")
    else:
        # Interactive mode
        print("Press 1 to run sanity checks")
        print("Press 2 to test a URL")
        try:
            choice = getch()
            print(f"\nYou selected: {choice}")

            if choice == "1":
                sanity_checks()
            elif choice == "2":
                url_prompt = f"Enter a URL {f'[{previous_url}]' if previous_url else ''}: "
                url_input = input(url_prompt)
                # Use the previous URL if the user just hits Enter
                url = url_input if url_input.strip() else previous_url or url_input
                if url:
                    # Save the URL for future runs
                    try:
                        with open(URL_HISTORY_FILE, 'w') as f:
                            f.write(url)
                    except Exception:
                        # If we can't save the URL, just continue
                        pass
                    previous_url = url
                    test(url)
                else:
                    print("No URL provided")
            else:
                print("Invalid choice")
        except Exception as e:
            print(f"Error in interactive mode: {e}")
            print("Try using command line arguments: python parser.py [sanity|URL]")
