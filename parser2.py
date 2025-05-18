import requests
import pandas as pd
import re
from bs4 import BeautifulSoup

def get_tables(content, examples: list):
    """
    Provide a list of string examples that you want to fetch, and try to identify the best parser for the content.
    Return a dataframe with results, and a regular expression that can be used to parse the content.
    """
    soup = BeautifulSoup(content, "html.parser")

    # Try to find all tags that contain example strings
    matches = []
    for example in examples:
        # Convert &nbsp; to regular space for comparison
        clean_example = example.replace("&nbsp;", " ")
        # Try different ways to find the text
        found = soup.find_all(string=lambda text: clean_example in (text or "").replace("\xa0", " "))
        if not found:
            # Try with regex that handles non-breaking spaces
            pattern = re.compile(re.escape(clean_example).replace(" ", r"[\s\xa0]+"))
            found = soup.find_all(string=lambda text: text and pattern.search(text.replace("\xa0", " ")))
        matches.extend(found)

    # If no matches found, try a more aggressive approach
    if not matches:
        for example in examples:
            clean_example = example.replace("&nbsp;", " ")
            # Extract just the numbers for price matching
            num_only = re.sub(r'[^\d]', '', clean_example)
            found = soup.find_all(string=lambda text: text and re.sub(r'[^\d]', '', text) == num_only)
            matches.extend(found)

    # Collect parent elements of each matched example (for context)
    parent_blocks = [el.parent for el in matches]

    # Extract data from the matches
    extracted_rows = []
    for match in matches:
        # Find the containing article or div
        container = match
        for _ in range(5):  # Look up to 5 levels up
            if container.name in ['article', 'div', 'li']:
                break
            container = container.parent if hasattr(container, 'parent') else None
            if container is None:
                break
        
        if container:
            row = {}
            # Extract all text content
            text_content = container.get_text(" ", strip=True)
            
            # Try to match each example
            for example in examples:
                clean_example = example.replace("&nbsp;", " ")
                if clean_example in text_content.replace("\xa0", " "):
                    row[example] = clean_example
                else:
                    # Try with just the numbers
                    num_only = re.sub(r'[^\d]', '', clean_example)
                    if num_only in re.sub(r'[^\d]', '', text_content):
                        row[example] = clean_example
                    else:
                        row[example] = None
            
            extracted_rows.append(row)

    df = pd.DataFrame(extracted_rows)

    # Suggest a general regex based on the first example
    if examples:
        base_example = examples[0]
        cleaned = base_example.replace("&nbsp;", " ")
        # Create a regex pattern that matches price format (digits, spaces, currency)
        suggested_regex = r"\d+[\s\xa0]*\d{3}[\s\xa0]*\d{3}[\s\xa0]*kr"
    else:
        suggested_regex = ""

    return df, suggested_regex


def generate_code(url: str, examples: list):
    """Generate code to parse the content of the url using the examples."""
    content = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}).text
    df, regex = get_tables(content, examples)
    with open("parse_site.py", "w") as f:
        f.write(f"""import requests
import pandas as pd
import re
from bs4 import BeautifulSoup

url = "{url}"
content = requests.get(url, headers={{"User-Agent": "Mozilla/5.0"}}).text

print(re.findall(r"{regex}", content))
                
                """)
    
    print("Code generated in parse_site.py")

# Example usage:
url = "https://www.finn.no/realestate/homes/search.html?filters=&location=0.20061"
generate_code(url, ["3&nbsp;700&nbsp;000&nbsp;kr","10&nbsp;900&nbsp;000&nbsp;kr","19&nbsp;900&nbsp;000&nbsp;kr"])
