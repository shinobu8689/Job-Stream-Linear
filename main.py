import json
import random
from playwright.sync_api import sync_playwright
import requests
from datetime import datetime, timezone
from bs4 import BeautifulSoup
import os
import re
import time
from pathlib import Path
from jobObj import JobPosting
import llm
import util

headers = {"User-Agent": "Mozilla/5.0"}

url = "https://api.adzuna.com/v1/api/jobs/au/search/"

def load_api_param():
    if not os.path.exists("param.txt"): 
        raise FileNotFoundError(f"Parameter file '{"param.txt"}' not found. Please create the file with your app_id and app_key.")
    else:
        with open("param.txt", "r") as f:  lines = f.readlines()
        app_id = lines[0].strip() if len(lines) > 0 else ""
        app_key = lines[1].strip() if len(lines) > 1 else ""

    return app_id, app_key

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

SECTION_CUTOFF_HEADERS = [
    "culture",
    "about us",
    "our values",
    "why join",
    "life at",
    "diversity",
    "who we are"
]

def clean_section(section):
    # non-desicion making description filter, might not work if the description is a blob on words.

    # --- 1. Remove everything after specific headers ---
    header = section.find(
        ["strong", "b", "h1", "h2", "h3", "h4"],
        string=lambda x: (
            x and any(trigger in x.lower() for trigger in SECTION_CUTOFF_HEADERS)
        )
    )

    if header:
        for tag in header.find_all_next():
            tag.decompose()
        header.decompose()

    # --- 2. Remove fluff paragraphs ---
    for p in section.find_all("p"):
        text = p.get_text().lower()
        if any(keyword in text for keyword in FLUFF_KEYWORDS):
            p.decompose()

    return section

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
            })
        else:
            results.append({
                "phrase": match.group(0),
                "min_years": convert(single_val),
                "max_years": None,
            })

    return results

def block_redirect(route, request):
    if request.is_navigation_request() and request.redirected_from:
        route.abort()
    else:
        route.continue_()

def get_full_description(jobObj):  

    success = False

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            args=[
                "--start-maximized",
                "--disable-blink-features=AutomationControlled",
                "--disable-infobars"
            ]
        )

        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/122.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080},
            locale="en-AU",
            timezone_id="Australia/Melbourne"
        )

        context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined
            });
        """)


        pw_page = browser.new_page()
        #pw_page.route("**/*", block_redirect)
        job_url = jobObj.url   # reduce webpage get to redeuce time
        pw_page.goto(job_url)
        pw_page.wait_for_timeout(10)
        soup = BeautifulSoup(pw_page.content(), "html.parser")

        description = soup.select_one("section.adp-body")                   # reduce LLM token used
        if description is None:
            print("\n⚠  Failed to get full description. Please check with Playwright Browser.")
            input("Please paste content into content.txt'. Then press enter.")

            manual_description = util.load_text_file("content.txt")
            if manual_description != "":
                description = manual_description                       
                success = True
        else:
            description = clean_section(description)                            
            description = description.get_text(separator="\n", strip=True)
            success = True
        

        browser.close()

        return description, success

def info_checker(job: JobPosting):  # filter from job basic info to reduce LLM usage and web call
    reason = ""
    if job.days_ago > 30: # old job
        reason = reason + f"[>30 days] "
    if util.contains_keywords(job.title.lower(), SENIORITY_KEYWORDS):
        reason = reason + f"[Keyword ({[k for k in SENIORITY_KEYWORDS if k in job.title.lower()]}) "
    if util.contains_keywords(job.desciption, NON_PREFERED_KEYWORDS):
        reason = reason + f"Keyword ({[k for k in NON_PREFERED_KEYWORDS if k in job.desciption]}) "
                
    sym = '⚠  ' if reason != "" else ""
    return reason == "", f"""{sym}{reason}"""

def description_checker(JobDesc: str):     # filter with full description  # reduce LLM usage

    desc_pass, exp_pass = True, True
    reason = ""

    if JobDesc.strip() == "":
        desc_pass = False
        reason = reason + f"⚠ Meaningless Talk"

    yrs_of_exp = extract_experience(JobDesc)   #yrs of exp check
    if yrs_of_exp:
        for exp in yrs_of_exp:
            if exp['min_years'] > 2:
                exp_pass = False
                reason = reason + f"⚠ Min Exp"
    
    if util.contains_keywords(JobDesc, NON_PREFERED_KEYWORDS):
        reason = reason + f"⚠  Keyword ({[k for k in NON_PREFERED_KEYWORDS if k in JobDesc]}).\n"
        desc_pass = False

    return desc_pass, exp_pass, yrs_of_exp, reason

def m1_via_api():

    position = input("You are looking for? ")
    os.system('cls' if os.name == 'nt' else 'clear')

    app_id, app_key = load_api_param()
    
    results_per_page = 3

    params = {
        "app_id": app_id,
        "app_key": app_key,
        "what": position,
        "where": "melbourne",
        "what_exclude": "senior lead principal manager director",
        "max_days_old": 30,
        "results_per_page": results_per_page,
        "distance": 25
    }

    page_num = 0

    limit = 99999

    while limit == 99999 or min(results_per_page*page_num, data['count']) <= limit:

        shortlist = []

        page_num += 1
        response = requests.get(url + str(page_num), params=params)
        data = response.json()  # TODO: Should check response status and handle errors
        limit = data['count']

        print(f"Showing {results_per_page*(page_num-1)+1} - {min(results_per_page*page_num, data['count'])} of {data['count']} job listings (Page {page_num}) for '{params['what']}' in '{params['where']}' within {params['distance']}km radius:")
        
        for job in data["results"]:
            
            jobObj = JobPosting(
                title = job.get('title'),
                company = job.get('company'),
                location = job.get('location'),
                date_created = job.get('created'),
                url = job.get('redirect_url'),
                description = job.get('description'),
                contract_time = job.get('contract_time') or "N/A"
            )

            if job['category']['label'] != "IT Jobs":
                continue
            
            prev_pass = jobObj.id in util.load_text_file("pass_list.txt").split("\n")
            if prev_pass:
                print(jobObj, " 🅿️ Record")
                continue

            book_pass = jobObj.id in util.load_text_file("bookmarks.txt").split("\n")
            if book_pass:
                print(jobObj, "🔖 Bookmarked")
                continue

            info_pass, reason = info_checker(jobObj)
            if not info_pass:
                print(jobObj, f" 🅿️ Saved", reason)
                save2pass(jobObj.id)
                continue

            print(jobObj, f"📜 Approved")

            shortlist.append(jobObj)
        
        if len(shortlist) > 0:
            # input(f"\n{"[Enter]":<7} -> Description Check")
            util.countdown("Description Check ", 5)
            os.system('cls' if os.name == 'nt' else 'clear')
            

        for job in shortlist:

            job.desciption, full_desc_success = get_full_description(job) # TODO: this need to be replace with a more anti bot version
            desc_pass, exp_pass, yrs_exp, reason = description_checker(job.desciption)
            job.set_yrs_exp(yrs_exp)

            if not desc_pass or not exp_pass:
                print(job, f" 🅿️ Saved")
                print(job.print_yrs_exp())
                save2pass(job.id)
                continue
            if exp_pass:
                print(job, f"📜 Approved")
                job.to_json()
        
            llm.llm_seq(job)
            
            decision = input(f"\n{"[Enter]":<7} -> 🅿️ Pass\n{"[a]":<7} -> 🔖 Save to Bookmark\n{"[e]":<7} -> 🚶 Exit\n")
            match decision:
                case "a":
                    save2bookmark(job.id, str(job))
                case "e":
                    exit()
                case _:
                    save2pass(job.id)
                    # unmatched skillset statics

            os.system('cls' if os.name == 'nt' else 'clear')
   

def m2_via_html():
    project_folder = Path(__file__).parent
    html_files = list(project_folder.glob("*.html"))

    if html_files:
        html_file = html_files[0]
        soup = BeautifulSoup(html_file.read_text(encoding="utf-8"), "html.parser")
    else:
        print("No HTML files found.")
        input()

    
    # create jobObj from local HTML
    main_post = soup.select_one("main.ui-main")
    title = soup.select_one("h1.leading-none")#.getText().strip()
    job_info = soup.select_one("div.flex-grow").select_one("div.ui-job-card-info")#.getText().strip()
    description = soup.select_one("section.adp-body").getText().strip()


    print(title)
    print(job_info)
    
    input()

    jobObj = JobPosting(
        title = job.get('title'),
        company = job.get('company'),
        location = job.get('location'),
        date_created = job.get('created'),
        url = job.get('redirect_url'),
        description = job.get('description'),
        contract_time = job.get('contract_time') or "N/A"
    )

    print(jobObj)


    # Proceed to LLM Filter (extracted refactor code from mode 1)

def save2pass(ID: str):
    if not ID in util.load_text_file("pass_list.txt").split("\n"):
        with open('pass_list.txt', 'a', encoding='utf-8') as f:
            f.write(f'{ID}\n')

def save2bookmark(ID: str, txt):
    if not ID in util.load_text_file("bookmarks.txt").split("\n"):
        with open('bookmarks.txt', 'a', encoding='utf-8') as f:
            f.write(f'{ID}\n')

if __name__ == "__main__":

    # init info for all modes
    SKILL_KEYWORDS = ["requirement", "certification", "tech stack", "skill", "responsibilities", "nice to have", "must have"]
    SENIORITY_KEYWORDS = util.load_text_file("seniority_word_list.txt").split("\n")
    NON_PREFERED_KEYWORDS = [ "vehicle", "travel", "Driving License", "NV1 Clearance", "NV1"]
    now = datetime.now(timezone.utc)

    mode = None
    while mode != "1":
        print(f"Welcome to Job Streamlinear!\n\n Please select mode:")
        print(f" 1. Auto Search via Adzuna API")
        print(f" 2. Paste via URL (WIP)")
        print(f" 3. Paste Raw Text (WIP)")
        print(f" 4. View Bookmark")
        print(f" 5. Test LLM")
        print(f" 6. cover letter")
        mode = input()

        match mode:
            case "1":
                os.system('cls' if os.name == 'nt' else 'clear')
                m1_via_api()
            case "2":
                m2_via_html()
            case "3":
                print("WIP")
            case "4":
                text = util.load_text_file("bookmarks.txt").split('\n')
                for each in text:
                    print()
            case "5":
                break
            case "6":
                job = json.loads(util.load_text_file("job_json.txt"))
                person = json.loads(util.load_text_file("personal_profile.txt"))
                llm.generates_cover_letter(job, person)
            case _:
                print("Invalid mode selected. Exiting.")
                exit()


        
        
    
    
