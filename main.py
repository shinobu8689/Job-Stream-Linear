import json
from geopy.geocoders import Nominatim
import requests
from datetime import datetime, timezone
from bs4 import BeautifulSoup
import os

headers = {"User-Agent": "Mozilla/5.0"}

PARAM_FILE = "param.txt"

def load_api_param():
    if not os.path.exists(PARAM_FILE): 
        raise FileNotFoundError(f"Parameter file '{PARAM_FILE}' not found. Please create the file with your app_id and app_key.")
    else:
        with open(PARAM_FILE, "r") as f:  lines = f.readlines()
        app_id = lines[0].strip() if len(lines) > 0 else ""
        app_key = lines[1].strip() if len(lines) > 1 else ""

    return app_id, app_key


url = "https://api.adzuna.com/v1/api/jobs/au/search/1"


def days_to_today(time_str):
    created_time = datetime.strptime(time_str, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)

    delta = now - created_time
    return delta.days

def parse_date(time_str):
    created_time = datetime.strptime(time_str, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    return created_time.strftime("%d/%m/%Y")



if __name__ == "__main__":

    app_id, app_key = load_api_param()

    params = {
        "app_id": app_id,
        "app_key": app_key,
        "what": "developer",
        "where": "melbourne",
        "results_per_page": 3,
        "distance": 25
    }

    response = requests.get(url, params=params)
    data = response.json()

    geolocator = Nominatim(user_agent="geoapi")
    now = datetime.now(timezone.utc)

    print(f"\n")


    for job in data["results"]: # each page shows 10 results
        # print(json.dumps(job, indent=4))
        contract_time = job.get('contract_time') or "N/A"
        days_ago = f"{days_to_today(job['created'])} days ago" if days_to_today(job['created']) > 0 else "Today"

        job_url = job['redirect_url'].split("?", 1)[0]

        page = requests.get(job_url, headers=headers)
        soup = BeautifulSoup(page.text, "html.parser")

        description = soup.select_one("section.adp-body")

        print(f"● {job['title']} ({contract_time}) - {job['company']['display_name']} @{job['location']['display_name']} - {parse_date(job['created'])} ({days_ago})")
        print(f"  - Category: {job['category']['label']} - {job_url}")
        print(f"  - Description: {description.get_text() if description else 'N/A'}")
        print(f"\n")

        # seperate marketing stuff in description, e.g. "About the company", "What you will do", "What we are looking for", "Benefits"
        # reducing token required and pass it to Local LLM
        # domain, responsibilities, tech_stack, other
    
