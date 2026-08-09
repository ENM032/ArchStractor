import re
import os
import csv
import json
import sqlite3
from typing import List, Tuple, Dict, Any, Optional
from datetime import datetime

HEADER_re = re.compile(r"^===\s+(\d{4})\s+===$")
COMPLETED_re = re.compile(r"^Day\s+(\d+)\s+-\s+\[(\d+(?:,\d+)*,\[\d+\])\]$")
PLACEHOLDER_re = re.compile(r"^Day\s+(\d+)\s+-\s+\[\]$")

def get_file_format(file_path: str, format_override: Optional[str] = None) -> str:
    """Auto-detects format from file extension, unless overridden."""
    if format_override:
        return format_override.lower()
    ext = os.path.splitext(file_path)[1].lower()
    if ext == '.csv':
        return 'csv'
    elif ext == '.json':
        return 'json'
    elif ext in ['.db', '.sqlite', '.sqlite3']:
        return 'sqlite'
    return 'txt'

def detect_line_ending(file_path: str) -> str:
    """Detects the line ending of the file (CRLF or LF). Defaults to LF."""
    if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
        return "\n"
    try:
        with open(file_path, "rb") as f:
            content = f.read(4096)
            if b"\r\n" in content:
                return "\r\n"
    except IOError:
        pass
    return "\n"

# ==================== TXT FORMAT HANDLERS ====================

def parse_txt_dataset(file_path: str) -> Tuple[List[Dict[str, Any]], List[str], int, int]:
    """Parses existing TXT dataset."""
    lines_to_keep_raw = []
    records = []
    last_completed_day = 0
    last_completed_idx = -1
    current_year = 2009
    year_map = {}
    
    with open(file_path, "r", encoding="utf-8") as f:
        lines = [line.rstrip("\r\n") for line in f]
        
    for i, line in enumerate(lines):
        header_match = HEADER_re.match(line)
        if header_match:
            current_year = int(header_match.group(1))
            continue
            
        comp_match = COMPLETED_re.match(line)
        if comp_match:
            day_num = int(comp_match.group(1))
            last_completed_day = day_num
            last_completed_idx = i
            year_map[day_num] = current_year
            
            # Extract balls
            inner_content = comp_match.group(2)
            parts = re.split(r",?\[", inner_content)
            main_nums_str = parts[0].rstrip(",")
            pb_str = parts[1].rstrip("]")
            main_balls = [int(x) for x in main_nums_str.split(",")]
            powerball = int(pb_str)
            
            records.append({
                "day": day_num,
                "date": None,  # Not stored in TXT
                "main_balls": main_balls,
                "powerball": powerball,
                "year": current_year
            })
            
    if last_completed_idx == -1:
        return [], [], 0, 2009
        
    lines_to_keep_raw = lines[:last_completed_idx + 1]
    last_completed_year = year_map.get(last_completed_day, 2009)
    return records, lines_to_keep_raw, last_completed_day, last_completed_year

def append_txt_results(
    file_path: str,
    new_draws: List[Tuple[Any, List[int], int]],
    last_completed_day: int,
    last_completed_year: int,
    lines_to_keep: List[str]
) -> int:
    line_ending = detect_line_ending(file_path)
    output_lines = list(lines_to_keep)
    
    current_day = last_completed_day
    current_year = last_completed_year
    appended_count = 0
    
    for draw_date, main_balls, powerball in new_draws:
        draw_year = draw_date.year
        if draw_year > current_year:
            output_lines.append(f"=== {draw_year} ===")
            current_year = draw_year
            
        current_day += 1
        balls_str = ",".join(map(str, main_balls))
        entry_str = f"Day {current_day} - [{balls_str},[{powerball}]]"
        output_lines.append(entry_str)
        appended_count += 1
        
    with open(file_path, "w", encoding="utf-8", newline="") as f:
        f.write(line_ending.join(output_lines) + line_ending)
        
    return appended_count

# ==================== CSV FORMAT HANDLERS ====================

def parse_csv_dataset(file_path: str) -> Tuple[List[Dict[str, Any]], int, int]:
    records = []
    last_day = 0
    last_year = 2009
    
    if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
        return [], 0, last_year
        
    with open(file_path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            day = int(row["day"])
            date_str = row["date"]
            dt = datetime.strptime(date_str, "%Y-%m-%d").date()
            
            # Find all ball_X keys
            balls = []
            i = 1
            while f"ball_{i}" in row:
                balls.append(int(row[f"ball_{i}"]))
                i += 1
                
            pb = int(row["powerball"])
            
            records.append({
                "day": day,
                "date": dt,
                "main_balls": balls,
                "powerball": pb,
                "year": dt.year
            })
            last_day = day
            last_year = dt.year
            
    return records, last_day, last_year

def append_csv_results(
    file_path: str,
    new_draws: List[Tuple[Any, List[int], int]],
    last_completed_day: int,
    existing_records: List[Dict[str, Any]]
) -> int:
    # Get balls count from new draws or existing
    num_main = len(new_draws[0][1]) if new_draws else 5
    
    # Header fields
    fieldnames = ["day", "date"] + [f"ball_{i}" for i in range(1, num_main + 1)] + ["powerball"]
    
    # Write existing + new records
    records_to_write = []
    for r in existing_records:
        row_dict = {"day": r["day"], "date": r["date"].strftime("%Y-%m-%d"), "powerball": r["powerball"]}
        for idx, val in enumerate(r["main_balls"]):
            row_dict[f"ball_{idx+1}"] = val
        records_to_write.append(row_dict)
        
    current_day = last_completed_day
    appended_count = 0
    for draw_date, main_balls, powerball in new_draws:
        current_day += 1
        row_dict = {
            "day": current_day,
            "date": draw_date.strftime("%Y-%m-%d"),
            "powerball": powerball
        }
        for idx, val in enumerate(main_balls):
            row_dict[f"ball_{idx+1}"] = val
        records_to_write.append(row_dict)
        appended_count += 1
        
    with open(file_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records_to_write)
        
    return appended_count

# ==================== JSON FORMAT HANDLERS ====================

def parse_json_dataset(file_path: str) -> Tuple[List[Dict[str, Any]], int, int]:
    records = []
    last_day = 0
    last_year = 2009
    
    if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
        return [], 0, last_year
        
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        for row in data:
            day = int(row["day"])
            dt = datetime.strptime(row["date"], "%Y-%m-%d").date()
            records.append({
                "day": day,
                "date": dt,
                "main_balls": row["main_balls"],
                "powerball": row["powerball"],
                "year": dt.year
            })
            last_day = day
            last_year = dt.year
            
    return records, last_day, last_year

def append_json_results(
    file_path: str,
    new_draws: List[Tuple[Any, List[int], int]],
    last_completed_day: int,
    existing_records: List[Dict[str, Any]]
) -> int:
    records_to_write = []
    for r in existing_records:
        records_to_write.append({
            "day": r["day"],
            "date": r["date"].strftime("%Y-%m-%d"),
            "main_balls": r["main_balls"],
            "powerball": r["powerball"]
        })
        
    current_day = last_completed_day
    appended_count = 0
    for draw_date, main_balls, powerball in new_draws:
        current_day += 1
        records_to_write.append({
            "day": current_day,
            "date": draw_date.strftime("%Y-%m-%d"),
            "main_balls": main_balls,
            "powerball": powerball
        })
        appended_count += 1
        
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(records_to_write, f, indent=2)
        
    return appended_count

# ==================== SQLITE FORMAT HANDLERS ====================

def parse_sqlite_dataset(file_path: str) -> Tuple[List[Dict[str, Any]], int, int]:
    records = []
    last_day = 0
    last_year = 2009
    
    if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
        return [], 0, last_year
        
    conn = sqlite3.connect(file_path)
    cursor = conn.cursor()
    
    # Check if table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='draw_results'")
    if not cursor.fetchone():
        conn.close()
        return [], 0, last_year
        
    # Get column names
    cursor.execute("PRAGMA table_info(draw_results)")
    cols = [col[1] for col in cursor.fetchall()]
    
    cursor.execute("SELECT * FROM draw_results ORDER BY day ASC")
    rows = cursor.fetchall()
    
    for row in rows:
        row_dict = dict(zip(cols, row))
        day = row_dict["day"]
        dt = datetime.strptime(row_dict["date"], "%Y-%m-%d").date()
        
        # Assemble main balls
        balls = []
        i = 1
        while f"ball_{i}" in row_dict:
            balls.append(row_dict[f"ball_{i}"])
            i += 1
            
        pb = row_dict["powerball"]
        
        records.append({
            "day": day,
            "date": dt,
            "main_balls": balls,
            "powerball": pb,
            "year": dt.year
        })
        last_day = day
        last_year = dt.year
        
    conn.close()
    return records, last_day, last_year

def append_sqlite_results(
    file_path: str,
    new_draws: List[Tuple[Any, List[int], int]],
    last_completed_day: int
) -> int:
    num_main = len(new_draws[0][1]) if new_draws else 5
    conn = sqlite3.connect(file_path)
    cursor = conn.cursor()
    
    # Create Table
    ball_cols = ", ".join(f"ball_{i} INTEGER" for i in range(1, num_main + 1))
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS draw_results (
            day INTEGER PRIMARY KEY,
            date TEXT,
            {ball_cols},
            powerball INTEGER
        )
    """)
    conn.commit()
    
    current_day = last_completed_day
    appended_count = 0
    
    cols = ["day", "date"] + [f"ball_{i}" for i in range(1, num_main + 1)] + ["powerball"]
    # Sanitize database identifiers to prevent potential SQL injection vectors
    for col in cols:
        if not re.match(r"^[a-zA-Z0-9_]+$", col):
            raise ValueError(f"Dangerous database identifier detected: {col}")
            
    placeholders = ", ".join("?" for _ in cols)
    sql = f"INSERT INTO draw_results ({', '.join(cols)}) VALUES ({placeholders})"
    
    rows_to_insert = []
    for draw_date, main_balls, powerball in new_draws:
        current_day += 1
        row = [current_day, draw_date.strftime("%Y-%m-%d")] + main_balls + [powerball]
        rows_to_insert.append(row)
        appended_count += 1
        
    cursor.executemany(sql, rows_to_insert)
    conn.commit()
    conn.close()
    
    return appended_count

# ==================== MAIN FORWARD INTERFACE ====================

def parse_existing_dataset(file_path: str, format_override: Optional[str] = None) -> Tuple[List[Any], int, int]:
    """
    Interface compatible with main.py.
    Returns:
        - lines_to_keep: Custom representation of rows to retain (varies by format)
        - last_completed_day: Day number of last completed draw
        - last_completed_year: Year of last completed draw
    """
    file_format = get_file_format(file_path, format_override)
    
    if file_format == 'txt':
        records, lines_to_keep, last_day, last_year = parse_txt_dataset(file_path)
        return lines_to_keep, last_day, last_year
    elif file_format == 'csv':
        records, last_day, last_year = parse_csv_dataset(file_path)
        return records, last_day, last_year
    elif file_format == 'json':
        records, last_day, last_year = parse_json_dataset(file_path)
        return records, last_day, last_year
    elif file_format == 'sqlite':
        records, last_day, last_year = parse_sqlite_dataset(file_path)
        return records, last_day, last_year
        
    return [], 0, 2009

def append_new_results(
    file_path: str,
    new_draws: List[Tuple[Any, List[int], int]],
    last_completed_day: int,
    last_completed_year: int,
    existing_data: List[Any],
    format_override: Optional[str] = None
) -> int:
    """
    Interface compatible with main.py.
    """
    file_format = get_file_format(file_path, format_override)
    
    if file_format == 'txt':
        return append_txt_results(file_path, new_draws, last_completed_day, last_completed_year, existing_data)
    elif file_format == 'csv':
        return append_csv_results(file_path, new_draws, last_completed_day, existing_data)
    elif file_format == 'json':
        return append_json_results(file_path, new_draws, last_completed_day, existing_data)
    elif file_format == 'sqlite':
        return append_sqlite_results(file_path, new_draws, last_completed_day)
        
    raise ValueError(f"Unsupported file format: {file_format}")
