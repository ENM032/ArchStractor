import sys
import os
import shutil
import logging
import argparse
import re
from datetime import date
from typing import List, Tuple, Optional, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
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

def get_last_completed_draw_balls(last_line: str) -> Tuple[Optional[List[int]], Optional[int]]:
    """
    Parses the ball numbers from the last completed draw line in dataset (for TXT format).
    Example: "Day 21 - [1,8,31,43,44,[11]]" -> ([1, 8, 31, 43, 44], 11)
    """
    match = re.match(r"^Day\s+\d+\s+-\s+\[(\d+(?:,\d+)*,\[\d+\])\]$", last_line)
    if not match:
        return None, None
    inner = match.group(1)
    parts = re.split(r",?\[", inner)
    if len(parts) < 2:
        return None, None
    main_nums_str = parts[0].rstrip(",")
    pb_str = parts[1].rstrip("]")
    try:
        main_nums = [int(x) for x in main_nums_str.split(",")]
        pb = int(pb_str)
        return main_nums, pb
    except ValueError:
        return None, None

def fetch_and_parse_year(
    year: int, 
    url_template: str
) -> Tuple[int, List[Tuple[date, List[int], int]], Dict[str, int], int, Optional[str]]:
    """
    Fetches and parses SA lottery results for a single year.
    Returns: (year, valid_draws, schema, validation_failures, error_url)
    """
    url = url_template.format(year=year)
    validation_fails = 0
    try:
        html = fetch_page(url, retries=1)
        draws, schema = parse_html_page(html)
        logger.info(f"Year {year}: parsed {len(draws)} draws from webpage using schema {schema}")
        
        # Sort chronologically (oldest to newest)
        draws.sort(key=lambda x: x[0])
        
        year_new_draws = []
        for draw_date, main_balls, powerball in draws:
            is_valid, err_msg = validate_draw_data(
                draw_date, main_balls, powerball,
                schema.get("num_main_balls", 5),
                schema.get("num_power_balls", 1)
            )
            if not is_valid:
                logger.warning(f"Validation failure for draw in year {year}: {err_msg}")
                validation_fails += 1
                continue
            
            year_new_draws.append((draw_date, main_balls, powerball))
            
        return year, year_new_draws, schema, validation_fails, None
        
    except Exception as e:
        logger.error(f"Failed to process year {year}: {e}")
        return year, [], {"num_main_balls": 5, "num_power_balls": 1}, 0, url

def run_interactive_wizard() -> Tuple[int, int, Optional[str], str, Optional[str]]:
    """
    Launches a clean, interactive terminal wizard to configure settings.
    Returns: (start_year, end_year, url_template, output_path, game)
    """
    print("\n" + "="*50)
    print("      ArcStractor Interactive Configuration Wizard")
    print("="*50)
    
    # 1. Choose Game Preset
    print("\nSelect Game Preset:")
    print("  [1] PowerBall (Default)")
    print("  [2] PowerBall Xtra")
    print("  [3] Lotto")
    choice = input("Enter choice (1-3) [1]: ").strip()
    if choice == "2":
        game = "powerball-xtra"
    elif choice == "3":
        game = "lotto"
    else:
        game = "powerball"
    
    # 2. Year Range
    current_year = date.today().year
    print(f"\nEnter Year Range (available 2009-{current_year}):")
    
    start_input = input("Enter start year [2010]: ").strip()
    start_year = int(start_input) if start_input.isdigit() else 2010
    
    end_input = input(f"Enter end year [{current_year}]: ").strip()
    end_year = int(end_input) if end_input.isdigit() else current_year
    
    # 3. Output Path
    if game == "powerball":
        default_output = "data/dataset_2.txt"
    elif game == "lotto":
        default_output = "data/dataset_lotto.txt"
    else:
        default_output = "data/dataset_xtra.txt"
        
    print(f"\nEnter Output Destination (supported: .txt, .csv, .json, .db, .sqlite):")
    output_path = input(f"Enter file path [{default_output}]: ").strip()
    if not output_path:
        output_path = default_output
        
    print("\n" + "-"*50)
    print("Configuration Summary:")
    print(f"  - Game Preset: {game.upper()}")
    print(f"  - Year Range: {start_year} to {end_year}")
    print(f"  - Output File: {output_path}")
    print("-"*50)
    
    confirm = input("Proceed with extraction? (y/n) [y]: ").strip().lower()
    if confirm == 'n':
        print("Extraction canceled.")
        sys.exit(0)
        
    if game == "powerball-xtra":
        url_template = "https://za.national-lottery.com/powerball-xtra/results/{year}-archive"
    elif game == "lotto":
        url_template = "https://za.national-lottery.com/lotto/results/{year}-archive"
    else:
        url_template = "https://za.national-lottery.com/powerball/results/{year}-archive"
        
    return start_year, end_year, url_template, output_path, game

def main():
    backup_path = None
    dataset_exists = False
    output_path = None
    
    try:
        # Detect if we should launch the wizard:
        # Trigger if no CLI args are passed AND standard input is an interactive terminal.
        if len(sys.argv) == 1 and sys.stdin.isatty():
            start_year, end_year, url_template, output_path, game = run_interactive_wizard()
        else:
            # Parse CLI Arguments
            parser = argparse.ArgumentParser(description="SA National Lottery results extraction and multi-format dataset builder")
            parser.add_argument("--start-year", "-s", type=int, default=2010, help="Start year for results retrieval (inclusive)")
            parser.add_argument("--end-year", "-e", type=int, default=2026, help="End year for results retrieval (inclusive)")
            parser.add_argument("--url-template", "-u", type=str, default=None, 
                                help="Base archive URL template with {year} placeholder")
            parser.add_argument("--output", "-o", type=str, default="data/dataset_2.txt", help="Output dataset file path (.txt, .csv, .json, .db, .sqlite)")
            parser.add_argument("--game", "-g", type=str, choices=["powerball", "powerball-xtra", "lotto"], default=None, 
                                help="Preset shortcut for URL template")
            args = parser.parse_args()

            start_year = args.start_year
            end_year = args.end_year
            output_path = args.output
            
            # Determine URL Template based on preset or custom value
            url_template = args.url_template
            if not url_template:
                game = args.game or "powerball"
                if game == "powerball-xtra":
                    url_template = "https://za.national-lottery.com/powerball-xtra/results/{year}-archive"
                elif game == "lotto":
                    url_template = "https://za.national-lottery.com/lotto/results/{year}-archive"
                else:
                    url_template = "https://za.national-lottery.com/powerball/results/{year}-archive"

        logger.info("Starting SA Lottery Draw Results Extraction process")
        logger.info(f"Configuration: Start={start_year}, End={end_year}, Game URL template={url_template}, Output={output_path}")

        # 1. Parse the existing dataset
        dataset_exists = os.path.exists(output_path)
        lines_to_keep = []
        last_completed_day = 0
        last_completed_year = start_year - 1

        if dataset_exists:
            try:
                lines_to_keep, last_completed_day, last_completed_year = parse_existing_dataset(output_path)
                logger.info(f"Existing dataset parsed. Last completed Day {last_completed_day} in year {last_completed_year}")
            except IOError as e:
                logger.error(f"Failed to read existing dataset: {e}")
                sys.exit(1)
        else:
            logger.info(f"Target dataset file {output_path} does not exist. A new file will be created.")

        # 2. Fetch and parse results in parallel using ThreadPoolExecutor
        all_new_draws = []
        failed_urls = []
        skipped_duplicates = 0
        total_validation_failures = 0
        years_processed = []
        detected_schema = {"num_main_balls": 5, "num_power_balls": 1}

        logger.info(f"Initiating concurrent scrape for years {start_year} to {end_year}...")
        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = {
                executor.submit(fetch_and_parse_year, year, url_template): year
                for year in range(start_year, end_year + 1)
            }
            
            for future in as_completed(futures):
                year = futures[future]
                try:
                    yr, year_draws, schema, val_fails, err_url = future.result()
                    if err_url:
                        failed_urls.append(err_url)
                    else:
                        all_new_draws.extend(year_draws)
                        total_validation_failures += val_fails
                        years_processed.append(yr)
                        detected_schema = schema
                except Exception as exc:
                    logger.error(f"Thread execution error for year {year}: {exc}")
                    failed_urls.append(url_template.format(year=year))

        # Sort years processed
        years_processed.sort()
        # Sort the entire scraped list chronologically
        all_new_draws.sort(key=lambda x: x[0])

        # 3. Dynamic Cutoff Determination by matching the last completed draw numbers
        cutoff_date = None
        if lines_to_keep:
            last_item = lines_to_keep[-1]
            last_main_balls = None
            last_powerball = None
            
            if isinstance(last_item, dict):
                last_main_balls = last_item.get("main_balls")
                last_powerball = last_item.get("powerball")
            else:
                last_main_balls, last_powerball = get_last_completed_draw_balls(last_item)
                
            if last_main_balls and last_powerball is not None:
                logger.info(f"Searching for match of last completed draw: {last_main_balls} [{last_powerball}]")
                for i, (draw_date, main_balls, powerball) in enumerate(all_new_draws):
                    if main_balls == last_main_balls and powerball == last_powerball:
                        cutoff_date = draw_date
                        logger.info(f"Match found! Cutoff date set to {cutoff_date}")
                        break
                if not cutoff_date:
                    logger.warning("Could not find a match for the last completed draw numbers in the scraped results. No entries will be skipped.")

        # Filter out duplicates (on or before cutoff date)
        unique_draws = []
        seen_dates = set()
        for item in all_new_draws:
            d_date = item[0]
            if cutoff_date and d_date <= cutoff_date:
                skipped_duplicates += 1
                continue
            if d_date in seen_dates:
                logger.warning(f"Duplicate date detected in scraped results: {d_date}. Skipping.")
                skipped_duplicates += 1
                continue
            seen_dates.add(d_date)
            unique_draws.append(item)
            
        logger.info(f"Total new draws to append after validation and duplication checks: {len(unique_draws)}")
        
        # 4. Create a backup of the existing file if it exists
        if dataset_exists and output_path:
            backup_path = output_path + ".bak"
            try:
                logger.info(f"Creating backup of {output_path} at {backup_path}")
                shutil.copy2(output_path, backup_path)
            except IOError as e:
                logger.error(f"Failed to create backup file: {e}. Aborting write.")
                sys.exit(1)
            
        # 5. Append the results to the dataset file
        appended_count = 0
        if unique_draws and output_path:
            try:
                out_dir = os.path.dirname(output_path)
                if out_dir:
                    os.makedirs(out_dir, exist_ok=True)
                    
                appended_count = append_new_results(
                    output_path,
                    unique_draws,
                    last_completed_day,
                    last_completed_year,
                    lines_to_keep
                )
                logger.info(f"Successfully appended {appended_count} records to {output_path}")
            except IOError as e:
                logger.error(f"Failed to write results to dataset: {e}.")
                if dataset_exists and backup_path:
                    logger.info("Restoring backup...")
                    try:
                        shutil.copy2(backup_path, output_path)
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
        print(f"Output File: {output_path}")
        print(f"Years processed: {years_processed}")
        print(f"Number of records added: {appended_count}")
        print(f"Number of duplicates skipped: {skipped_duplicates}")
        print(f"Number of validation failures: {total_validation_failures}")
        if failed_urls:
            print(f"Failed URLs: {failed_urls}")
        else:
            print("Failed URLs: None")
        print("="*40 + "\n")
    except KeyboardInterrupt:
        logger.info("Extraction process interrupted by user. Cleaning up and exiting gracefully.")
        if backup_path and os.path.exists(backup_path) and output_path:
            logger.info("Restoring backup dataset...")
            try:
                shutil.copy2(backup_path, output_path)
                logger.info("Backup successfully restored.")
            except Exception as e:
                logger.error(f"Failed to restore backup during shutdown cleanup: {e}")
        sys.exit(0)

if __name__ == "__main__":
    main()
