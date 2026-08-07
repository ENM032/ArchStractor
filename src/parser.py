import re
from datetime import datetime
from bs4 import BeautifulSoup
from typing import List, Tuple, Optional, Dict, Any

MONTHS = ["january", "february", "march", "april", "may", "june", 
          "july", "august", "september", "october", "november", "december"]

def clean_whitespace(text: str) -> str:
    """Replaces all consecutive whitespace characters with a single space."""
    return " ".join(text.split())

def parse_date(date_cell_text: str, href: Optional[str] = None) -> datetime.date:
    """
    Parses date from the cell text or href link.
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
    cleaned_split = re.sub(r"([a-zA-Z]+)(\d+)", r"\1 \2", cleaned)
    parts = cleaned_split.split()
    
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

def detect_draw_schema(ball_lis: List[Any]) -> Tuple[int, int]:
    """
    Detects schema dynamically from list of ball elements.
    Returns: (num_main_balls, num_power_balls)
    """
    num_main = 0
    num_power = 0
    
    for li in ball_lis:
        classes = li.get('class', [])
        classes_str = " ".join(classes).lower()
        # Check for PowerBall or bonus ball tags (avoiding "pb" since main balls have "pb" class)
        if any(x in classes_str for x in ['powerball', 'bonus', 'bonusball', 'supp']):
            num_power += 1
        elif 'ball' in classes_str:
            num_main += 1
        else:
            num_main += 1
            
    # Fallback to counts if class names didn't distinguish them
    if num_power == 0 and len(ball_lis) > 0:
        if len(ball_lis) == 6:
            num_main = 5
            num_power = 1
        elif len(ball_lis) == 7:
            num_main = 6
            num_power = 1
        else:
            num_main = len(ball_lis) - 1
            num_power = 1
            
    return num_main, num_power

def parse_html_page(html_content: str) -> Tuple[List[Tuple[datetime.date, List[int], int]], Dict[str, int]]:
    """
    Parses the PowerBall results from the HTML content.
    Returns a tuple: (results_list, schema_dict)
    where results_list is sorted from newest to oldest.
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Match tables with any of the lottery class indicators, or fall back to the first table
    table = soup.find('table', class_=lambda c: c and any(cls in c for cls in ['powerball', 'powerball-plus', 'powerball-xtra', 'mobResult']))
    if not table:
        table = soup.find('table')
        
    if not table:
        return [], {"num_main_balls": 5, "num_power_balls": 1}
        
    rows = table.find_all('tr')
    results = []
    detected_schema = {"num_main_balls": 5, "num_power_balls": 1}
    schema_detected = False
    
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
        except ValueError:
            continue
            
        # Balls cell parsing
        balls_ul = cells[1].find('ul', class_='balls')
        if not balls_ul:
            continue
            
        ball_lis = balls_ul.find_all('li')
        if len(ball_lis) < 2:
            continue
            
        # Dynamic schema detection from the first parseable draw
        if not schema_detected:
            num_main, num_power = detect_draw_schema(ball_lis)
            detected_schema = {"num_main_balls": num_main, "num_power_balls": num_power}
            schema_detected = True
            
        try:
            main_count = detected_schema["num_main_balls"]
            power_count = detected_schema["num_power_balls"]
            
            if len(ball_lis) < main_count + power_count:
                continue
                
            main_balls = [int(li.text.strip()) for li in ball_lis[:main_count]]
            # Support single Powerball extraction or raise warning if multiple
            powerball = int(ball_lis[main_count].text.strip())
            results.append((draw_date, main_balls, powerball))
        except ValueError:
            continue
            
    return results, detected_schema
