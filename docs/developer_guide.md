# ArcStractor Developer Guide

This document is intended for developers who wish to understand the inner workings, system architecture, logic, and processes of the **ArcStractor** dataset extractor and builder.

---

## 1. System Architecture & Component Diagram

The project is structured as a collection of modular Python scripts under `src/`. Below is a Mermaid sequence showing how components interact during a standard execution flow:

```mermaid
sequenceDiagram
    participant User/CLI
    participant Main as main.py
    participant Formatter as formatter.py
    participant Scraper as scraper.py
    participant Parser as parser.py
    participant Validator as validator.py

    User/CLI->>Main: Execute with arguments
    Main->>Formatter: parse_existing_dataset(output_path)
    Formatter-->>Main: Return (existing_data, last_completed_day, last_completed_year)
    
    loop For each year in range
        Main->>Scraper: fetch_page(year_url)
        Scraper-->>Main: Return HTML content
        Main->>Parser: parse_html_page(html)
        Parser-->>Main: Return (draws, detected_schema)
    end
    
    Main->>Main: Sort scraped draws chronologically
    
    loop Validate each scraped draw
        Main->>Validator: validate_draw_data(date, main, pb, schema_main, schema_pb)
        Validator-->>Main: Return (is_valid, error_message)
    end
    
    Main->>Main: Perform Dynamic Cutoff Match (locate last completed draw's numbers)
    Main->>Main: Create backup dataset file (.bak)
    
    Main->>Formatter: append_new_results(output_path, new_draws, ...)
    Formatter-->>Main: Write file (TXT/CSV/JSON/SQLite), return appended_count
    Main->>User/CLI: Print execution summary
```

---

## 2. Module Specifications

### `src/scraper.py`
- **Purpose**: Fetches raw HTML pages from the target South African National Lottery results archive.
- **Key Features**:
  - Implements customized request headers containing a generic browser `User-Agent` to avoid anti-scraping blocks.
  - Implements connection timeout handling (15 seconds).
  - Supports automated single retry logic: if a request fails or returns a non-200 HTTP code, it waits 2 seconds and attempts retrieval once more before raising an exception.
  - **Local HTML Caching**: Saves parsed HTML files to a local `.cache/` folder for all historical years (`year < current_year`). On subsequent runs, it loads from cache instead of hitting the network. The current year is always fetched live.

### `src/parser.py`
- **Purpose**: Extracts draw elements (Dates, Main numbers, and PowerBall numbers) and detects game schemas.
- **Key Features**:
  - Employs `BeautifulSoup` to parse HTML. It matches the results table using a flexible selector that targets classes like `powerball`, `powerball-plus`, `powerball-xtra`, or `mobResult`. If all else fails, it targets the first table.
  - Utilizes a robust date extractor (`parse_date`) that attempts to regex-match the `{day}-{month}-{year}` pattern inside the row's `href` URL structure first. If missing, it falls back to parsing string structures in the date cell, splitting out weekdays and month names safely.
  - **Dynamic Schema Detection**: Parses list item classes inside `ul.balls` to identify bonus/powerball indicators (e.g. classes containing `powerball`, `bonus`, `bonusball`, `supp`) vs. normal numbers. It returns the detected schema (number of main balls, number of powerballs) on-the-fly, avoiding hardcoding the number layout.

### `src/validator.py`
- **Purpose**: The central gatekeeper enforcing data formatting and mathematical constraints for draw results.
- **Enforced Rules**:
  - **Date Validation**: The draw date must exist and must not be in the future (greater than the machine's local date).
  - **Ball Counts**: Each draw must contain exactly the expected count of main and PowerBall numbers as declared by the page's schema.
  - **Numerical Ranges**: Main numbers must fall within the range `[1, 50]`. The PowerBall must fall within the range `[1, 20]`.
  - **Uniqueness Check**: The main numbers list must contain no duplicate values.

### `src/formatter.py`
- **Purpose**: Multi-format handler reading and writing files according to their file extension.
- **Supported Formats**:
  - **Custom Text (`.txt`)**: Stores data in `Day X - [N1,N2,N3,N4,N5,[PB]]` with `=== YEAR ===` rollover headers.
  - **CSV (`.csv`)**: Reads and writes standard CSV layout dynamically based on the schema (e.g. `day,date,ball_1,ball_2,ball_3,ball_4,ball_5,powerball`).
  - **JSON (`.json`)**: Reads and writes standard formatted JSON arrays of objects containing `day`, `date`, `main_balls`, and `powerball` keys.
  - **SQLite Database (`.db` / `.sqlite`)**: Manages local database tables inside SQLite. Creates/appends rows inside the `draw_results` table.
- **Line Ending Preservation**: Detects line endings (`\r\n` vs `\n`) for TXT/CSV files to prevent encoding corruption.

### `src/main.py`
- **Purpose**: The main orchestration script. It parses terminal options, manages safety backups, computes cutoff offsets, and manages logs.
- **Dynamic Cutoff Logic**:
  Instead of hardcoding a date threshold, `main.py` parses the ball values of the very last completed entry in the target file (supports both string extraction for TXT, and dictionary inspection for CSV/JSON/SQLite). It then runs a chronological search through the newly scraped entries. Once it finds an entry with identical ball values, it sets that date as the `cutoff_date`. All scraped draws on or before this date are safely ignored.
- **Atomic File Backups**:
  Before calling the write module, `main.py` copies the target file to `{filename}.bak`. If the write fails due to disk operations (`IOError`), it attempts to restore the backup file, preventing data corruption.

### `src/verify.py`
- **Purpose**: An offline verification script to test dataset integrity.
- **Key Features**:
  - **Auto-Format Detection**: Checks file extension to choose either raw line parsing (for TXT files) or structured record verification (for CSV, JSON, and SQLite).
  - **Sequence Validation**: Confirms that day indexes are strictly sequential (incrementing by 1), year timelines are ascending, and calls the central `validator.py` constraints on each draw.

---

## 3. Customizing or Extending the Tool

### Adding a Game Preset
To add a new preset game shortcut (like standard `lotto`):
1. In `src/main.py`, update `choices` in the `argparse` configuration:
   ```python
   parser.add_argument("--game", "-g", choices=["powerball", "powerball-xtra", "lotto"])
   ```
2. Map the game to its national-lottery URL template in the template resolution block:
   ```python
   if game == "lotto":
       url_template = "https://za.national-lottery.com/lotto/results/{year}-archive"
   ```
3. The parser will automatically adapt to standard Lotto's schema (`6 main, 1 bonusball`) on-the-fly due to the dynamic schema detector!
