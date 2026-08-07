import sys
import os
import shutil
import logging
from datetime import date
from scraper import fetch_page
from parser import parse_html_page
from formatter import parse_existing_dataset, append_new_results
from validator import validate_draw_data

# Set up logging to both console and a file for robust tracking
log_format = "%(asctime)s [%(levelname)s] %(message)s"
logging.basicConfig(
    level=logging.INFO,
    format=log_format,
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("extraction.log", encoding="utf-8")
    ],
    force=True
)
logger = logging.getLogger(__name__)

DATASET_PATH = "data/dataset_2.txt"
BACKUP_PATH = "data/dataset_2.txt.bak"

def main():
    logger.info("Starting SA PowerBall Draw Results Extraction process")
    
    # 1. Parse the existing dataset
    if not os.path.exists(DATASET_PATH):
        logger.error(f"Dataset file not found at {DATASET_PATH}. Cannot continue.")
        sys.exit(1)
        
    try:
        lines_to_keep, last_completed_day, last_completed_year = parse_existing_dataset(DATASET_PATH)
        logger.info(f"Existing dataset parsed. Last completed Day {last_completed_day} in year {last_completed_year}")
    except IOError as e:
        logger.error(f"Failed to read existing dataset: {e}")
        sys.exit(1)
        
    # The last completed day in 2010 is Day 21, which is 2010-01-05.
    # Any draws on or before 2010-01-05 should be skipped as duplicates.
    cutoff_date = date(2010, 1, 5)
    
    # 2. Fetch and parse results for each year from 2010 to 2026
    all_new_draws = []
    failed_urls = []
    skipped_duplicates = 0
    validation_failures = 0
    years_processed = []
    
    for year in range(2010, 2027):
        url = f"https://za.national-lottery.com/powerball/results/{year}-archive"
        try:
            html = fetch_page(url, retries=1)
            draws = parse_html_page(html)
            logger.info(f"Year {year}: parsed {len(draws)} draws from webpage")
            
            # Sort chronologically (oldest to newest)
            draws.sort(key=lambda x: x[0])
            
            year_new_draws = []
            for draw_date, main_balls, powerball in draws:
                # Use validator to check data correctness
                is_valid, err_msg = validate_draw_data(draw_date, main_balls, powerball)
                if not is_valid:
                    logger.warning(f"Validation failure for draw in year {year}: {err_msg}")
                    validation_failures += 1
                    continue
                
                # Check for duplicates (on or before cutoff date)
                if draw_date <= cutoff_date:
                    skipped_duplicates += 1
                    continue
                
                year_new_draws.append((draw_date, main_balls, powerball))
                
            all_new_draws.extend(year_new_draws)
            years_processed.append(year)
            logger.info(f"Year {year}: added {len(year_new_draws)} new draws")
            
        except Exception as e:
            logger.error(f"Failed to process year {year}: {e}")
            failed_urls.append(url)
            
    # 3. Verify chronological order and uniqueness of the entire new dataset
    all_new_draws.sort(key=lambda x: x[0])
    
    # Check for duplicate dates in the scraped data
    unique_draws = []
    seen_dates = set()
    for item in all_new_draws:
        d_date = item[0]
        if d_date in seen_dates:
            logger.warning(f"Duplicate date detected in scraped results: {d_date}. Skipping.")
            skipped_duplicates += 1
            continue
        seen_dates.add(d_date)
        unique_draws.append(item)
        
    logger.info(f"Total new draws to append after validation: {len(unique_draws)}")
    
    # 4. Create a backup of the existing file before modifying it
    try:
        logger.info(f"Creating backup of {DATASET_PATH} at {BACKUP_PATH}")
        shutil.copy2(DATASET_PATH, BACKUP_PATH)
    except IOError as e:
        logger.error(f"Failed to create backup file: {e}. Aborting write.")
        sys.exit(1)
        
    # 5. Append the results to the dataset file
    appended_count = 0
    if unique_draws:
        try:
            appended_count = append_new_results(
                DATASET_PATH,
                unique_draws,
                last_completed_day,
                last_completed_year,
                lines_to_keep
            )
            logger.info(f"Successfully appended {appended_count} records to {DATASET_PATH}")
        except IOError as e:
            logger.error(f"Failed to write results to dataset: {e}. Restoring backup...")
            try:
                shutil.copy2(BACKUP_PATH, DATASET_PATH)
                logger.info("Backup successfully restored.")
            except IOError as restore_err:
                logger.critical(f"Failed to restore backup: {restore_err}. Source dataset may be corrupted!")
            sys.exit(1)
    else:
        logger.info("No new draw records to append.")
        
    # 6. Output Summary Report
    print("\n" + "="*40)
    print("EXTRACTION SUMMARY")
    print("="*40)
    print(f"Years processed: {years_processed}")
    print(f"Number of records added: {appended_count}")
    print(f"Number of duplicates skipped: {skipped_duplicates}")
    print(f"Number of validation failures: {validation_failures}")
    if failed_urls:
        print(f"Failed URLs: {failed_urls}")
    else:
        print("Failed URLs: None")
    print("="*40 + "\n")

if __name__ == "__main__":
    main()
