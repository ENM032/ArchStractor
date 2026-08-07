import re
from datetime import datetime
from bs4 import BeautifulSoup
from typing import List, Tuple, Optional

# List of month names in English to help with parsing
MONTHS = ["january", "february", "march", "april", "may", "june", 
          "july", "august", "september", "october", "november", "december"]

def clean_whitespace(text: str) -> str:
    """Replaces all consecutive whitespace characters with a single space."""
    return " ".join(text.split())

def parse_date(date_cell_text: str, href: Optional[str] = None) -> datetime.date:
    """
    Parses date from the cell text or href link.
    Examples of date_cell_text:
        - "Friday 31 December 2010"
        - "Friday31 December 2010"
        - "31 December 2010"
    Examples of href:
        - "/powerball/results/31-december-2010"
    """
    # 1. Try parsing from href if available
    if href:
        match = re.search(r"(\d{1,2})-([a-zA-Z]+)-(\d{4})", href)
        if match:
            day_str, month_str, year_str = match.groups()
            try:
                dt = datetime.strptime(f"{day_str}-{month_str.lower()}-{year_str}", "%d-%B-%Y")
                return dt.date()
            except ValueError:
                pass

    # 2. Try parsing from the cell text
    cleaned = clean_whitespace(date_cell_text)
    # Remove weekday if it's at the beginning (e.g. "Friday", "Tuesday", etc.)
    # We can match patterns like "31 December 2010" or "Friday 31 December 2010"
    # Also handle "Friday31 December 2010" by separating letters and numbers
    cleaned_split = re.sub(r"([a-zA-Z]+)(\d+)", r"\1 \2", cleaned)
    parts = cleaned_split.split()
    
    # We expect to find a day (1-31), a month (name), and a year (4 digits)
    day = None
    month_val = None
    year = None
    
    for part in parts:
        part_lower = part.lower()
        if part_lower in MONTHS:
            month_val = MONTHS.index(part_lower) + 1
        elif part.isdigit():
            val = int(part)
            if 1 <= val <= 31 and day is None:
                day = val
            elif 2000 <= val <= 2030:
                year = val
                
    if day is not None and month_val is not None and year is not None:
        return datetime(year, month_val, day).date()
        
    raise ValueError(f"Could not parse date from text: '{date_cell_text}' or href: '{href}'")

def parse_html_page(html_content: str) -> List[Tuple[datetime.date, List[int], int]]:
    """
    Parses the PowerBall results from the HTML content.
    Returns a list of tuples: (draw_date, main_balls, powerball)
    sorted from newest to oldest (as they appear in the HTML table).
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    # Match tables with any of the lottery class indicators, or fall back to the first table
    table = soup.find('table', class_=lambda c: c and any(cls in c for cls in ['powerball', 'powerball-plus', 'powerball-xtra', 'mobResult']))
    if not table:
        table = soup.find('table')
        
    if not table:
        return []
        
    rows = table.find_all('tr')
    results = []
    
    for row in rows:
        cells = row.find_all('td')
        if len(cells) < 2:
            continue
            
        # Date cell parsing
        date_cell = cells[0]
        date_a = date_cell.find('a')
        href = date_a.get('href') if date_a else None
        date_text = date_cell.text.strip()
        
        try:
            draw_date = parse_date(date_text, href)
        except ValueError as e:
            # Skip rows where date is not parseable
            continue
            
        # Balls cell parsing
        balls_ul = cells[1].find('ul', class_='balls')
        if not balls_ul:
            continue
            
        ball_lis = balls_ul.find_all('li')
        if len(ball_lis) < 6:
            continue
            
        try:
            # First 5 are main balls, 6th is PowerBall
            main_balls = [int(li.text.strip()) for li in ball_lis[:5]]
            powerball = int(ball_lis[5].text.strip())
            results.append((draw_date, main_balls, powerball))
        except ValueError:
            # Skip if any ball value is not an integer
            continue
            
    return results
