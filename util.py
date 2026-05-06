from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse, urlencode, urlunparse, parse_qs
import sys
import time
from pathlib import Path as FilePath

# funtions for file handling, text processing, and other utilities. most self explanatory.

BASE_DIR = FilePath(__file__).resolve().parent

BASE_DIR = FilePath(__file__).resolve().parent

def load_text_file(path):
    file_path = BASE_DIR / path

    # Ensure parent directory exists (in case you later use subfolders)
    file_path.parent.mkdir(parents=True, exist_ok=True)

    # Create file if it doesn't exist
    if not file_path.exists():
        file_path.write_text("", encoding="utf-8")

    return file_path.read_text(encoding="utf-8")
    
def save2txt(filename, content):
    file_path = BASE_DIR / filename
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(str(content))

def hyperlink(label, url):
    ESC = "\033]"
    BEL = "\007"
    return f"{ESC}8;;{url}{BEL}{label}{ESC}8;;{BEL}"

def days_to_today(time_str):
    created_time = datetime.strptime(time_str, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)

    delta = now - created_time
    return delta.days

def parse_date(time_str):
    created_time = datetime.strptime(time_str, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    return created_time.strftime("%d/%m/%Y")

def contains_keywords(text, keywords):
    if not text:
        return False
    text_lower = text.lower()
    return any(keyword.lower() in text_lower for keyword in keywords)

def days_ago(x):
    now = datetime.now(timezone.utc)
    return now - timedelta(days=x)

def countdown(txt: str, seconds: int):
    CLEAR = "\033[2K"   # wipe entire line
    for i in range(seconds, -1, -1):
        sys.stdout.write(CLEAR + "\r")   # clear + return to start
        sys.stdout.write(f"{txt}proceed in {i}...")
        sys.stdout.flush()
        time.sleep(1)

def clean_url(raw_url: str) -> str:
        parsed = urlparse(raw_url)

        # Parse existing query params
        query_dict = parse_qs(parsed.query)

        # Re-encode query params safely
        encoded_query = urlencode(query_dict, doseq=True)

        # Rebuild the full URL
        return urlunparse((
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            parsed.params,
            encoded_query,
            parsed.fragment
        ))
