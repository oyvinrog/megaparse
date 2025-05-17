import requests
from bs4 import BeautifulSoup
import pandas as pd
from collections import Counter

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
    """
    Find groups of sibling elements whose direct children share the same set of
    tags (a simple signature), and turn those into DataFrames.
    """
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
                        row = [sibling.find(col).get_text(strip=True) for col in cols]
                        rows.append(row)
                df = pd.DataFrame(rows, columns=cols)
                tables.append(df)
    return tables

def get_tables(content):
    """
    Parses arbitrary HTML and returns a list of pandas.DataFrame,
    including both real <table>s and repeated-structure “pseudo-tables.”
    """
    soup = BeautifulSoup(content, "lxml")
    tables = extract_html_tables(soup)
    tables += find_repeated_structures(soup)
    return tables

def test(url : str):
    """Fetch www.vg.no and print a summary of detected tables."""
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
        print(df.head())

if __name__ == "__main__":
    url = input("Enter a URL: ")
    test(url)
