from datetime import datetime, timezone
from urllib.parse import urlparse, urlencode, urlunparse, parse_qs
import sys
import time


def load_text_file(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()
    
def save2txt(filename, content):
    with open(filename, "w", encoding="utf-8") as f:
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
