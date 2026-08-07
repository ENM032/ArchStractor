import re
import os
import sys
from datetime import date
from typing import Tuple
from validator import validate_draw_data
from formatter import parse_existing_dataset, get_file_format

HEADER_re = re.compile(r"^===\s+(\d{4})\s+===$")
COMPLETED_re = re.compile(r"^Day\s+(\d+)\s+-\s+\[(\d+(?:,\d+)*,\[\d+\])\]$")
PLACEHOLDER_re = re.compile(r"^Day\s+(\d+)\s+-\s+\[\]$")

def verify_txt_dataset(lines: list, errors: list) -> Tuple[int, int, list]:
    current_year = None
    expected_day = 1
    total_completed = 0
    total_placeholders = 0
    years_seen = []
    
    for line_num, line in enumerate(lines, 1):
        header_match = HEADER_re.match(line)
        if header_match:
            year = int(header_match.group(1))
            if current_year is not None and year <= current_year:
                errors.append(f"Line {line_num}: Year {year} is not strictly greater than previous year {current_year}")
            current_year = year
            years_seen.append(year)
            continue
            
        comp_match = COMPLETED_re.match(line)
        if comp_match:
            day_num = int(comp_match.group(1))
            if day_num != expected_day:
                errors.append(f"Line {line_num}: Expected Day {expected_day}, but got Day {day_num}")
            expected_day = day_num + 1
            
            inner_content = comp_match.group(2)
            parts = re.split(r",?\[", inner_content)
            if len(parts) < 2:
                errors.append(f"Line {line_num}: Invalid structure in brackets: '{inner_content}'")
                continue
                
            main_nums_str = parts[0].rstrip(",")
            pb_str = parts[1].rstrip("]")
            
            try:
                main_nums = [int(x) for x in main_nums_str.split(",")]
                pb = int(pb_str)
            except ValueError:
                errors.append(f"Line {line_num}: Failed to parse balls/PowerBall as integers: '{inner_content}'")
                continue
                
            is_valid, err_msg = validate_draw_data(date.today(), main_nums, pb, len(main_nums), 1)
            if not is_valid:
                errors.append(f"Line {line_num}: {err_msg}")
                
            total_completed += 1
            continue
            
        placeholder_match = PLACEHOLDER_re.match(line)
        if placeholder_match:
            day_num = int(placeholder_match.group(1))
            if day_num != expected_day:
                errors.append(f"Line {line_num}: Expected Day {expected_day}, but got Day {day_num}")
            expected_day = day_num + 1
            total_placeholders += 1
            continue
            
        if not line.strip():
            errors.append(f"Line {line_num}: Empty line detected")
            continue
            
        errors.append(f"Line {line_num}: Malformed line: '{line}'")
        
    return total_completed, total_placeholders, years_seen

def verify_records_dataset(records: list, errors: list) -> Tuple[int, int, list]:
    expected_day = 1
    last_year = None
    years_seen = []
    total_completed = 0
    
    for idx, r in enumerate(records):
        day = r["day"]
        year = r["year"]
        main_balls = r["main_balls"]
        powerball = r["powerball"]
        
        # Verify Day Sequence
        if day != expected_day:
            errors.append(f"Index {idx}: Expected Day {expected_day}, but got Day {day}")
        expected_day = day + 1
        
        # Verify Year sequence
        if last_year is not None and year < last_year:
            errors.append(f"Index {idx} (Day {day}): Year {year} is less than previous year {last_year}")
        last_year = year
        if year not in years_seen:
            years_seen.append(year)
            
        # Verify data constraints
        # Set date to r["date"] if not None, otherwise default to today
        draw_date = r["date"] if r["date"] is not None else date.today()
        is_valid, err_msg = validate_draw_data(draw_date, main_balls, powerball, len(main_balls), 1)
        if not is_valid:
            errors.append(f"Day {day} ({draw_date}): {err_msg}")
            
        total_completed += 1
        
    return total_completed, 0, years_seen

def verify_dataset(file_path: str) -> bool:
    if not os.path.exists(file_path):
        print(f"Error: Dataset file not found at {file_path}")
        return False
        
    print(f"Verifying dataset health: {file_path}")
    file_format = get_file_format(file_path)
    errors = []
    
    total_completed = 0
    total_placeholders = 0
    years_seen = []
    total_lines = 0
    
    if file_format == 'txt':
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                lines = [line.rstrip("\r\n") for line in f]
                total_lines = len(lines)
            total_completed, total_placeholders, years_seen = verify_txt_dataset(lines, errors)
        except IOError as e:
            print(f"Error reading dataset file: {e}")
            return False
    else:
        # Load through formatter parser as structured records
        try:
            records, _, _ = parse_existing_dataset(file_path)
            total_lines = len(records)
            total_completed, total_placeholders, years_seen = verify_records_dataset(records, errors)
        except Exception as e:
            print(f"Error parsing database/structured records: {e}")
            return False
            
    print("\nVerification Results:")
    print(f"- Total records/lines checked: {total_lines}")
    print(f"- Years seen: {years_seen}")
    print(f"- Completed records: {total_completed}")
    print(f"- Placeholder records: {total_placeholders}")
    
    if errors:
        print(f"\n[FAIL] Found {len(errors)} validation errors:")
        for err in errors[:20]:  # print first 20 errors
            print(f"  * {err}")
        if len(errors) > 20:
            print(f"  * ... and {len(errors) - 20} more errors")
        return False
        
    print("\n[PASS] Dataset is healthy, structured correctly, and chronologically complete!")
    return True

if __name__ == "__main__":
    file_to_check = sys.argv[1] if len(sys.argv) > 1 else "data/dataset_2.txt"
    success = verify_dataset(file_to_check)
    sys.exit(0 if success else 1)
