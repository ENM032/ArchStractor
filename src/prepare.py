import os
import sys
import re
import csv
import json
import sqlite3
import logging
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Tuple, Optional

# Add src/ to path so we can import from existing modules
src_dir = os.path.dirname(os.path.abspath(__file__))
if src_dir not in sys.path:
    sys.path.append(src_dir)

from scraper import fetch_page, get_cache_path
from parser import parse_html_page
from formatter import parse_txt_dataset
from validator import validate_draw_data

# Configure logging
log_format = "%(asctime)s [%(levelname)s] %(message)s"
logging.basicConfig(
    level=logging.INFO,
    format=log_format,
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("preparation.log", encoding="utf-8")
    ],
    force=True
)
logger = logging.getLogger(__name__)

def detect_game_type(file_name: str, sample_records: List[Dict[str, Any]]) -> str:
    """Infers the game type based on the file name or parsed records schema."""
    name_lower = file_name.lower()
    if "lotto" in name_lower:
        return "lotto"
    if "xtra" in name_lower:
        return "powerball-xtra"
    
    # Fallback to record inspection
    if sample_records:
        first_rec = sample_records[0]
        main_balls = first_rec.get("main_balls", [])
        if len(main_balls) == 6:
            return "lotto"
            
    return "powerball"

def fetch_and_parse_crawled_draws(game: str, start_year: int, end_year: int) -> List[Tuple[date, List[int], int]]:
    """Loads all archived HTML files for the game and extracts draw dates and numbers."""
    crawled_draws = []
    
    # Resolve URL template
    if game == "powerball-xtra":
        url_template = "https://za.national-lottery.com/powerball-xtra/results/{year}-archive"
    elif game == "lotto":
        url_template = "https://za.national-lottery.com/lotto/results/{year}-archive"
    else:
        url_template = "https://za.national-lottery.com/powerball/results/{year}-archive"
        
    for year in range(start_year, end_year + 1):
        url = url_template.format(year=year)
        cache_path = get_cache_path(url)
        
        html_content = ""
        if cache_path and os.path.exists(cache_path):
            logger.debug(f"Loading {game} year {year} from cache.")
            with open(cache_path, "r", encoding="utf-8") as f:
                html_content = f.read()
        else:
            logger.info(f"Cache miss or non-cacheable year for {game} year {year}. Fetching from web...")
            try:
                html_content = fetch_page(url, retries=1)
            except Exception as e:
                logger.error(f"Failed to fetch {game} results page for {year}: {e}")
                continue
                
        if html_content:
            try:
                year_draws, _ = parse_html_page(html_content)
                crawled_draws.extend(year_draws)
            except Exception as e:
                logger.error(f"Error parsing HTML content for {game} year {year}: {e}")
                
    # Sort chronologically (oldest to newest)
    crawled_draws.sort(key=lambda x: x[0])
    return crawled_draws

def check_gaps_and_anomalies(
    game: str,
    records: List[Dict[str, Any]]
) -> Tuple[List[str], List[str]]:
    """
    Checks for:
    - Sequencing gaps (e.g. Day 1, Day 3)
    - Chronological date gaps based on expected lottery schedule
    - Ball counts and range violations
    """
    warnings = []
    gaps = []
    
    if not records:
        return warnings, gaps
        
    # 1. Check Sequencing gaps
    expected_day = 1
    for idx, rec in enumerate(records):
        day = rec["day"]
        if day != expected_day:
            warnings.append(f"Sequence Gap: Expected Day {expected_day}, but got Day {day} at index {idx}.")
        expected_day = day + 1
        
    # 2. Check Date Gaps
    # Filter records that have valid mapped dates
    valid_dates = sorted([rec["date"] for rec in records if rec.get("date") is not None])
    
    if len(valid_dates) > 1:
        start_date = valid_dates[0]
        end_date = valid_dates[-1]
        
        # Expected draw days (0=Mon, 1=Tue, 2=Wed, 3=Thu, 4=Fri, 5=Sat, 6=Sun)
        if game == "lotto":
            expected_weekdays = {2, 5}  # Wednesday and Saturday
        else:
            expected_weekdays = {1, 4}  # Tuesday and Friday for PowerBall / PB Xtra
            
        current_date = start_date
        records_dates_set = set(valid_dates)
        
        while current_date <= end_date:
            if current_date.weekday() in expected_weekdays:
                if current_date not in records_dates_set:
                    gaps.append(f"Missing Draw Date: No draw recorded on expected date {current_date} ({current_date.strftime('%A')}).")
            current_date += timedelta(days=1)
            
    # 3. Check ranges and duplicate dates
    seen_dates = set()
    for rec in records:
        day = rec["day"]
        draw_date = rec.get("date")
        main_balls = rec["main_balls"]
        powerball = rec["powerball"]
        
        # Uniqueness of date
        if draw_date:
            if draw_date in seen_dates:
                warnings.append(f"Duplicate Date: Day {day} has duplicate date {draw_date}.")
            seen_dates.add(draw_date)
            
        # Call common validator
        is_valid, err_msg = validate_draw_data(
            draw_date or date.today(),
            main_balls,
            powerball,
            len(main_balls),
            1
        )
        if not is_valid:
            warnings.append(f"Validation Failure at Day {day}: {err_msg}")
            
    return warnings, gaps

def engineer_features(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Calculates statistical and ML features for each draw record."""
    enriched_records = []
    
    for rec in records:
        main_balls = rec["main_balls"]
        pb = rec["powerball"]
        draw_date = rec.get("date")
        
        # Raw items
        enriched = {
            "day": rec["day"],
            "date": draw_date.strftime("%Y-%m-%d") if draw_date else None,
            "year": draw_date.year if draw_date else rec["year"],
            "month": draw_date.month if draw_date else None,
            "day_of_month": draw_date.day if draw_date else None,
            "day_of_week": draw_date.weekday() if draw_date else None,
            "is_weekend": 1 if draw_date and draw_date.weekday() in {5, 6} else 0,
            "powerball": pb
        }
        
        # Main ball columns (ball_1 to ball_N)
        for idx, val in enumerate(main_balls):
            enriched[f"ball_{idx+1}"] = val
            
        # Statistical features
        if main_balls:
            enriched["sum_main_balls"] = sum(main_balls)
            enriched["mean_main_balls"] = round(sum(main_balls) / len(main_balls), 2)
            enriched["min_main_ball"] = min(main_balls)
            enriched["max_main_ball"] = max(main_balls)
            enriched["range_main_balls"] = max(main_balls) - min(main_balls)
            enriched["odd_count"] = sum(1 for x in main_balls if x % 2 != 0)
            enriched["even_count"] = sum(1 for x in main_balls if x % 2 == 0)
        else:
            enriched["sum_main_balls"] = 0
            enriched["mean_main_balls"] = 0.0
            enriched["min_main_ball"] = 0
            enriched["max_main_ball"] = 0
            enriched["range_main_balls"] = 0
            enriched["odd_count"] = 0
            enriched["even_count"] = 0
            
        enriched["is_powerball_even"] = 1 if pb % 2 == 0 else 0
        enriched["raw_main_balls"] = main_balls  # kept for internal reference if needed
        enriched_records.append(enriched)
        
    return enriched_records

# ==================== EXPORTER FUNCTIONS ====================

def export_to_csv(filepath: str, records: List[Dict[str, Any]], num_main: int):
    """Exports records to a structured CSV file."""
    if not records:
        return
        
    # Establish headers order
    fields = ["day", "date", "year", "month", "day_of_month", "day_of_week", "is_weekend"]
    fields.extend(f"ball_{i}" for i in range(1, num_main + 1))
    fields.extend([
        "powerball",
        "sum_main_balls",
        "mean_main_balls",
        "min_main_ball",
        "max_main_ball",
        "range_main_balls",
        "odd_count",
        "even_count",
        "is_powerball_even"
    ])
    
    try:
        with open(filepath, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(records)
    except IOError as e:
        logger.error(f"IOError exporting cleaned data to CSV {filepath}: {e}")

def export_to_json(filepath: str, records: List[Dict[str, Any]]):
    """Exports records to a JSON array of objects."""
    # Build clean output objects (removing helper fields like raw_main_balls)
    clean_records = []
    for r in records:
        clean_rec = dict(r)
        clean_rec.pop("raw_main_balls", None)
        clean_records.append(clean_rec)
        
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(clean_records, f, indent=2)
    except IOError as e:
        logger.error(f"IOError exporting cleaned data to JSON {filepath}: {e}")

def export_to_sqlite(filepath: str, table_name: str, records: List[Dict[str, Any]], num_main: int):
    """Exports records to an SQLite database table."""
    if not records:
        return
        
    conn = None
    try:
        import re
        # Sanitize database table name to prevent SQL injection
        if not re.match(r"^[a-zA-Z0-9_]+$", table_name):
            raise ValueError(f"Dangerous database table name detected: {table_name}")
            
        conn = sqlite3.connect(filepath)
        cursor = conn.cursor()
        
        # Drop existing table if any
        cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
        
        # Create Table schema
        ball_cols = ", ".join(f"ball_{i} INTEGER" for i in range(1, num_main + 1))
        schema_sql = f"""
            CREATE TABLE {table_name} (
                day INTEGER PRIMARY KEY,
                date TEXT,
                year INTEGER,
                month INTEGER,
                day_of_month INTEGER,
                day_of_week INTEGER,
                is_weekend INTEGER,
                {ball_cols},
                powerball INTEGER,
                sum_main_balls INTEGER,
                mean_main_balls REAL,
                min_main_ball INTEGER,
                max_main_ball INTEGER,
                range_main_balls INTEGER,
                odd_count INTEGER,
                even_count INTEGER,
                is_powerball_even INTEGER
            )
        """
        cursor.execute(schema_sql)
        
        # Insert rows
        cols = ["day", "date", "year", "month", "day_of_month", "day_of_week", "is_weekend"]
        cols.extend(f"ball_{i}" for i in range(1, num_main + 1))
        cols.extend([
            "powerball",
            "sum_main_balls",
            "mean_main_balls",
            "min_main_ball",
            "max_main_ball",
            "range_main_balls",
            "odd_count",
            "even_count",
            "is_powerball_even"
        ])
        
        # Sanitize column names
        for col in cols:
            if not re.match(r"^[a-zA-Z0-9_]+$", col):
                raise ValueError(f"Dangerous database column name detected: {col}")
                
        placeholders = ", ".join("?" for _ in cols)
        insert_sql = f"INSERT INTO {table_name} ({', '.join(cols)}) VALUES ({placeholders})"
        
        rows_to_insert = []
        for r in records:
            row = [r.get(c) for c in cols]
            rows_to_insert.append(row)
            
        cursor.executemany(insert_sql, rows_to_insert)
        conn.commit()
    except sqlite3.Error as e:
        logger.error(f"SQLite Error exporting cleaned data to {filepath}: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()

# ==================== MAIN RUNNER ====================

def clean_and_prepare_file(raw_filepath: str, output_dir: str):
    """Processes a single raw text dataset file, checks it, and exports cleaned versions."""
    file_name = os.path.basename(raw_filepath)
    logger.info(f"Processing raw dataset file: {raw_filepath}")
    
    # 1. Parse raw text file
    try:
        raw_records, _, _, _ = parse_txt_dataset(raw_filepath)
        logger.info(f"Successfully read {len(raw_records)} records from {file_name}")
    except Exception as e:
        logger.error(f"Error parsing raw dataset {raw_filepath}: {e}")
        return
        
    if not raw_records:
        logger.warning(f"No records found in {raw_filepath}. Skipping.")
        return
        
    # 2. Detect game details
    try:
        game = detect_game_type(file_name, raw_records)
        num_main = len(raw_records[0]["main_balls"])
        logger.info(f"Inferred Game Preset: {game.upper()} (Main Balls={num_main})")
    except Exception as e:
        logger.error(f"Failed to infer game details for {file_name}: {e}")
        return
        
    # 3. Load crawled results to align draw dates
    try:
        years = [rec["year"] for rec in raw_records if "year" in rec]
        if not years:
            raise ValueError("No year entries found in the raw records.")
        min_year = min(years)
        max_year = max(years)
        logger.info(f"Scraping/loading archive timeline: {min_year} to {max_year}")
        crawled_draws = fetch_and_parse_crawled_draws(game, min_year, max_year)
        logger.info(f"Loaded {len(crawled_draws)} chronological draws from archives.")
    except Exception as e:
        logger.error(f"Failed to fetch date-alignment archives for {game}: {e}")
        return
    
    # Build date lookup mapping
    # Key: (tuple(sorted(main_balls)), powerball) -> date
    date_lookup = {}
    for draw_date, main, pb in crawled_draws:
        key = (tuple(sorted(main)), pb)
        date_lookup[key] = draw_date
        
    # 4. Map dates to raw records
    mapped_count = 0
    fallback_count = 0
    
    for rec in raw_records:
        rec_key = (tuple(sorted(rec["main_balls"])), rec["powerball"])
        draw_date = date_lookup.get(rec_key)
        
        if draw_date:
            rec["date"] = draw_date
            mapped_count += 1
        else:
            # Fallback to index-based chronological alignment
            day_idx = rec["day"] - 1
            if 0 <= day_idx < len(crawled_draws):
                draw_date = crawled_draws[day_idx][0]
                rec["date"] = draw_date
                fallback_count += 1
            else:
                rec["date"] = None
                
    logger.info(f"Date alignment complete. Mapped strictly: {mapped_count}, Aligned chronologically: {fallback_count}")
    
    # 5. Gaps and Anomalies Detection
    warnings, gaps = check_gaps_and_anomalies(game, raw_records)
    
    # Output logs for warnings/gaps
    if warnings:
        logger.warning(f"Found {len(warnings)} validation warnings/anomalies:")
        for w in warnings[:5]:
            logger.warning(f"  * {w}")
        if len(warnings) > 5:
            logger.warning(f"  * ... and {len(warnings) - 5} more warnings.")
            
    if gaps:
        logger.warning(f"Found {len(gaps)} missing draw date gaps:")
        for g in gaps[:5]:
            logger.warning(f"  * {g}")
        if len(gaps) > 5:
            logger.warning(f"  * ... and {len(gaps) - 5} more gaps.")
            
    if not warnings and not gaps:
        logger.info("Dataset is clean. No sequence gaps, range anomalies, or missing draw dates found.")
        
    # 6. Feature Engineering
    logger.info("Engineering statistical & ML features...")
    cleaned_records = engineer_features(raw_records)
    
    # 7. Exports
    os.makedirs(output_dir, exist_ok=True)
    game_clean_name = game.replace("-", "_")
    
    csv_out = os.path.join(output_dir, f"{game_clean_name}_clean.csv")
    json_out = os.path.join(output_dir, f"{game_clean_name}_clean.json")
    sqlite_out = os.path.join(output_dir, f"{game_clean_name}_clean.db")
    
    logger.info(f"Exporting cleaned data to CSV: {csv_out}")
    export_to_csv(csv_out, cleaned_records, num_main)
    
    logger.info(f"Exporting cleaned data to JSON: {json_out}")
    export_to_json(json_out, cleaned_records)
    
    logger.info(f"Exporting cleaned data to SQLite: {sqlite_out}")
    export_to_sqlite(sqlite_out, "draw_results", cleaned_records, num_main)
    
    logger.info(f"Processing complete for {game.upper()}.\n" + "-"*40)

def main():
    logger.info("ArcStractor Data Cleaning and Preparation Pipeline Initiated")
    
    # Define directories
    raw_data_dir = "data"
    cleaned_data_dir = os.path.join(raw_data_dir, "cleaned")
    
    # Find all raw text files
    if not os.path.exists(raw_data_dir):
        logger.error(f"Raw data directory '{raw_data_dir}' does not exist. Aborting.")
        sys.exit(1)
        
    raw_files = [
        os.path.join(raw_data_dir, f)
        for f in os.listdir(raw_data_dir)
        if f.endswith(".txt") and not f.endswith(".bak")
    ]
    
    if not raw_files:
        logger.warning(f"No raw .txt dataset files found in '{raw_data_dir}'.")
        sys.exit(0)
        
    logger.info(f"Discovered {len(raw_files)} raw files to process: {raw_files}")
    
    for rf in raw_files:
        clean_and_prepare_file(rf, cleaned_data_dir)
        
    logger.info("All datasets successfully cleaned, prepared, and exported!")

if __name__ == "__main__":
    main()
