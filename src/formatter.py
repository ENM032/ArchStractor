import re
import os
from typing import List, Tuple, Dict
from datetime import datetime

HEADER_re = re.compile(r"^===\s+(\d{4})\s+===$")
COMPLETED_re = re.compile(r"^Day\s+(\d+)\s+-\s+\[(\d+(?:,\d+)*,\[\d+\])\]$")
PLACEHOLDER_re = re.compile(r"^Day\s+(\d+)\s+-\s+\[\]$")

def detect_line_ending(file_path: str) -> str:
    """Detects the line ending of the file (CRLF or LF). Defaults to LF."""
    if not os.path.exists(file_path):
        return "\n"
    with open(file_path, "rb") as f:
        content = f.read(4096)
        if b"\r\n" in content:
            return "\r\n"
    return "\n"

def parse_existing_dataset(file_path: str) -> Tuple[List[str], int, int]:
    """
    Parses the existing file.
    Returns:
        - lines_to_keep: List of lines (without trailing newline) to keep.
        - last_completed_day: The day number of the last completed entry.
        - last_completed_year: The year of the last completed entry.
    """
    if not os.path.exists(file_path):
        return [], 0, 2009

    with open(file_path, "r", encoding="utf-8") as f:
        lines = [line.rstrip("\r\n") for line in f]

    last_completed_idx = -1
    last_completed_day = 0
    current_year = 2009
    year_map = {} # Maps day_num to year

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
            continue

    # Keep all lines up to the last completed index
    if last_completed_idx == -1:
        # If no completed entries, start from scratch
        return [], 0, 2009

    lines_to_keep = lines[:last_completed_idx + 1]
    last_completed_year = year_map.get(last_completed_day, 2009)

    return lines_to_keep, last_completed_day, last_completed_year

def format_draw_result(day_num: int, main_balls: List[int], powerball: int) -> str:
    """Formats a single draw entry as: Day X - [N1,N2,N3,N4,N5,[PB]]"""
    balls_str = ",".join(map(str, main_balls))
    return f"Day {day_num} - [{balls_str},[{powerball}]]"

def append_new_results(
    file_path: str,
    new_draws: List[Tuple[datetime.date, List[int], int]],
    last_completed_day: int,
    last_completed_year: int,
    lines_to_keep: List[str]
) -> int:
    """
    Appends new draw results to the dataset file, formatting headers and entries.
    Returns the number of new records appended.
    """
    line_ending = detect_line_ending(file_path)
    output_lines = list(lines_to_keep)
    
    current_day = last_completed_day
    current_year = last_completed_year

    appended_count = 0

    for draw_date, main_balls, powerball in new_draws:
        draw_year = draw_date.year
        
        # If we transitioned to a new year, add the header
        if draw_year > current_year:
            output_lines.append(f"=== {draw_year} ===")
            current_year = draw_year

        current_day += 1
        entry_str = format_draw_result(current_day, main_balls, powerball)
        output_lines.append(entry_str)
        appended_count += 1

    # Write the file back
    with open(file_path, "w", encoding="utf-8", newline="") as f:
        # Write with explicit line endings
        f.write(line_ending.join(output_lines) + line_ending)

    return appended_count
