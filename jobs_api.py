"""
Jobs API Integration — Multi-source live job data (NO API key required!)
Sources:
  1. Remotive.com  — curated remote jobs with salary data
  2. Arbeitnow.com — global job board with wide coverage
  3. JSearch (RapidAPI) — optional, if user provides a subscribed key

Handles search, caching, normalization, ranking, and error recovery.
"""

import os
import re
import html
import requests
from datetime import datetime, timezone
from cachetools import TTLCache
from concurrent.futures import ThreadPoolExecutor, as_completed

# ─────────────────────────────────────────────
#  CONFIG
# ─────────────────────────────────────────────
# JSearch (optional — only used if key is valid + subscribed)
RAPIDAPI_KEY  = os.environ.get("JSEARCH_API_KEY", "")
RAPIDAPI_HOST = "jsearch.p.rapidapi.com"
JSEARCH_URL   = "https://jsearch.p.rapidapi.com/search"

# In-memory cache: 64 entries, 5-minute TTL
_cache = TTLCache(maxsize=64, ttl=300)


# ─────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────
def _relative_time(dt_str: str | int | None) -> str:
    """Convert datetime string or unix timestamp to relative time."""
    if not dt_str:
        return "Recently"
    try:
        if isinstance(dt_str, (int, float)):
            posted = datetime.fromtimestamp(dt_str, tz=timezone.utc)
        else:
            posted = datetime.fromisoformat(str(dt_str).replace("Z", "+00:00"))
        now   = datetime.now(timezone.utc)
        delta = now - posted
        days  = delta.days
        if days == 0:    return "Today"
        elif days == 1:  return "Yesterday"
        elif days < 7:   return f"{days} days ago"
        elif days < 30:  return f"{days // 7} week{'s' if days >= 14 else ''} ago"
        elif days < 365: return f"{days // 30} month{'s' if days >= 60 else ''} ago"
        else:            return f"{days // 365} year{'s' if days >= 730 else ''} ago"
    except Exception:
        return "Recently"


def _strip_html(text: str) -> str:
    """Remove HTML tags and decode entities."""
    clean = re.sub(r'<[^>]+>', ' ', text)
    clean = html.unescape(clean)
    clean = re.sub(r'\s+', ' ', clean).strip()
    return clean


# ─────────────────────────────────────────────
#  NORMALIZERS — each source → common format
# ─────────────────────────────────────────────
def _normalize_remotive(raw: dict) -> dict:
    """Normalize a Remotive API job to our common format."""
    salary_str = raw.get("salary") or None
    salary_min, salary_max = 0, 0
    if salary_str:
        nums = re.findall(r'[\d,]+', salary_str.replace(',', ''))
        if len(nums) >= 2:
            salary_min = int(nums[0]) * (1000 if 'k' in salary_str.lower() else 1)
            salary_max = int(nums[1]) * (1000 if 'k' in salary_str.lower() else 1)
            salary_str = f"${salary_min:,} – ${salary_max:,}"
        elif len(nums) == 1:
            salary_min = int(nums[0]) * (1000 if 'k' in salary_str.lower() else 1)
            salary_str = f"${salary_min:,}+"

    location = raw.get("candidate_required_location") or "Worldwide"
    desc_raw = raw.get("description") or ""
    desc = _strip_html(desc_raw)

    return {
        "job_id":           f"rem_{raw.get('id', '')}",
        "title":            raw.get("title", "Unknown"),
        "company":          raw.get("company_name", "Unknown"),
        "company_logo":     raw.get("company_logo_url") or raw.get("company_logo"),
        "location":         f"🌐 Remote — {location}",
        "is_remote":        True,
        "employment_type":  (raw.get("job_type") or "full_time").replace("_", " ").title(),
        "description":      desc,
        "posted_at":        _relative_time(raw.get("publication_date")),
        "posted_raw":       raw.get("publication_date", ""),
        "salary":           salary_str,
        "salary_min":       salary_min,
        "salary_max":       salary_max,
        "salary_currency":  "USD",
        "salary_period":    "year",
        "apply_link":       raw.get("url", ""),
        "apply_options":    [],
        "qualifications":   [],
        "responsibilities": [],
        "benefits":         [],
        "publisher":        "Remotive",
        "tags":             [t.strip().lower() for t in (raw.get("tags") or [])],
        "category":         raw.get("category", ""),
    }


def _normalize_arbeitnow(raw: dict) -> dict:
    """Normalize an Arbeitnow API job to our common format."""
    location = raw.get("location") or "Not specified"
    is_remote = raw.get("remote", False)
    if is_remote:
        location = f"🌐 Remote — {location}" if location != "Not specified" else "🌐 Remote"

    job_types = raw.get("job_types") or []
    emp_type = "Full Time"
    for jt in job_types:
        jt_lower = jt.lower()
        if "part" in jt_lower: emp_type = "Part Time"
        elif "contract" in jt_lower: emp_type = "Contract"
        elif "intern" in jt_lower: emp_type = "Internship"
        elif "freelance" in jt_lower: emp_type = "Freelance"

    desc_raw = raw.get("description") or ""
    desc = _strip_html(desc_raw)

    return {
        "job_id":           f"arb_{raw.get('slug', '')}",
        "title":            raw.get("title", "Unknown"),
        "company":          raw.get("company_name", "Unknown"),
        "company_logo":     None,
        "location":         location,
        "is_remote":        is_remote,
        "employment_type":  emp_type,
        "description":      desc,
        "posted_at":        _relative_time(raw.get("created_at")),
        "posted_raw":       str(raw.get("created_at", "")),
        "salary":           None,
        "salary_min":       0,
        "salary_max":       0,
        "salary_currency":  "EUR",
        "salary_period":    "",
        "apply_link":       raw.get("url", ""),
        "apply_options":    [],
        "qualifications":   [],
        "responsibilities": [],
        "benefits":         [],
        "publisher":        "Arbeitnow",
        "tags":             [t.strip().lower() for t in (raw.get("tags") or [])],
        "category":         "",
    }


def _normalize_jsearch(raw: dict) -> dict:
    """Normalize a JSearch API job to our common format."""
    city    = raw.get("job_city") or ""
    state   = raw.get("job_state") or ""
    country = raw.get("job_country") or ""
    parts   = [p for p in (city, state, country) if p]
    location = ", ".join(parts) if parts else "Not specified"
    is_remote = raw.get("job_is_remote", False)
    if is_remote:
        location = f"🌐 Remote — {location}" if location != "Not specified" else "🌐 Remote"

    salary_min  = raw.get("job_min_salary")
    salary_max  = raw.get("job_max_salary")
    salary_cur  = raw.get("job_salary_currency", "USD")
    salary_per  = raw.get("job_salary_period", "")
    salary_str  = None
    if salary_min and salary_max:
        salary_str = f"{salary_cur} {salary_min:,.0f} – {salary_max:,.0f}"
        if salary_per: salary_str += f" / {salary_per.lower()}"
    elif salary_min:
        salary_str = f"{salary_cur} {salary_min:,.0f}+"

    apply_link = raw.get("job_apply_link", "")
    google_link = raw.get("job_google_link", "")
    has_direct = False

    for opt in (raw.get("apply_options") or []):
        if opt.get("is_direct", False):
            apply_link = opt.get("apply_link", apply_link)
            has_direct = True
            break
            
    # LinkedIn frequently redirects to the main feed if not logged in or if the scraper's token expired.
    # Google Jobs link is much more reliable as a fallback.
    if ("linkedin.com" in apply_link.lower() and not has_direct) or not apply_link:
        if google_link:
            apply_link = google_link

    highlights = raw.get("job_highlights") or {}

    return {
        "job_id":           raw.get("job_id", ""),
        "title":            raw.get("job_title", "Unknown Title"),
        "company":          raw.get("employer_name", "Unknown Company"),
        "company_logo":     raw.get("employer_logo"),
        "location":         location,
        "is_remote":        is_remote,
        "employment_type":  (raw.get("job_employment_type") or "FULLTIME").replace("_", " ").title(),
        "description":      raw.get("job_description") or "",
        "posted_at":        _relative_time(raw.get("job_posted_at_datetime_utc")),
        "posted_raw":       raw.get("job_posted_at_datetime_utc", ""),
        "salary":           salary_str,
        "salary_min":       salary_min or 0,
        "salary_max":       salary_max or 0,
        "salary_currency":  salary_cur,
        "salary_period":    salary_per,
        "apply_link":       apply_link,
        "apply_options":    raw.get("apply_options") or [],
        "qualifications":   (highlights.get("Qualifications") or [])[:6],
        "responsibilities": (highlights.get("Responsibilities") or [])[:6],
        "benefits":         (highlights.get("Benefits") or [])[:4],
        "publisher":        raw.get("job_publisher", "JSearch"),
        "tags":             [],
        "category":         "",
    }


# ─────────────────────────────────────────────
#  SOURCE FETCHERS
# ─────────────────────────────────────────────
def _fetch_remotive(query: str, limit: int = 15) -> list[dict]:
    """Fetch from Remotive (free, no key). Returns normalized jobs."""
    try:
        resp = requests.get(
            "https://remotive.com/api/remote-jobs",
            params={"search": query, "limit": min(limit, 50)},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        return [_normalize_remotive(j) for j in (data.get("jobs") or [])]
    except Exception as e:
        print(f"[Remotive] Error: {e}")
        return []


def _fetch_arbeitnow(query: str, page: int = 1) -> list[dict]:
    """Fetch from Arbeitnow (free, no key). Returns normalized jobs."""
    try:
        resp = requests.get(
            "https://www.arbeitnow.com/api/job-board-api",
            params={"search": query, "page": page},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        return [_normalize_arbeitnow(j) for j in (data.get("data") or [])[:20]]
    except Exception as e:
        print(f"[Arbeitnow] Error: {e}")
        return []


def _fetch_jsearch(query: str, page: int = 1) -> list[dict]:
    """Fetch from JSearch (requires subscribed RapidAPI key)."""
    if not RAPIDAPI_KEY:
        return []
    try:
        resp = requests.get(
            JSEARCH_URL,
            headers={
                "Content-Type": "application/json",
                "x-rapidapi-host": RAPIDAPI_HOST,
                "x-rapidapi-key": RAPIDAPI_KEY,
            },
            params={"query": query, "page": str(page), "num_pages": "1"},
            timeout=12,
        )
        resp.raise_for_status()
        data = resp.json()
        if "message" in data:  # e.g. "You are not subscribed"
            return []
        return [_normalize_jsearch(j) for j in (data.get("data") or [])]
    except Exception:
        return []


def _fetch_linkedin_live(query: str, page: int = 1) -> list[dict]:
    """Fetch live LinkedIn jobs using the public guest API."""
    try:
        import re
        import requests
        from datetime import datetime, timezone
        
        import urllib.parse
        import html
        
        safe_query = urllib.parse.quote(query)
        # LinkedIn guest API uses 'start' for pagination (0, 10, 20...)
        start = (page - 1) * 10
        url = f"https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?keywords={safe_query}&location=India&start={start}"
        resp = requests.get(url, timeout=10)
        html_content = resp.text

        jobs = []
        blocks = html_content.split('<li>')
        for block in blocks[1:]:
            link_m = re.search(r'href="(https://[a-z\.]*linkedin\.com/jobs/view/[^"]+)"', block)
            title_m = re.search(r'class="base-search-card__title">\s*(.+?)\s*</h3>', block, re.DOTALL)
            company_m = re.search(r'class="base-search-card__subtitle">.*?<a[^>]*>\s*(.+?)\s*</a>', block, re.DOTALL)
            if not company_m:
                company_m = re.search(r'class="base-search-card__subtitle">\s*(.+?)\s*</h4>', block, re.DOTALL)
            loc_m = re.search(r'class="job-search-card__location">\s*(.+?)\s*</span>', block, re.DOTALL)
            
            if link_m and title_m:
                title = title_m.group(1).strip()
                link = link_m.group(1).split('?')[0] # Remove tracking params
                
                # Accurately extract the numeric job ID
                job_id_match = re.search(r'view/(?:.*?-)?(\d+)/?', link)
                extracted_id = job_id_match.group(1) if job_id_match else link.split('-')[-1].strip('/')
                
                company = company_m.group(1).strip() if company_m else "Unknown Company"
                loc = loc_m.group(1).strip() if loc_m else "Not specified"
                
                is_remote = "remote" in loc.lower() or "remote" in title.lower()
                
                jobs.append({
                    "job_id": f"li_{extracted_id}",
                    "title": html.unescape(title),
                    "company": html.unescape(company),
                    "company_logo": None,
                    "location": loc,
                    "is_remote": is_remote,
                    "employment_type": "Full Time",
                    "description": f"View the full posting on LinkedIn for details about this role at {company}.",
                    "posted_at": "Recently",
                    "posted_raw": datetime.now(timezone.utc).isoformat(),
                    "salary": None,
                    "salary_min": 0,
                    "salary_max": 0,
                    "salary_currency": "USD",
                    "salary_period": "",
                    "apply_link": f"https://www.linkedin.com/jobs/search/?currentJobId={extracted_id}",
                    "apply_options": [],
                    "qualifications": [],
                    "responsibilities": [],
                    "benefits": [],
                    "publisher": "LinkedIn",
                    "tags": [query.lower()],
                    "category": "",
                })
        return jobs
    except Exception as e:
        print(f"[LinkedIn Live] Error: {e}")
        return []



# ─────────────────────────────────────────────
#  PUBLIC API
# ─────────────────────────────────────────────
def search_jobs(
    query: str,
    page: int = 1,
    num_pages: int = 1,
    country: str = "",
    date_posted: str = "all",
    remote_only: bool = False,
    employment_type: str = "",
) -> dict:
    """
    Search for jobs across multiple free sources in parallel.

    Returns:
        {
          "jobs":  [normalized_job, ...],
          "total": int,
          "page":  int,
          "error": str | None,
        }
    """
    cache_key = f"{query}|{page}|{remote_only}|{employment_type}|{country}"
    if cache_key in _cache:
        return _cache[cache_key]

    all_jobs = []
    errors = []

    # Fetch from all sources in parallel
    with ThreadPoolExecutor(max_workers=5) as pool:
        futures = {
            pool.submit(_fetch_remotive, query, 20): "Remotive",
            pool.submit(_fetch_arbeitnow, query, page): "Arbeitnow",
            pool.submit(_fetch_linkedin_live, query, page): "LinkedIn",
        }
        # Only add JSearch if key is available
        if RAPIDAPI_KEY:
            futures[pool.submit(_fetch_jsearch, query, page)] = "JSearch"

        for future in as_completed(futures, timeout=15):
            source = futures[future]
            try:
                jobs = future.result()
                all_jobs.extend(jobs)
            except Exception as e:
                errors.append(f"{source}: {str(e)[:60]}")

    # Apply filters
    if remote_only:
        all_jobs = [j for j in all_jobs if j["is_remote"]]

    if employment_type:
        et = employment_type.lower()
        all_jobs = [j for j in all_jobs if et in j["employment_type"].lower()]

    # Deduplicate by title+company
    seen = set()
    unique = []
    for j in all_jobs:
        key = f"{j['title'].lower().strip()}|{j['company'].lower().strip()}"
        if key not in seen:
            seen.add(key)
            unique.append(j)

    error_msg = None
    if not unique and errors:
        error_msg = "Could not fetch jobs: " + "; ".join(errors)
    elif not unique:
        error_msg = None  # just no results

    result = {
        "jobs":  unique,
        "total": len(unique),
        "page":  page,
        "error": error_msg,
    }
    if unique:  # only cache successful results
        _cache[cache_key] = result
    return result


# ─────────────────────────────────────────────
#  SKILL EXTRACTION
# ─────────────────────────────────────────────
def extract_skills_from_description(desc: str) -> list[str]:
    """Extract tech keywords from a job description for matching."""
    TECH_KEYWORDS = {
        'python','javascript','typescript','react','angular','vue','node.js','nodejs',
        'java','c++','c#','go','rust','swift','kotlin','scala','ruby','php','perl',
        'sql','postgresql','mysql','mongodb','redis','elasticsearch','dynamodb',
        'aws','gcp','azure','docker','kubernetes','terraform','jenkins','ci/cd',
        'git','linux','bash','html','css','sass','webpack','vite',
        'tensorflow','pytorch','machine learning','deep learning','nlp',
        'data science','data visualization','tableau','power bi','excel',
        'figma','sketch','adobe xd',
        'agile','scrum','jira','confluence',
        'rest api','graphql','microservices','serverless',
        'selenium','cypress','jest','pytest',
        'flask','django','spring boot','express','fastapi',
        'pandas','numpy','spark','hadoop','kafka','airflow',
        'computer vision','opencv','llm','generative ai',
        'salesforce','sap','oracle','next.js','shopify',
    }
    desc_lower = desc.lower()
    found = sorted([s for s in TECH_KEYWORDS if s in desc_lower])
    # Also check tags if present
    return found


def rank_jobs_for_profile(jobs: list[dict], user_profile: dict) -> list[dict]:
    """
    Score and rank jobs against a user profile.

    Scoring:
      - Skill + tag overlap:  40%
      - Location match:       20%
      - Experience fit:       15%
      - Salary overlap:       15%
      - Recency:              10%
    """
    user_skills    = set(s.strip().lower() for s in (user_profile.get("skills") or "").split(",") if s.strip())
    pref_locations = [l.strip().lower() for l in (user_profile.get("preferred_locations") or "").split(",") if l.strip()]
    exp_level      = (user_profile.get("experience_level") or "").lower()
    salary_min     = user_profile.get("salary_min") or 0
    salary_max     = user_profile.get("salary_max") or 999999999
    pref_roles     = [r.strip().lower() for r in (user_profile.get("preferred_roles") or "").split(",") if r.strip()]

    EXP_KEYWORDS = {
        "fresher":  ["intern", "entry", "junior", "fresher", "graduate", "trainee"],
        "junior":   ["junior", "entry", "associate", "1-2", "0-2", "fresher"],
        "mid":      ["mid", "3-5", "2-5", "intermediate"],
        "senior":   ["senior", "lead", "principal", "staff", "5+", "7+", "10+"],
        "lead":     ["lead", "principal", "director", "head", "vp", "manager", "architect"],
    }

    for job in jobs:
        score       = 0
        reasons     = []
        desc_lower  = job["description"].lower()
        title_lower = job["title"].lower()

        # ── Skill + tag overlap (40%) ──
        job_skills = set(extract_skills_from_description(job["description"]))
        job_tags   = set(job.get("tags") or [])
        combined   = job_skills | job_tags

        if user_skills and combined:
            overlap  = user_skills & combined
            skill_sc = len(overlap) / max(len(combined), 1)
            score   += skill_sc * 40
            if overlap:
                reasons.append(f"Skills match: {', '.join(sorted(overlap)[:4])}")
        elif not user_skills:
            score += 20

        # ── Location match (20%) ──
        loc_lower = job["location"].lower()
        if job["is_remote"] and any(r in pref_locations for r in ["remote", "wfh", "work from home"]):
            score += 20
            reasons.append("Remote — matches your preference")
        elif pref_locations:
            for pl in pref_locations:
                if pl in loc_lower:
                    score += 20
                    reasons.append(f"Location: {job['location'][:30]}")
                    break
        elif not pref_locations:
            score += 10

        # ── Experience fit (15%) ──
        if exp_level and exp_level in EXP_KEYWORDS:
            keywords = EXP_KEYWORDS[exp_level]
            if any(kw in title_lower or kw in desc_lower for kw in keywords):
                score += 15
                reasons.append(f"Level: fits {exp_level}")
            else:
                score += 5

        # ── Salary overlap (15%) ──
        if job["salary_min"] and job["salary_max"]:
            if salary_min <= job["salary_max"] and salary_max >= job["salary_min"]:
                score += 15
                reasons.append(f"Salary in range: {job['salary']}")
            else:
                score += 2
        elif not job["salary_min"]:
            score += 8

        # ── Recency (10%) ──
        posted = job.get("posted_at", "")
        if "Today" in posted or "Yesterday" in posted:
            score += 10
            reasons.append("Just posted!")
        elif "days ago" in posted:
            score += 7
        elif "week" in posted:
            score += 4
        else:
            score += 2

        # ── Role title bonus ──
        if pref_roles:
            for pr in pref_roles:
                if pr in title_lower:
                    score = min(score + 5, 100)
                    reasons.append(f"Role: {pr.title()}")
                    break

        job["match_score"]   = min(int(score), 100)
        job["match_reasons"] = reasons

    jobs.sort(key=lambda x: x["match_score"], reverse=True)
    return jobs
