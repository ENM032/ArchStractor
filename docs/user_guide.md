# ArcStractor User Guide

Welcome to the **ArcStractor** User Guide! This document is designed for average users who want to run the PowerBall extraction tool to collect and update South African lottery draws. No coding experience is required—we will take you through the entire flow step-by-step.

---

## Table of Contents
1. [What is ArcStractor?](#1-what-is-arcstractor)
2. [Prerequisites](#2-prerequisites)
3. [Installation](#3-installation)
4. [Running the Tool](#4-running-the-tool)
5. [Supported Output Formats](#5-supported-output-formats)
6. [Verifying Your Data](#6-verifying-your-data)
7. [Understanding Backups and Logs](#7-understanding-backups-and-logs)

---

## 1. What is ArcStractor?
ArcStractor is a simple command-line tool that fetches historical South African National Lottery results from the web (specifically PowerBall and PowerBall Xtra archives), validates that the results are correct, and saves them into a file. 

If the target file already contains data, the tool is smart enough to start exactly where the existing data stops without introducing duplicate draws.

---

## 2. Prerequisites

Before using the tool, you need to have **Python** installed on your computer.

### Installing Python
1. **Download**: Visit [python.org/downloads](https://www.python.org/downloads/) and download the installer for your operating system (Windows, macOS, or Linux).
2. **Install**: Run the installer. 
   > [!IMPORTANT]
   > On Windows, make sure to check the box that says **"Add Python to PATH"** before clicking Install. This allows you to run Python from the command prompt.
3. **Verify**: Open your terminal (Command Prompt or PowerShell on Windows, Terminal on macOS/Linux) and type:
   ```bash
   python --version
   ```
   You should see a message like `Python 3.x.x` printed out.

---

## 3. Installation

Once Python is installed, download this project folder. Next, we need to install two helper packages (called "libraries") that help Python fetch web pages and parse them.

Open your terminal, navigate to this project folder, and run:

```bash
pip install requests beautifulsoup4
```

This will automatically download and install:
- **`requests`**: Used to fetch the archive webpages.
- **`beautifulsoup4`**: Used to read and extract results tables from the webpage's code.

---

## 4. Running the Tool

You run the tool using command-line commands. Navigate your terminal to the project root directory, and choose one of the options below.

### Option A: Standard Run (Original PowerBall TXT)
To run the extractor with default settings (which retrieves South African PowerBall results for years 2010 through 2026 and updates the existing `data/dataset_2.txt`):

```bash
python src/main.py
```

### Option B: Retrieve a Different Game and Format
If you want to extract a different game like **PowerBall Xtra**, starting from a specific year range (e.g. 2015 to 2026), and save it to a new file in a different format (like **CSV** or **JSON** or **SQLite database**), simply specify the appropriate file extension in the `--output` path:

**For CSV (Excel compatible)**:
```bash
python src/main.py --game powerball-xtra --start-year 2015 --end-year 2026 --output data/dataset_xtra.csv
```

**For JSON (Web/Developer compatible)**:
```bash
python src/main.py --game powerball-xtra --start-year 2015 --end-year 2026 --output data/dataset_xtra.json
```

**For SQLite Database (SQL queries compatible)**:
```bash
python src/main.py --game powerball-xtra --start-year 2015 --end-year 2026 --output data/dataset_xtra.db
```

### Command Options Reference
You can customize how the tool runs by appending "flags" to the command:
- `--start-year` (or `-s`): The first year you want to retrieve results for (e.g., `2018`).
- `--end-year` (or `-e`): The last year to retrieve (e.g., `2026`).
- `--game` (or `-g`): Choose between `powerball` or `powerball-xtra`.
- `--output` (or `-o`): The path where the file will be saved. The extension of this file (`.txt`, `.csv`, `.json`, `.db`, `.sqlite`) determines its output format!

---

## 5. Supported Output Formats

ArcStractor automatically determines how to read and write your data based on your file path extension:

- **Custom Text (`.txt`)**: Stores draws in the format `Day X - [N1,N2,N3,N4,N5,[PB]]` grouped under yearly headers.
- **CSV (`.csv`)**: Stores draws in spreadsheet layout with columns: `day,date,ball_1,ball_2,ball_3,ball_4,ball_5,powerball`.
- **JSON (`.json`)**: Stores draws as an array of JSON objects containing keys for `day`, `date`, `main_balls`, and `powerball`.
- **SQLite Database (`.db` or `.sqlite`)**: Stores draws inside a SQL table named `draw_results`, making it ready for database querying.

---

## 6. Verifying Your Data

To verify that your dataset file was written correctly, is formatted properly, and has no missing sequences or duplicate numbers, you can run the validation script.

Run the script by typing:
```bash
python src/verify.py
```
*(By default, this checks the main `data/dataset_2.txt` file).*

If you want to verify a custom output file instead (like `data/dataset_xtra.csv` or `data/dataset_xtra.db`), type:
```bash
python src/verify.py data/dataset_xtra.csv
```

If everything is healthy, you will see this success message:
```text
[PASS] Dataset is healthy, structured correctly, and chronologically complete!
```

---

## 7. Understanding Backups and Logs

ArcStractor has safety measures built in so you don't lose your data:

- **Automatic Backups**: Whenever you update an existing file, the tool automatically makes a copy of the old file and saves it with a `.bak` extension (e.g., `data/dataset_2.txt.bak`). If something goes wrong during the scrape, it restores the backup automatically.
- **Extraction Logs**: All details of the scraper execution—such as validation warnings, URLs scraped, and entries skipped—are saved to a file named `extraction.log` in the project folder. Open this file in any text editor if you want to inspect what the tool did.
