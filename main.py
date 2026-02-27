import json
from geopy.geocoders import Nominatim
import requests
from datetime import datetime, timezone
from bs4 import BeautifulSoup
import os
import re

headers = {"User-Agent": "Mozilla/5.0"}

PARAM_FILE = "param.txt"
url = "https://api.adzuna.com/v1/api/jobs/au/search/"



def load_api_param():
    if not os.path.exists(PARAM_FILE): 
        raise FileNotFoundError(f"Parameter file '{PARAM_FILE}' not found. Please create the file with your app_id and app_key.")
    else:
        with open(PARAM_FILE, "r") as f:  lines = f.readlines()
        app_id = lines[0].strip() if len(lines) > 0 else ""
        app_key = lines[1].strip() if len(lines) > 1 else ""

    return app_id, app_key

def days_to_today(time_str):
    created_time = datetime.strptime(time_str, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)

    delta = now - created_time
    return delta.days

def parse_date(time_str):
    created_time = datetime.strptime(time_str, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    return created_time.strftime("%d/%m/%Y")

def remove_corporate_fluff(section):    # Find header
    culture_header = section.find(
        ["strong", "b"],
        string=lambda x: x and "culture" in x.lower()
    )

    if culture_header:
        # Remove everything after this header
        for tag in culture_header.find_all_next():
            tag.decompose()

        culture_header.decompose()

    return section

FLUFF_KEYWORDS = [
    "equal opportunity",
    "diversity",
    "inclusive",
    "apply anyway",
    "circle back",
    "benefits",
    "wellbeing",
    "parental leave",
    "our values",
    "personal data"
]

def remove_fluff_paragraphs(section):
    for p in section.find_all("p"):
        text = p.get_text().lower()
        if any(keyword in text for keyword in FLUFF_KEYWORDS):
            p.decompose()

    return section

def contains_keywords(text, keywords):
    if not text:
        return False

    text_lower = text.lower()
    return any(keyword.lower() in text_lower for keyword in keywords)

SKILL_KEYWORDS = ["requirement", "certification", "tech stack", "skill", "responsibilities", "nice to have", "must have"]



WORD_NUM_PATTERN = r"(one|two|three|four|five|six|seven|eight|nine|ten)"
DIGIT_PATTERN = r"\d+"

NUMBER_PATTERN = rf"(?:{DIGIT_PATTERN}|{WORD_NUM_PATTERN})"

RANGE_PATTERN = rf"""
(?P<min>{NUMBER_PATTERN})
\s*
(?:-|–|to)
\s*
(?P<max>{NUMBER_PATTERN})
\+?
"""

SINGLE_PATTERN = rf"""
(?P<single>{NUMBER_PATTERN})
\+?
"""

EXPERIENCE_PATTERN = rf"""
(
    (?:
        {RANGE_PATTERN}
        |
        {SINGLE_PATTERN}
    )
    \s+years?
    (?:\s+of)?
    (?:\s+\w+){{0,5}}?
    \s+experience
)
"""

WORD_TO_NUM = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10
}

def extract_experience(text):
    results = []

    for match in re.finditer(EXPERIENCE_PATTERN, text, re.IGNORECASE | re.VERBOSE):

        min_val = match.group("min")
        max_val = match.group("max")
        single_val = match.group("single")

        def convert(value):
            if not value:
                return None
            value = value.lower()
            if value.isdigit():
                return int(value)
            return WORD_TO_NUM.get(value)

        if min_val and max_val:
            results.append({
                "phrase": match.group(0),
                "min_years": convert(min_val),
                "max_years": convert(max_val),
                "type": "range"
            })
        else:
            results.append({
                "phrase": match.group(0),
                "min_years": convert(single_val),
                "max_years": None,
                "type": "single"
            })

    return results






if __name__ == "__main__":

    app_id, app_key = load_api_param()

    params = {
        "app_id": app_id,
        "app_key": app_key,
        "what": "developer",
        "where": "melbourne",
        "results_per_page": 10,
        "distance": 25
    }

    page_num = 0

    

    geolocator = Nominatim(user_agent="geoapi")
    now = datetime.now(timezone.utc)

    counter = 0

    # implement make it track current page, total page and auto proceed to next page
    
    while True:

        page_num += 1

        response = requests.get(url + str(page_num), params=params)
        data = response.json()
        
        
        for job in data["results"]: # each page shows 10 results

            counter += 1

            if job['category']['label'] != "IT Jobs": continue

            print(f"Found {counter}/{data['count']} job listings (Page {page_num}) for '{params['what']}' in '{params['where']}' within {params['distance']}km radius:\n")
            #print(json.dumps(job, indent=4))
            contract_time = job.get('contract_time') or "N/A"
            days_ago = f"{days_to_today(job['created'])} days ago" if days_to_today(job['created']) > 0 else "Today"

            job_url = job['redirect_url'].split("?", 1)[0]

            page = requests.get(job_url, headers=headers)
            soup = BeautifulSoup(page.text, "html.parser")

            description = soup.select_one("section.adp-body")
            # description.get_text() for no html tags

            ## reducing token to LLM, if trigger basic keyword requirment, pass
            # non-desicion making description filter, might not work if the description is a blob on words.
            description = remove_corporate_fluff(description)
            description = remove_fluff_paragraphs(description)
            cleaned_text = description.get_text(separator="\n", strip=True)
            # basic filtering for "X years experience", certification requirement, specific tech stack requirement, etc.

            print(f"● {job['title']} ({contract_time}) - {job['company']['display_name']} @{job['location']['display_name']} - {parse_date(job['created'])} ({days_ago})")
            print(f"  - Category: {job['category']['label']} - {job_url} ID: {job['id']}")
            print(f"  - Filtered Description: {cleaned_text if cleaned_text else 'N/A'}")

            if not contains_keywords(cleaned_text, SKILL_KEYWORDS):
                print("\n⚠  Description may lack clear requirements or tech stack.")

            print(extract_experience(cleaned_text))

            input("\nPress Enter to continue to the next job listing...\n")

            os.system('cls' if os.name == 'nt' else 'clear')
        
            
            # reducing token text pass to Local LLM
            # domain, responsibilities, tech_stack, other
    
