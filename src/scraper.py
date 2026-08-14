import time
import logging
import requests
import os
import re
from datetime import date
from typing import Optional
try:
    from config import MAX_PAGE_SIZE
except ModuleNotFoundError:
    from src.config import MAX_PAGE_SIZE

logger = logging.getLogger(__name__)

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

CACHE_DIR = ".cache"

def get_cache_path(url: str) -> Optional[str]:
    """
    Extracts game and year from URL to construct a cache file path.
    Example: https://za.national-lottery.com/powerball/results/2010-archive
             -> .cache/powerball_2010.html
    """
    # Extract game name
    game_match = re.search(r"national-lottery\.com/([^/]+)/results", url)
    # Extract year
    year_match = re.search(r"results/(\d{4})-archive", url)
    
    if game_match and year_match:
        game = game_match.group(1)
        year = int(year_match.group(1))
        
        # Only cache historical years. Do not cache current or future years.
        current_year = date.today().year
        if year < current_year:
            os.makedirs(CACHE_DIR, exist_ok=True)
            return os.path.join(CACHE_DIR, f"{game}_{year}.html")
            
    return None

def fetch_page(url: str, retries: int = 1, timeout: int = 15) -> str:
    """
    Fetches the HTML content of the given URL.
    Checks and loads from local cache if applicable.
    Retries once if network retrieval fails.
    """
    # 1. Check local cache first
    cache_path = get_cache_path(url)
    if cache_path and os.path.exists(cache_path):
        try:
            logger.info(f"Cache hit for URL: {url} -> Loading from {cache_path}")
            with open(cache_path, "r", encoding="utf-8") as f:
                return f.read()
        except IOError as e:
            logger.warning(f"Failed to read cache file {cache_path}: {e}. Falling back to web fetch.")

    # 2. Fetch from web with retry logic
    for attempt in range(retries + 1):
        try:
            logger.info(f"Fetching URL: {url} (Attempt {attempt + 1}/{retries + 1})")
            response = requests.get(url, headers=DEFAULT_HEADERS, timeout=timeout, verify=True, stream=True)
            if response.status_code == 200:
                html_bytes = b""
                for chunk in response.iter_content(chunk_size=1024 * 64):
                    html_bytes += chunk
                    if len(html_bytes) > MAX_PAGE_SIZE:
                        raise ValueError(f"Fetched page size from {url} exceeds safety limit of {MAX_PAGE_SIZE} bytes")
                
                html_content = html_bytes.decode("utf-8", errors="ignore")
                
                # Write to cache if applicable
                if cache_path:
                    try:
                        logger.info(f"Writing fetched content to cache: {cache_path}")
                        with open(cache_path, "w", encoding="utf-8") as f:
                            f.write(html_content)
                    except IOError as cache_err:
                        logger.warning(f"Failed to write cache file {cache_path}: {cache_err}")
                        
                return html_content
            else:
                logger.warning(f"Failed to fetch {url}. Status code: {response.status_code}")
        except requests.RequestException as e:
            logger.warning(f"Error fetching {url}: {e}")
        except ValueError as val_err:
            logger.error(f"Payload limit error for URL {url}: {val_err}")
            raise val_err
        
        if attempt < retries:
            time.sleep(2)  # Delay before retry
            
    raise Exception(f"Failed to retrieve page content from {url} after {retries + 1} attempts")
