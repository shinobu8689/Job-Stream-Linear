import json
from playwright.sync_api import sync_playwright
import requests
from datetime import datetime, timezone
from bs4 import BeautifulSoup
import os
import re
import time
from pathlib import Path


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

def contains_keywords(text, keywords):
    if not text:
        return False

    text_lower = text.lower()
    return any(keyword.lower() in text_lower for keyword in keywords)

SKILL_KEYWORDS = ["requirement", "certification", "tech stack", "skill", "responsibilities", "nice to have", "must have"]
SENIORITY_KEYWORDS = [ "senior", "lead", "principal", "manager", "Level 2", "Director"]
NON_PREFERED_KEYWORDS = [ "vehicle", "travel", "Driving License"]

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

def analyze_with_llm(text, model="gemma3:12b"):
    print("⟲ Generating analysis...")

    prompt = f"""
    Extract the following from the job description:

    {{
        "skills": [],
        "optional_skills":[]
        "min_experience_years": int or null,
        "responsibilities": []
        "japan_career_relevance": [
            "score": float (between 0-1),
            "verdict": "Helpful" or "Neutral" or "Risky",
            "reason": str (one-sentence reason of how would it help to work in Japan in a future in IT industry)
        ]
    }}

    Only return valid JSON. Ignore marketing fluff.
    
    Job description:
    {text}
    """

    response = requests.post(       # to local ollama LLM
        "http://localhost:11434/api/generate",
        json={
            "model": model,
            "prompt": prompt,
            "max_length": 1024,
            "stream": False
        }
    )

    return json.loads(response.text)['response'][7:-3]    # text need to be parsed

def hyperlink(label, url):
    ESC = "\033]"
    BEL = "\007"
    return f"{ESC}8;;{url}{BEL}{label}{ESC}8;;{BEL}"

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
        job_url = jobObj.url   # reduce webpage get to redeuce time
        pw_page.goto(job_url)
        pw_page.wait_for_timeout(10)
        soup = BeautifulSoup(pw_page.content(), "html.parser")

        description = soup.select_one("section.adp-body")                   # reduce LLM token used
        if description is None:
            print("\n⚠  Failed to get full description. Please check with Playwright Browser.")
            input("Please save page HTML file in the dir. Then press enter.")
            
            # TODO: get HTML file in project folder.
            manual_description = None 
            if manual_description != "":
                description = manual_description
                description = clean_section(description)                            
                description = description.get_text(separator="\n", strip=True)
                success = True
        else:
            description = clean_section(description)                            
            description = description.get_text(separator="\n", strip=True)
            success = True
        

        browser.close()

        return description, success

def save2txt(filename, content):
    with open(filename, "w", encoding="utf-8") as f:
        f.write(str(content))

def info_checker(job: JobPosting):  # filter from job basic info to reduce LLM usage and web call
    reason = ""
    if job.days_ago > 30: # old job
        reason = reason + f"⚠  Job is older than 30 days.\n"
    if contains_keywords(job.title.lower(), SENIORITY_KEYWORDS):
        reason = reason + f"⚠  Contains senior-level keyword ({[k for k in SENIORITY_KEYWORDS if k in job.title.lower()]}).\n"
    if contains_keywords(job.desciption, NON_PREFERED_KEYWORDS):
        reason = reason + f"⚠  Contains non-prefered keyword ({[k for k in NON_PREFERED_KEYWORDS if k in job.desciption]}).\n"
                
    if reason != "":
        print(f"""⚠  Info Check\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━""")
        print(reason)

    return reason == ""

def description_checker(JobDesc: str):     # filter with full description  # reduce LLM usage

    desc_pass = True
    exp_pass = True


    years_of_experience = extract_experience(JobDesc)   #yrs of exp check
    if years_of_experience:
        print(f"""Experience Check\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━""")
        
        for exp in years_of_experience:
            if exp['min_years'] > 2:
                tag = "⚠ " 
            else:
                tag = "- "
                exp_pass = False
            if exp["type"] == "range":  print(f"{tag}{exp['phrase']} ({exp['min_years']} - {exp['max_years']} years)")
            else:                       print(f"{tag}{exp['phrase']} ({exp['min_years']} years)")
        print()


    reason = ""
    if not contains_keywords(JobDesc, SKILL_KEYWORDS):
        reason = reason + f"⚠  Description might not include requirements or specification.\n"
        desc_pass = False
    if contains_keywords(JobDesc, NON_PREFERED_KEYWORDS):
        reason = reason + f"⚠  Contains non-prefered keyword ({[k for k in NON_PREFERED_KEYWORDS if k in JobDesc]}).\n"
        desc_pass = False

    if reason != "":
        print(f"""⚠  Description Check\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━""")
        print(reason)

    return desc_pass, exp_pass
    
    

class JobPosting:
    def __init__(self, title, company, location, date_created, url, description, contract_time = "N/A"):
        self.title = title
        self.company = company['display_name']
        self.location = location['display_name']
        self.date_created = parse_date(date_created)
        self.url = url
        self.contract_time = contract_time
        self.days_ago = days_to_today(date_created)
        self.desciption = description

    def __str__(self):
        if self.days_ago <= 0:  day_str = "Today"
        else:                   day_str = f"{self.days_ago} days ago"
        return f"""
 ● {self.title} - {self.company}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ ID: {hyperlink(self.url[self.url.rfind("/")+1:self.url.find("?")], self.url)} ━━━
{'Contract Type':<20}: {self.contract_time}
{'Location':<20}: {self.location}
{'Posted':<20}: {self.date_created} ({day_str})
"""

def m1_via_api():
    app_id, app_key = load_api_param()

    params = {
        "app_id": app_id,
        "app_key": app_key,
        "what": "Developer",
        "where": "melbourne",
        "results_per_page": 10,
        "distance": 25
    }

    page_num = 0
    job_counter = 0



    while True:
        page_num += 1

        response = requests.get(url + str(page_num), params=params)
        data = response.json()  # TODO: Should check response status and handle errors

        for job in data["results"]:

            job_counter += 1
            if job['category']['label'] != "IT Jobs": continue  # filter non-IT Job, this should be modularised as an option

            print(f"Found {job_counter}/{data['count']} job listings (Page {page_num}) for '{params['what']}' in '{params['where']}' within {params['distance']}km radius:\n")

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

            info_passes = info_checker(jobObj)
            if not info_passes:
                input("Enter to Next")
                os.system('cls' if os.name == 'nt' else 'clear')
                continue

            jobObj.desciption, full_desc_success = get_full_description(jobObj)

            if not full_desc_success:
                continue

            save2txt("desc.txt", jobObj.desciption)


            desc_pass, exp_pass = description_checker(jobObj.desciption)
            if not desc_pass:
                input("Enter to Next")
                os.system('cls' if os.name == 'nt' else 'clear')
                continue
            
            if exp_pass and input("⚠  Please review the years of experiences. Proceed? [Y / N}") == "Y":
                llm_result = analyze_with_llm(jobObj.desciption)    # TODO: currently ouputing raw json in text, this need to be parsed
                print(llm_result)
                
                save2txt("llm_json.txt", llm_result)
            else:
                os.system('cls' if os.name == 'nt' else 'clear')
                continue


            




            while True:
                decision = input(f"\n Options:\nEnter -> Next\na -> Save to Pass List (WIP)\nd -> Show Description\n")
                match decision:
                    case "d":
                        print(f"\n==========   Full Description   ==========\n{jobObj.desciption}")
                        print(f"==========     End Description      ==========\n")
                    case "a":
                        print(f"\n Saved to Pass List. (WIP, not really saving.)")
                        # WIP, save ID to pass list
                    case _:
                        break




            #implement LLM with getting the matching score of my capability and the job requirement, and the improvment point to reach this job  

            '''
                ⟲ Generating analysis...
                ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ Score: 72% ━━━
                ● Skills                ● Nice to have
                    ✔ Java                  - OmniStudio
                    - Kotlin                - Azure
                    - React                 - CI/CD
                    ✔ Typescript
                    - Springboot
                    - Kubernetes
                    ✔ REST API

                ⚠ Experience Req : Software Engineer (3-5 years)

                ● Responsibilities
                    - Building and enhancing MYOB's checkout journey
                    - Enabling secure, seamless connectivity between MYOB and financial institutions
                    - Designing and developing scalable, performant, and secure systems
                    - Collaboration with team member               

                ● Career Relevance: 60% (Helpful)
                Experience with cloud platforms (AWS, Azure), Kubernetes, and scalable systems are valuable in the Japanese IT landscape, which is increasingly adopting cloud-native technologies.

                ● Improvement Suggestion
                Learn Kubernetes fundamentals and deploy a demo project.
            '''

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





if __name__ == "__main__":

    # init info for all modes
    now = datetime.now(timezone.utc)

    mode = None
    while mode != "1":
        print(f"Welcome to Job Streamlinear!\n\n Please select mode:")
        print(f" 1. Auto Search via Adzuna API")
        print(f" 2. Paste via URL (WIP)")
        print(f" 3. Paste Raw Text (WIP)")
        mode = input()

        match mode:
            case "1":
                os.system('cls' if os.name == 'nt' else 'clear')
                m1_via_api()
            case "2":
                m2_via_html()
            case "3":
                print("WIP")
            case _:
                print("Invalid mode selected. Exiting.")
                exit()


        
        
    
    
