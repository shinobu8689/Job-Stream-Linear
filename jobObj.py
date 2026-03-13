import json

import util

class JobPosting:
    def __init__(self, title, company, location, date_created, url, description, contract_time = "N/A"):
        self.title = title
        self.company = company['display_name']
        self.location = location['display_name']
        self.date_created = util.parse_date(date_created)
        self.url = url
        self.id = url[self.url.rfind("/") + 1 : self.url.find("?") if "?" in self.url else None]
        self.contract_time = contract_time
        self.days_ago = util.days_to_today(date_created)
        self.desciption = description

        # info from llm parse desc
        self.skills = None
        self.opt_skills = None
        self.yrs_exp = None
        self.responsibilities = None
        self.company_focus = None
    
    def from_llm(self, content: json):
        self.skills = content.get("skills")
        self.opt_skills = content.get("optional_skills")
        self.yrs_exp = content.get("min_experience_years")
        self.responsibilities = content.get("responsibilities")
        self.company_focus = content.get("company_focus")

    def set_yrs_exp(self, yrs_exp):
        self.yrs_exp = yrs_exp

    def print_yrs_exp(self):
        yrs = ""
        for exp in self.yrs_exp:
            if exp['min_years'] > 2:    yrs = yrs + "  ⚠ "
            else:                       yrs = yrs + "  - "
            if exp['max_years']:        yrs = yrs + f"{exp['phrase']} ({exp['min_years']} - {exp['max_years']} years)\n"
            else:                       yrs = yrs + f"{exp['phrase']} ({exp['min_years']} years)\n"
        return yrs

    def to_json(self):
        json_str = json.dumps(self.__dict__, indent=2)
        util.save2txt(f"job.json", json_str)

    def __str__(self):
        if self.days_ago <= 0:  day_str = "Today"
        else:                   day_str = f"{self.days_ago} days ago"

        title_company = f"{self.title} - {self.company}"
        if len(title_company) > 55:
            title_company = title_company[:52] + "..."
        return (
            f"{util.hyperlink('🔗', self.url)} {self.id:<12}"
            f"{(title_company):<60}"
            f"{self.contract_time:<11}"
            f"{util.hyperlink('🗺️', util.clean_url(f'https://www.google.com/search?q={self.location}'))} {self.location.split(", ")[0]:<15}"
            f"{self.date_created:<10} ({day_str + ")":<12}"
        )
    
    