import requests
from bs4 import BeautifulSoup
import pandas as pd
from collections import Counter, defaultdict
import sys
import tty
import termios
import os

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
            dfs += pd.read_html(str(tbl))
        except ValueError:
            continue
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

def get_tables(content):
    """
    Parses arbitrary HTML and returns a list of pandas.DataFrame,
    including real <table>s, repeated-tag pseudo-tables, visual blocks, and repeated class blocks.
    """
    soup = BeautifulSoup(content, "lxml")
    tables = extract_html_tables(soup)
    tables += find_repeated_structures(soup)
    tables += find_visual_blocks(soup)
    tables += find_repeated_class_blocks(soup)
    return tables

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
    print("Press 1 to run sanity checks")
    print("Press 2 to test a URL")
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
