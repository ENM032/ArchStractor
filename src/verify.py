import re
import os
import sys
from datetime import date
from validator import validate_draw_data

HEADER_re = re.compile(r"^===\s+(\d{4})\s+===$")
COMPLETED_re = re.compile(r"^Day\s+(\d+)\s+-\s+\[(\d+(?:,\d+)*,\[\d+\])\]$")
PLACEHOLDER_re = re.compile(r"^Day\s+(\d+)\s+-\s+\[\]$")

def verify_dataset(file_path: str) -> bool:
    if not os.path.exists(file_path):
        print(f"Error: Dataset file not found at {file_path}")
        return False
        
    print(f"Verifying dataset health: {file_path}")
    
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = [line.rstrip("\r\n") for line in f]
    except IOError as e:
        print(f"Error reading dataset file: {e}")
        return False
        
    errors = []
    current_year = None
    expected_day = 1
    total_completed = 0
    total_placeholders = 0
    years_seen = []
    
    for line_num, line in enumerate(lines, 1):
        # 1. Check Year Header
        header_match = HEADER_re.match(line)
        if header_match:
            year = int(header_match.group(1))
            if current_year is not None and year <= current_year:
                errors.append(f"Line {line_num}: Year {year} is not strictly greater than previous year {current_year}")
            current_year = year
            years_seen.append(year)
            continue
            
        # 2. Check Completed Entry
        comp_match = COMPLETED_re.match(line)
        if comp_match:
            day_num = int(comp_match.group(1))
            if day_num != expected_day:
                errors.append(f"Line {line_num}: Expected Day {expected_day}, but got Day {day_num}")
            expected_day = day_num + 1
            
            # Parse the inner numbers
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
                
            # Perform validation via the central validator
            # (Note: draw_date is set to today's date for verification, as the date isn't stored in dataset_2.txt)
            is_valid, err_msg = validate_draw_data(date.today(), main_nums, pb)
            if not is_valid:
                errors.append(f"Line {line_num}: {err_msg}")
                
            total_completed += 1
            continue
            
        # 3. Check Placeholder Entry
        placeholder_match = PLACEHOLDER_re.match(line)
        if placeholder_match:
            day_num = int(placeholder_match.group(1))
            if day_num != expected_day:
                errors.append(f"Line {line_num}: Expected Day {expected_day}, but got Day {day_num}")
            expected_day = day_num + 1
            total_placeholders += 1
            continue
            
        # If line is completely empty, it might be an error or whitespace
        if not line.strip():
            errors.append(f"Line {line_num}: Empty line detected")
            continue
            
        errors.append(f"Line {line_num}: Malformed line: '{line}'")
        
    print("\nVerification Results:")
    print(f"- Total lines checked: {len(lines)}")
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
