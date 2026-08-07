import time
import logging
import requests

logger = logging.getLogger(__name__)

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def fetch_page(url: str, retries: int = 1, timeout: int = 15) -> str:
    """
    Fetches the HTML content of the given URL.
    Retries once if it fails.
    """
    for attempt in range(retries + 1):
        try:
            logger.info(f"Fetching URL: {url} (Attempt {attempt + 1}/{retries + 1})")
            response = requests.get(url, headers=DEFAULT_HEADERS, timeout=timeout)
            if response.status_code == 200:
                return response.text
            else:
                logger.warning(f"Failed to fetch {url}. Status code: {response.status_code}")
        except requests.RequestException as e:
            logger.warning(f"Error fetching {url}: {e}")
        
        if attempt < retries:
            time.sleep(2)  # Short delay before retry
            
    raise Exception(f"Failed to retrieve page content from {url} after {retries + 1} attempts")
