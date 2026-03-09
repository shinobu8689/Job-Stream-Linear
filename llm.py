import json
import requests
from jobObj import JobPosting
import util


def analyse_with_llm(text, model="gemma3:12b"):
    print("⟲ Generating analysis...")

    prompt = f"""
Extract the following from the job description. Return STRICT valid JSON only. 

{{
  "skills": [string],
  "optional_skills": [string],
  "min_experience_years": [
    {{
      "phase": string,
      "min_years": number,
      "max_years": number
    }}
  ] or null,
  "responsibilities": [string],
  "japan_career_relevance": {{
    "score": float (0 - 1),
    "verdict": "Helpful" | "Neutral" | "Risky",
    "reason": string
  }},
  "company_focus": string
}}

Rules:
- Use numbers for years (no text like "1 year").
- If only a minimum is mentioned, omit max_years.
- responsibilities should include the duties of this role.
- If no experience requirement is mentioned, return null.
- Remove marketing or culture statements.
- Keep skills concise (technologies, tools, frameworks).
    
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

    return json.loads(response.text)['response'][7:-3]

def parse_response(text):

    resp = json.loads(text)

    pp = json.loads(util.load_text_file("personal_profile.txt")).get("skills")
    pp = [s.lower() for s in pp]

    print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    skills = resp.get('skills')
    opt_skills = resp.get('optional_skills')
    print(f'{"● Skills":<35}{"● Nice to have":<35}')
    for each in range(max(len(skills), len(opt_skills))):
        if each <= len(skills)-1 and skills[each].lower() in pp: 
            check_L = "  ✔  " 
        else: 
            check_L = "  -  "
        if each <= len(opt_skills)-1 and opt_skills[each].lower() in pp: 
            check_R = "  ✔  " 
        else: 
            check_R = "  -  "
        left = check_L + skills[each] if each <= len(skills)-1 else ""
        right = check_R + opt_skills[each] if each <= len(opt_skills)-1 else ""

        print(f"{left:<35}{right:<35}")

    print()
    focus = resp.get("company_focus")
    print(f"● Company Focus: {focus}")

    print()
    responsibilities = resp.get('responsibilities')
    print(f"● Responsibilities")
    for each in responsibilities:
        print(f"  - {each}")

    print()

    exp_years = resp.get('min_experience_years')
    if exp_years:
        print("● Experience Req")
        for each in exp_years:
            phase = each.get("phase", "Unknown")
            min_years = each.get("min_years")
            max_years = each.get("max_years")

            if max_years is None:
                print(f"  - {phase} ({min_years} years)")
            else:
                print(f"  - {phase} ({min_years} - {max_years} years)")

    relevance = resp.get('japan_career_relevance')
    print(f"""
● Career Relevance: {int(float(relevance.get('score')*100))}% ({relevance.get('verdict')})
{relevance.get('reason')}
""")
    

def suggestion_with_llm(text, model="gemma3:12b"):
    
    print(f"⟲ Generating Sugggestions...")

    capabilities = set(util.load_text_file("personal_profile.txt").lower().split("\n"))
    skills = json.loads(text.lower()).get('skills')
    opt_skills = json.loads(text.lower()).get('optional_skills')


    skill_set = set(skills + opt_skills)

    # union of both sets
    combined_set = capabilities | skill_set

    combined_list = []

    for skill in combined_set:
        combined_list.append({
            "skill": skill,
            "required_by_job": skill in skills,
            "optional_for_job": skill in opt_skills,
            "i_have": skill in capabilities
        })

    # JSON output
    combined_json = json.dumps(combined_list, indent=2)

    

    prompt = f"""
Evaluate how well I match this job.
Do not include explanations

Return JSON only in this format:
{{
"matching_score": float (0 - 1),
"suggestion": string
}}

Scoring rules:
- A skill where required_by_job=true and i_have=true is a strong match.
- A skill where required_by_job=true and i_have=false is a missing required skill and should reduce the score.
- A skill where optional_for_job=true and i_have=true is a bonus.
- Skills where required_by_job=false and optional_for_job=false can be ignored.

Job summary:
{text}

Skill comparison data:
{combined_json}

Give a matching score and a one sentence suggestion on what skill I should improve to better match this job.
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

    return json.loads(response.text)['response'][7:-4]

def parse_improvement(text):
    resp = json.loads(text)

    score = resp.get('matching_score')

    if score >= 0.75:
        label = "Strong"
    elif score >= 0.60:
        label = "Possible"
    elif score >= 0.45:
        label = "Stretch"
    else:
        label = "Skip"

    print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━ Matching Score: {int(score*100)}% ━━━")
    print(f"{resp.get('suggestion')}")


def llm_seq(desc):
    llm_result = analyse_with_llm(desc)
    util.save2txt("llm_json.txt", llm_result)
    parse_response(llm_result)

    llm_suggestion = suggestion_with_llm(llm_result)
    util.save2txt("llm_sugg.txt", llm_suggestion)
    parse_improvement(llm_suggestion)

def generates_cover_letter(job: json, person: json, llm_analyitcs: json, model="gemma3:12b"):


    print("⟲ Generating Opening Paragraph...")

    prompt = f"""
Write the opening paragraph for a cover letter.

Job title: {job.get('title')}
Company: {job.get('company')}

Candidate background:
- Computer Science graduate
- Personal Developer
- Builds automation tools and data projects

Keep it concise and professional.
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

    print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(json.loads(response.text)['response'])
    print()





    # TODO: create overlap skills combine here
    print("⟲ Generating Skills/Project Hightlighs...")      # only give LLM the skills that the job and person overlaps.
    prompt = f"""
Write a paragraph describing relevant technical skills.

Job requires:
{llm_analyitcs.get('skills')}

Candidate skills:
{person.get('skills')}

Candidate projects:
{person.get('projects')}

Focus on relevant overlap and practical experience.
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

    print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(json.loads(response.text)['response'])
    print()





    # TODO: Candidate interests should be in pp.txt
    print("⟲ Generating \"Why this company\" talk...")      # only give LLM the skills that the job and person overlaps.
    prompt = f"""
Write a paragraph explaining why the candidate is interested in the company.

Company focus:
{job.get('company_focus')}

Candidate interests:
automation, data tools, developer tooling
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

    print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(json.loads(response.text)['response'])
    print()





    print("⟲ Generating Closing Paragraph...")  
    prompt = f"""
Write a short professional closing paragraph for a cover letter.
Express interest in discussing the role further.
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

    print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(json.loads(response.text)['response'])
    print()