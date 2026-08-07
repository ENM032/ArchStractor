# ArcStractor User Guide

Welcome to the **ArcStractor** User Guide! This document is designed for average users who want to run the PowerBall extraction tool to collect and update South African lottery draws. No coding experience is required—we will take you through the entire flow step-by-step.

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
ArcStractor is a simple command-line tool that fetches historical South African National Lottery results from the web (specifically PowerBall and PowerBall Xtra archives), validates that the results are correct, and saves them into a file. 

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

Follow the prompts on your screen and press `Enter` to accept defaults.

### Option B: Direct Command Line (Advanced)
If you want to bypass the prompt wizard and run it directly with custom flags, append options like so:

```bash
python src/main.py --game powerball-xtra --start-year 2015 --end-year 2026 --output data/dataset_xtra.csv
```

**Command Options Reference**:
- `--start-year` (or `-s`): The first year to retrieve (e.g., `2018`).
- `--end-year` (or `-e`): The last year to retrieve (e.g., `2026`).
- `--game` (or `-g`): Choose between `powerball` or `powerball-xtra`.
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

### 3. Run with Arguments in Docker
To run direct commands through Docker:
```bash
docker-compose run extractor --game powerball-xtra --start-year 2015 --end-year 2026 --output data/dataset_xtra.csv
```

All datasets generated inside Docker are saved directly to your local computer's `data/` folder (and caching is preserved inside `.cache/`) because volumes are mapped automatically.

---

## 6. Supported Output Formats

ArcStractor automatically determines how to read and write your data based on your file path extension:

- **Custom Text (`.txt`)**: Stores draws in the format `Day X - [N1,N2,N3,N4,N5,[PB]]` grouped under yearly headers.
- **CSV (`.csv`)**: Stores draws in spreadsheet layout with columns: `day,date,ball_1,ball_2,ball_3,ball_4,ball_5,powerball`.
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

If you want to verify a custom output file instead (like `data/dataset_xtra.csv` or `data/dataset_xtra.db`), type:
```bash
python src/verify.py data/dataset_xtra.csv
```

If everything is healthy, you will see this success message:
```text
[PASS] Dataset is healthy, structured correctly, and chronologically complete!
```

---

## 8. Understanding Backups and Logs

ArcStractor has safety measures built in so you don't lose your data:

- **Automatic Backups**: Whenever you update an existing file, the tool automatically makes a copy of the old file and saves it with a `.bak` extension (e.g., `data/dataset_2.txt.bak`). If something goes wrong during the scrape, it restores the backup automatically.
- **Extraction Logs**: All details of the scraper execution—such as validation warnings, URLs scraped, and entries skipped—are saved to a file named `extraction.log` in the project folder. Open this file in any text editor if you want to inspect what the tool did.
