# ArcStractor User Guide

Welcome to the **ArcStractor** User Guide! This document is designed for average users who want to run the PowerBall and Lotto extraction tool to collect and update South African lottery draws. No coding experience is required—we will take you through the entire flow step-by-step.

---

## Table of Contents
1. [What is ArcStractor?](#1-what-is-arcstractor)
2. [Prerequisites](#2-prerequisites)
3. [Installation](#3-installation)
4. [Running the Tool](#4-running-the-tool)
5. [Docker Execution (Zero-Setup)](#5-docker-execution-zero-setup)
6. [Supported Output Formats](#6-supported-output-formats)
7. [Verifying Your Data](#7-verifying-your-data)
8. [Understanding Backups and Logs](#8-understanding-backups-and-logs)

---

## 1. What is ArcStractor?
ArcStractor is a simple command-line tool that fetches historical South African National Lottery results from the web (PowerBall, PowerBall Xtra, and Lotto archives), validates that the results are correct, and saves them into a file. 

If the target file already contains data, the tool is smart enough to start exactly where the existing data stops without introducing duplicate draws.

---

## 2. Prerequisites

Before using the tool, you need to have **Python** installed on your computer. (If you prefer to run it using **Docker**, you only need Docker installed; see the Docker section below).

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

Once Python is installed, download this project folder. Next, install required helper libraries:

Open your terminal, navigate to this project folder, and run:

```bash
pip install -r requirements.txt
```

This will automatically download and install:
- **`requests`**: Used to fetch the archive webpages.
- **`beautifulsoup4`**: Used to read and extract results tables.

---

## 4. Running the Tool

You run the tool using command-line commands. Navigate your terminal to the project root directory.

### Option A: Interactive CLI Wizard (Easiest)
If you run the script with **no arguments** in an interactive terminal, ArcStractor will launch a configuration wizard that walks you through setting up your extraction (choosing the game, starting/ending years, and output path):

```bash
python src/main.py
```

Follow the prompts on your screen and press `Enter` to accept defaults. The wizard supports:
1. **PowerBall** (Default)
2. **PowerBall Xtra**
3. **Lotto**

### Option B: Direct Command Line (Advanced)
If you want to bypass the prompt wizard and run it directly with custom flags, append options like so:

**For Standard PowerBall**:
```bash
python src/main.py --game powerball --start-year 2010 --end-year 2026 --output data/dataset_2.txt
```

**For PowerBall Xtra**:
```bash
python src/main.py --game powerball-xtra --start-year 2015 --end-year 2026 --output data/dataset_xtra.csv
```

**For Standard Lotto**:
```bash
python src/main.py --game lotto --start-year 2010 --end-year 2026 --output data/dataset_lotto.txt
```

**Command Options Reference**:
- `--start-year` (or `-s`): The first year to retrieve (e.g., `2018`).
- `--end-year` (or `-e`): The last year to retrieve (e.g., `2026`).
- `--game` (or `-g`): Choose between `powerball`, `powerball-xtra`, or `lotto`.
- `--output` (or `-o`): The path where the file will be saved. The extension of this file (`.txt`, `.csv`, `.json`, `.db`, `.sqlite`) determines its output format!

---

## 5. Docker Execution (Zero-Setup)

If you have **Docker** and **Docker Compose** installed on your system, you can execute the tool without installing Python or any libraries locally.

### 1. Build the Container
Navigate to the project directory and run:
```bash
docker-compose build
```

### 2. Run the Interactive Wizard in Docker
To launch the interactive configuration prompt inside the container:
```bash
docker-compose run extractor
```

### 3. Run with Arguments in Docker (Lotto example)
To run direct commands through Docker:
```bash
docker-compose run extractor --game lotto --start-year 2010 --end-year 2026 --output data/dataset_lotto.txt
```

All datasets generated inside Docker are saved directly to your local computer's `data/` folder (and caching is preserved inside `.cache/`) because volumes are mapped automatically.

---

## 6. Supported Output Formats

ArcStractor automatically determines how to read and write your data based on your file path extension:

- **Custom Text (`.txt`)**: Stores draws in the format `Day X - [N1,N2,N3,N4,N5,[PB]]` (or `[N1,N2,N3,N4,N5,N6,[Bonus]]` for Lotto) grouped under yearly headers.
- **CSV (`.csv`)**: Stores draws in spreadsheet layout with columns: `day,date,ball_1,ball_2,ball_3,ball_4,ball_5,powerball` (automatically adds `ball_6` if Lotto is detected).
- **JSON (`.json`)**: Stores draws as an array of JSON objects containing keys for `day`, `date`, `main_balls`, and `powerball`.
- **SQLite Database (`.db` or `.sqlite`)**: Stores draws inside a SQL table named `draw_results`, making it ready for database querying.

---

## 7. Verifying Your Data

To verify that your dataset file was written correctly, is formatted properly, and has no missing sequences or duplicate numbers, you can run the validation script.

Run the script by typing:
```bash
python src/verify.py
```
*(By default, this checks the main `data/dataset_2.txt` file).*

If you want to verify a custom output file instead (like `data/dataset_lotto.txt` or `data/dataset_xtra.csv`), type:
```bash
python src/verify.py data/dataset_lotto.txt
```

If everything is healthy, you will see this success message:
```text
[PASS] Dataset is healthy, structured correctly, and chronologically complete!
```

---

## 8. Cleaning & Preparing Data (ML Feature Engineering)

If you want to prepare your lottery datasets for downstream machine learning (ML), data analysis, or statistical modeling, run the automated preparation pipeline script:

```bash
python src/prepare.py
```

### What this script does:
1. **Auto-discovers raw files**: Scans `data/` for text datasets (`dataset_2.txt`, `dataset_lotto.txt`, `dataset_xtra.txt`).
2. **Reconstructs draw dates**: Aligns day numbers with official historical draw dates (using the local HTML cache).
3. **Validates & Checks for Gaps**: Confirms chronological chronology, checks for sequence gaps, and checks for missing draws (such as public holidays like Christmas Day or Good Friday when draws are not held).
4. **Engineers Statistical/ML Features**: Automatically generates:
   - Calendar features: `year`, `month`, `day_of_month`, `day_of_week` (0-6), `is_weekend` (0 or 1).
   - Draw metrics: `sum_main_balls`, `mean_main_balls`, `min_main_ball`, `max_main_ball`, `range_main_balls` (max - min).
   - Parity metrics: `odd_count`, `even_count`, and `is_powerball_even` (0 or 1).
5. **Exports Structured Formats**: Saves the cleaned, feature-enriched data to a new `data/cleaned/` directory:
   - **CSV** (e.g. `data/cleaned/powerball_clean.csv`) - ready for analysis in Pandas or Excel.
   - **JSON** (e.g. `data/cleaned/powerball_clean.json`) - ready for JavaScript/Web platforms.
   - **SQLite** (e.g. `data/cleaned/powerball_clean.db`) - database file ready for SQL queries.

---

## 9. Interactive Streamlit Web Dashboard

If you prefer a graphical user interface to explore historical statistics and live mathematical tests, launch the Streamlit web dashboard:

```bash
streamlit run src/app.py
```

### Dashboard Features:
1. **Interactive Timeline Range**: Slide the year bounds in the sidebar to dynamically filter statistics over customized eras.
2. **Number Frequency & Highlights**: View hot and cold numbers instantly, with expectation bounds plotted.
3. **Live Mathematical Tests**: Recalculates Chi-Square Uniformity and Wald-Wolfowitz runs tests dynamically over your selected subset, displaying red/green status indicator cards.
4. **Odd/Even Binomial Projections**: Renders bar charts comparing actual odd/even draw splits against theoretical binomial expectations.
5. **Draw History Query Table**: Search or filter past draw values or specific dates inside an interactive datatable.

---

## 10. Understanding Backups and Logs

ArcStractor has safety measures built in so you don't lose your data:

- **Automatic Backups**: Whenever you update an existing file, the tool automatically makes a copy of the old file and saves it with a `.bak` extension (e.g., `data/dataset_2.txt.bak`). If something goes wrong during the scrape, it restores the backup automatically.
- **Extraction Logs**: All details of the scraper execution—such as validation warnings, URLs scraped, and entries skipped—are saved to a file named `extraction.log` in the project folder. Open this file in any text editor if you want to inspect what the tool did.
- **Preparation Logs**: Execution logs for the preparation script are stored in `preparation.log`.

