# SA PowerBall Results Extractor & Dataset Builder

This utility crawls the South African National Lottery archive pages for PowerBall draw results from 2010 through 2026, validates them, and appends them to a formatted dataset file.

## Project Structure

The project code is modularized inside the `src/` directory:
- **`src/scraper.py`**: Handles network requests, custom headers, and retries.
- **`src/parser.py`**: Extracts raw draw dates, main numbers, and PowerBall numbers from webpage tables.
- **`src/validator.py`**: central validation logic checking date ranges, ball counts (5 main, 1 PowerBall), duplicate numbers inside a draw, and valid numerical ranges.
- **`src/formatter.py`**: Manages reading, detecting line-endings, and formatting dataset rows chronologically under correct year headers.
- **`src/main.py`**: The main execution script. Creates a safety backup of the dataset before modification, and features rollback mechanisms.
- **`src/verify.py`**: Checks the dataset file (`data/dataset_2.txt`) to ensure sequence numbers, brackets, year order, and draw data are completely healthy and valid.

## Setup

Ensure you have Python 3.8+ installed. Install the required dependencies:

```bash
pip install requests beautifulsoup4
```

## Usage

### Run Extraction
To scrape the archive pages, validate findings, and append new results to the dataset:
```bash
python src/main.py
```
This runs the full extraction process, prints a summary, creates a backup file (`data/dataset_2.txt.bak`), and logs the actions to `extraction.log`.

### Verify Dataset
To run verification checks on the output dataset (`data/dataset_2.txt`):
```bash
python src/verify.py
```
This will parse the file and output whether it passes sequential day indexing, formatting style, and data validation rules.
