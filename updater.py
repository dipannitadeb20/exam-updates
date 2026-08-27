"""
Automatic official-source collector for Govt Job Tracker.

Safety rule:
- Existing ACTIVE records are automatically closed after their known last date.
- New discoveries from official pages are added as EXPECTED, never ACTIVE.
- ACTIVE/ANNOUNCED status should only be assigned from a verified official
  application/notification parser.
"""

from pathlib import Path
from datetime import date, datetime
import json, re, hashlib
import requests
from bs4 import BeautifulSoup

BASE=Path(__file__).parent
UA="GovtJobTracker/1.0 (+https://github.com/)"
HEADERS={"User-Agent":UA,"Accept-Language":"en-IN,en;q=0.9"}

KEYWORDS=re.compile(
    r"(recruit|recruitment|vacan|notification|advertisement|advt|"
    r"constable|sub[- ]?inspector|clerk|assistant|group[- ]?[bc d]|"
    r"technician|alp|ntpc|mts|chsl|cgl|gd|cpo|po/mt|customer service|"
    r"office assistant|officer|forest guard|forester|gds|apprentice|"
    r"stenographer|selection post|engineer|junior associate)",
    re.I
)

def get(url):
    r=requests.get(url,headers=HEADERS,timeout=25,allow_redirects=True)
    r.raise_for_status()
    return r.text

def clean(s):
    return re.sub(r"\s+"," ",s or "").strip()

def guess_category(title):
    t=title.lower()
    if any(x in t for x in ["railway","rrb","ntpc","alp","rpf"]): return "Railway"
    if any(x in t for x in ["bank","ibps","sbi","customer service associate","po/mt"]): return "Banking"
    if any(x in t for x in ["police","constable","cpo","sub-inspector","capf","cisf","crpf","bsf","itbp","ssb"]): return "Police"
    if any(x in t for x in ["forest","forester"]): return "Forest"
    if any(x in t for x in ["clerk","stenographer","chsl","assistant","ldc","jsa","udc"]): return "Clerk"
    if "group d" in t or "mts" in t: return "Group D"
    if "group c" in t or "cgl" in t: return "Group B/C"
    if "post" in t or "gds" in t: return "Post"
    if any(x in t for x in ["defence","army","navy","air force"]): return "Defence"
    if "upsc" in t: return "UPSC"
    return "Other Govt"

def guess_quals(title):
    t=title.lower()
    q=[]
    if "10th" in t or "matric" in t or "mts" in t or "gds" in t: q.append("10th Pass")
    if "12th" in t or "chsl" in t or "stenographer" in t or "ntpc undergraduate" in t: q.append("12th Pass")
    if "graduate" in t or "graduation" in t or "cgl" in t or "po/mt" in t or "clerk" in t or "customer service associate" in t: q.append("Graduation")
    if "iti" in t: q.append("ITI")
    if "diploma" in t: q.append("Diploma")
    return q or ["Post-wise"]

def main():
    jobs_path=BASE/"jobs.json"
    sources_path=BASE/"sources.json"
    jobs=json.loads(jobs_path.read_text(encoding="utf-8"))
    sources=json.loads(sources_path.read_text(encoding="utf-8"))
    by_key={j.get("title","").strip().lower():j for j in jobs["jobs"]}

    # Date maintenance for known records.
    today=date.today()
    for j in jobs["jobs"]:
        last=j.get("last","")
        if j.get("status")=="ACTIVE" and re.fullmatch(r"\d{4}-\d{2}-\d{2}",last or ""):
            if date.fromisoformat(last) < today:
                j["status"]="CLOSED"

    # Discover recruitment-like links from official pages.
    for src in sources["sources"]:
        url=src["url"]
        try:
            html=get(url)
            soup=BeautifulSoup(html,"html.parser")
            seen=set()
            for a in soup.find_all("a",href=True):
                title=clean(a.get_text(" ",strip=True))
                href=a["href"].strip()
                if not title or len(title)<8 or not KEYWORDS.search(title):
                    continue
                if href.startswith("/"):
                    from urllib.parse import urljoin
                    href=urljoin(url,href)
                if not href.startswith(("http://","https://")) or href in seen:
                    continue
                seen.add(href)
                key=title.lower()
                if key in by_key:
                    continue
                # New discovery is deliberately EXPECTED until a source-specific
                # parser confirms application/notification semantics.
                by_key[key]={
                    "title":title[:180],
                    "organization":src["name"],
                    "category":guess_category(title),
                    "qualifications":guess_quals(title),
                    "status":"EXPECTED",
                    "start":"",
                    "last":"",
                    "note":"Automatically discovered on an official recruitment source. Verify the linked notice before applying.",
                    "source":href,
                    "apply":href
                }
        except Exception as e:
            print(f"[WARN] {src['name']}: {e}")

    jobs["jobs"]=list(by_key.values())
    jobs["updated_at"]=datetime.now().astimezone().isoformat(timespec="seconds")
    jobs_path.write_text(json.dumps(jobs,ensure_ascii=False,indent=2),encoding="utf-8")
    print(f"Tracked records: {len(jobs['jobs'])}")

if __name__=="__main__":
    main()
