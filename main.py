import json
from playwright.sync_api import sync_playwright
import requests
from datetime import datetime, timezone
from bs4 import BeautifulSoup
import os
import re
from pathlib import Path
from jobObj import JobPosting
from collections import Counter
import llm
import util

headers = {"User-Agent": "Mozilla/5.0"}

url = "https://api.adzuna.com/v1/api/jobs/au/search/"

def load_api_param():
    '''
    param.txt stores user_id and api_key for Adzuna API, which is required to run auto mode. 
    Please create the file with your app_id and app_key.
    '''
    if not os.path.exists("param.txt"): 
        raise FileNotFoundError(f"Parameter file '{"param.txt"}' not found. Please create the file with your app_id and app_key.")
    else:
        with open("param.txt", "r") as f:  lines = f.readlines()
        app_id = lines[0].strip() if len(lines) > 0 else ""
        app_key = lines[1].strip() if len(lines) > 1 else ""

    return app_id, app_key

FLUFF_KEYWORDS = util.load_text_file("words_filter/fluff_words.txt").split("\n")

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
    '''
    basic description section filter.
    remove fluff paragraphs and everything after specific headers that usually indicate non-description content.
    might not work if the description is a blob on words without sections.
    Set to be not too aggresive to avoid removing useful info, but can be further improved with more comprehensive fluff keywords and section cutoff headers.
    '''

    # Remove everything after specific HTML headers
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

    # Remove fluff paragraphs
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
    '''
    get years of experience requirement from job description with regex.
    LLM will catch the info that cannot caught by regex, but this can be a basic filter to reduce LLM usage.
    '''
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
    '''
    Block navigation requests that are redirects to prevent leaving the job description page. Might be used in certaun cases.
    '''
    if request.is_navigation_request() and request.redirected_from:
        route.abort()
    else:
        route.continue_()

def get_full_description(jobObj):  
    '''
    fetch full job description with Playwright, cleaned without non-nesscary info for decision making.
    '''
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
        else:
            description = clean_section(description)                            
            description = description.get_text(separator="\n", strip=True)
        

        browser.close()

        return description

def info_checker(job: JobPosting):  # filter from job basic info to reduce LLM usage and web call
    reason = ""
    if job.days_ago > 30: # old job
        reason = reason + f"[>30 days] "
    if util.contains_keywords(job.title.lower(), SENIORITY_KEYWORDS):
        reason = reason + f"Keyword ({[k for k in SENIORITY_KEYWORDS if k in job.title.lower()]}) "
    if util.contains_keywords(job.desciption, NON_PREFERED_KEYWORDS):
        reason = reason + f"Keyword ({[k for k in NON_PREFERED_KEYWORDS if k in job.desciption]}) "
                
    sym = '⚠  ' if reason != "" else ""
    return reason == "", f"""{sym}{reason}"""

def manual_info_checker(text: str):  # filter from job basic info to reduce LLM usage and web call
    reason = ""
    if util.contains_keywords(text.split("View all jobs")[0].lower(), SENIORITY_KEYWORDS):
        reason = reason + f"Keyword ({[k for k in SENIORITY_KEYWORDS if k in text.lower()]}) "
    if util.contains_keywords(text.lower(), NON_PREFERED_KEYWORDS):
        reason = reason + f"Keyword ({[k for k in NON_PREFERED_KEYWORDS if k in text.lower()]}) "
                
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
        reason = reason + f"⚠  Keyword ({[k for k in NON_PREFERED_KEYWORDS if k in JobDesc.lower()]}).\n"
        desc_pass = False

    return desc_pass, exp_pass, yrs_of_exp, reason

# stats collection for further analysis.

FILE = Path("skills_stats.json")

def load_stats():
    if FILE.exists():
        return Counter(json.loads(FILE.read_text()))
    return Counter()

def save_stats(counter):
    FILE.write_text(json.dumps(counter, indent=2))

def update_skills():
    stats = load_stats()
    job_json = json.loads(util.load_text_file("temp/job.json"))
    job_skills = job_json.get('skills')
    job_skills = [s.lower() for s in job_skills]
    job_opt_skills = job_json.get('opt_skills')
    job_opt_skills = [s.lower() for s in job_opt_skills]

    skills_found = list(set(job_skills + job_opt_skills))
    stats.update(skills_found)
    save_stats(stats)

# operational functions

def m1_via_api():

    position = input("You are looking for? ")
    os.system('cls' if os.name == 'nt' else 'clear')


    # get results from API
    app_id, app_key = load_api_param()
    results_per_page = 5
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
    # continue until all result

        shortlist = []

        page_num += 1
        response = requests.get(url + str(page_num), params=params)
        data = response.json()
        limit = data['count']

        print(f"Showing {results_per_page*(page_num-1)+1} - {min(results_per_page*page_num, data['count'])} of {data['count']} job listings (Page {page_num}) for '{params['what']}' in '{params['where']}' within {params['distance']}km radius:")
        
        
        for job in data["results"]: # short condition check
            
            jobObj = JobPosting(
                title = job.get('title'),
                company = job.get('company'),
                location = job.get('location'),
                date_created = job.get('created'),
                url = job.get('redirect_url'),
                description = job.get('description'),
                contract_time = job.get('contract_time') or "N/A"
            )

            if job['category']['label'] != "IT Jobs":  # this is be an option instead of hard coded
                continue
            
            prev_pass = jobObj.id in util.load_text_file("temp/pass_list.txt").split("\n")
            if prev_pass:
                print(jobObj, " 🅿️ Record")
                continue

            book_pass = jobObj.id in util.load_text_file("temp/bookmarks.txt").split("\n")
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
            util.countdown("Description Check ", 5)
            os.system('cls' if os.name == 'nt' else 'clear')
            

        for job in shortlist:   # desctiption check

            job.desciption = get_full_description(job) # might replace with a more anti bot version
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
        
            # procee to LLM for skill extraction and cover letter generation if approved by description check
            llm.llm_seq(job)
            

            decision = input(f"\n{"[Enter]":<7} -> 🅿️ Pass\n{"[a]":<7} -> 🔖 Save to Bookmark\n{"[c]":<7} -> 📎 Generates Cover Letter & 🔖\n{"[e]":<7} -> 🚶 Exit\n")
            match decision:
                case "a":
                    save2bookmark(job.id, str(job))
                    update_skills()
                case "c":
                    update_skills()
                    llm.generates_cover_letter(json.loads(util.load_text_file("temp/job.json")), person = json.loads(util.load_text_file("temp/personal_profile.json")))
                    save2bookmark(job.id, str(job))
                    print("Saved to 🔖 Bookmark.")
                    util.countdown("", 5)
                case "e":
                    exit()
                case _:
                    save2pass(job.id)
                    update_skills()

            os.system('cls' if os.name == 'nt' else 'clear')


def m2_via_txt():
    '''
    manual mode text might be in inconsistent format. It breifly check for basic requirements and pass to LLM.
    optimised workflow for job description that is not on Adzuna.
    Tested on: Seek, Indeed.
    More formats from other platforms can be expanded later on.
    '''

    os.system('cls' if os.name == 'nt' else 'clear')

    content = util.load_text_file("content.txt")

    # regex to find date posted
    match = re.search(r"Posted (\d+)d ago", content)
    if match:   days = int(match.group(1))
    else:       days = None

    info_pass, reason = manual_info_checker(content)
    if not info_pass:
        print(f"🅿️ Basic Check Failed", reason)
        return

    print(f"📜 Basic Check Approved")


    desc_pass, exp_pass, yrs_exp, reason = description_checker(content)
    if not desc_pass or not exp_pass:
        print(f"🅿️ Description Check Failed", reason)
        print(f" Years of Experience: {yrs_exp}")
    if exp_pass:
        print(f"📜 Description Check Approved")

    job_basic = llm.get_basic_info(content)
    jobObj = JobPosting.manual_init(
        title=job_basic.get('title'),
        company=job_basic.get('company'),
        location=job_basic.get('location'),
        date_created=util.days_ago(days) if days is not None else None,
        url="N/A",
        description=content,
        contract_time=job_basic.get('contract_time') or "N/A"
    )

    jobObj.set_yrs_exp(yrs_exp)
    jobObj.to_json()
    print(jobObj)

    llm.llm_seq(jobObj)

    decision = input(f"\n{"[Enter]":<7} -> 🚶 Exit\n{"[c]":<7} -> 📎 Generates Cover Letter\n")
    match decision:
        case "c":
            update_skills()
            llm.generates_cover_letter(json.loads(util.load_text_file("temp/job.json")), person = json.loads(util.load_text_file("personal_profile.json")))
            util.countdown("", 5)
        case _:
            update_skills()

    return 
    






def save2pass(ID: str):
    if not ID in util.load_text_file("temp/pass_list.txt").split("\n"):
        with open('temp/pass_list.txt', 'a', encoding='utf-8') as f:
            f.write(f'{ID}\n')

def save2bookmark(ID: str, txt):
    if not ID in util.load_text_file("temp/bookmarks.txt").split("\n"):
        with open('temp/bookmarks.txt', 'a', encoding='utf-8') as f:
            f.write(f'{ID}\n')

if __name__ == "__main__":

    # init info for all modes
    # TODO: word list should be load with txt tile
    SENIORITY_KEYWORDS = util.load_text_file("words_filter/seniority_words.txt").split("\n")
    NON_PREFERED_KEYWORDS = util.load_text_file("words_filter/non_prefered_words.txt").split("\n")
    now = datetime.now(timezone.utc)

    mode = None
    while mode != "1":
        print(f"Welcome to Job Streamlinear!\n\n Please select mode:")
        print(f" 1. Auto Search via Adzuna API")
        print(f" 2. Analyse Description (Seek) txt file - Put text in content.txt")
        print(f" 3. Generates Cover Letter - Run Analyse (2) first")
        print(f" 4. View Bookmarked Adzuna Jobs")
        mode = input()

        match mode:
            case "1":
                os.system('cls' if os.name == 'nt' else 'clear')
                m1_via_api()
            case "2":
                m2_via_txt()
            case "3":
                job = json.loads(util.load_text_file("temp/job.json"))
                person = json.loads(util.load_text_file("personal_profile.json"))
                llm.generates_cover_letter(job, person)
            case "4":
                text = util.load_text_file("temp/bookmarks.txt").split('\n')
                for each in text:
                    print(each)
            case _:
                print("Invalid mode selected. Exiting.")
                exit()


        
        
    
    
