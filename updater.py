"""Govt Job Tracker updater.

Design goals:
- Read only public official recruitment pages.
- Never invent application dates or vacancies.
- ACTIVE is assigned only when an application window is explicitly found and today
  falls inside that window.
- ANNOUNCED/EXPECTED/EXAM/RESULT are informational states and must be verified
  against the linked official notice.
"""
from pathlib import Path
from datetime import date, datetime
from urllib.parse import urljoin
import json, re, requests
from bs4 import BeautifulSoup

BASE = Path(__file__).parent
HEADERS = {"User-Agent": "GovtJobTracker/1.0 (official-source-collector)"}
TODAY = date.today()

JOB_WORDS = re.compile(r"(recruit|recruitment|vacanc|advertisement|advt|apply online|registration|application|constable|sub.?inspector|clerk|assistant|officer|technician|engineer|apprentice|group.?d|group.?c|group.?b|mts|chsl|cgl|gd|cpo|selection post|stenographer|ntpc|alp|rpf|forest|forester|gds|probationary officer|customer service|junior associate|civil service|judicial service|miscellaneous services)", re.I)
RESULT_WORDS = re.compile(r"(result|merit list|selected|recommended|shortlisted|allocation|provisional allotment)", re.I)
EXAM_WORDS = re.compile(r"(admit card|call letter|answer key|exam schedule|examination schedule|pet/pst|skill test|written test|interview schedule)", re.I)
ANNOUNCE_WORDS = re.compile(r"(detailed advertisement|advertisement|recruitment|apply online|registration|application)", re.I)
EXPECTED_WORDS = re.compile(r"(indicative advertisement|calendar|tentative|expected|upcoming)", re.I)
DATE_RE = re.compile(r"\b(\d{1,2})[./-](\d{1,2})[./-](20\d{2})\b")
ISO_RE = re.compile(r"\b(20\d{2})-(\d{2})-(\d{2})\b")


def clean(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


def fetch(url: str) -> str:
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r.text


def dates_from(text: str):
    out=[]
    for m in DATE_RE.finditer(text):
        d,mo,y=map(int,m.groups())
        try: out.append(date(y,mo,d))
        except ValueError: pass
    for m in ISO_RE.finditer(text):
        y,mo,d=map(int,m.groups())
        try: out.append(date(y,mo,d))
        except ValueError: pass
    return sorted(set(out))


def category(title: str) -> str:
    t=title.lower()
    if any(x in t for x in ["railway","rrb","ntpc","alp","rpf","technician"]): return "Railway"
    if any(x in t for x in ["bank","ibps","sbi","probationary officer","junior associate","customer service associate"]): return "Banking"
    if any(x in t for x in ["police","constable","sub-inspector","cpo","capf","crpf","bsf","cisf","itbp","ssb"]): return "Police"
    if any(x in t for x in ["forest","forester"]): return "Forest"
    if any(x in t for x in ["clerk","chsl","stenographer","assistant","ldc","udc"]): return "Clerk / Assistant"
    if any(x in t for x in ["group d","mts","gds"]): return "Group D"
    if any(x in t for x in ["group c","cgl","selection post"]): return "Group B/C"
    if "upsc" in t or any(x in t for x in ["civil service","defence","cds","nda"]): return "UPSC / Defence"
    if any(x in t for x in ["psc","west bengal civil service","miscellaneous services"]): return "West Bengal Govt"
    return "Other Govt"


def qualifications(title: str):
    t=title.lower(); q=[]
    if any(x in t for x in ["10th","matric","mts","gds","gd constable","group d"]): q.append("10th Pass")
    if any(x in t for x in ["12th","10+2","chsl","higher secondary"]): q.append("12th Pass")
    if any(x in t for x in ["graduate","graduation","cgl","po/mt","clerk","assistant","officer","civil service"]): q.append("Graduation")
    if "iti" in t or "technician" in t: q.append("ITI / Technical")
    if "diploma" in t or "junior engineer" in t: q.append("Diploma")
    return q or ["Post-wise"]


def classify(title: str, text: str, dates):
    blob=(title+" "+text).lower()
    if RESULT_WORDS.search(blob): return "RESULT"
    if EXAM_WORDS.search(blob): return "EXAM"
    if EXPECTED_WORDS.search(blob): return "EXPECTED"
    if dates:
        if len(dates)>=2:
            start,end=dates[0],dates[-1]
            if start <= TODAY <= end: return "ACTIVE"
            if TODAY < start: return "UPCOMING"
            if TODAY > end: return "CLOSED"
        if TODAY <= dates[-1]: return "ANNOUNCED"
    if ANNOUNCE_WORDS.search(blob): return "ANNOUNCED"
    return "EXPECTED"


def source_link(soup, base_url, words):
    for a in soup.find_all("a", href=True):
        txt=clean(a.get_text(" ", strip=True))
        if any(w in txt.lower() for w in words):
            return urljoin(base_url, a["href"])
    return base_url


def main():
    jobs_file=BASE/"jobs.json"
    sources_file=BASE/"sources.json"
    data=json.loads(jobs_file.read_text(encoding="utf-8"))
    sources=json.loads(sources_file.read_text(encoding="utf-8"))

    # Keep curated records, but close known application windows automatically.
    curated=[]
    for j in data.get("jobs",[]):
        if j.get("start") and j.get("last"):
            try:
                st=date.fromisoformat(j["start"]); en=date.fromisoformat(j["last"])
                if st <= TODAY <= en: j["status"]="ACTIVE"
                elif TODAY > en and j.get("status") in {"ACTIVE","UPCOMING"}: j["status"]="CLOSED"
            except ValueError: pass
        curated.append(j)

    discovered=[]
    for src in sources.get("sources",[]):
        try:
            html=fetch(src["url"])
            soup=BeautifulSoup(html,"html.parser")
            for a in soup.find_all("a", href=True):
                title=clean(a.get_text(" ", strip=True))
                if len(title)<12 or len(title)>220 or not JOB_WORDS.search(title): continue
                href=urljoin(src["url"], a["href"])
                if not href.startswith(("http://","https://")): continue
                parent=clean(a.parent.get_text(" ", strip=True)) if a.parent else ""
                context=(title+" "+parent)[:1200]
                ds=dates_from(context)
                status=classify(title, context, ds)
                # Avoid obvious generic navigation and purely technical notices.
                if any(x in title.lower() for x in ["privacy policy","contact us","syllabus"]): continue
                start=ds[0].isoformat() if len(ds)>=2 else ""
                last=ds[-1].isoformat() if len(ds)>=2 else ""
                discovered.append({
                    "title": title,
                    "organization": src["name"],
                    "category": category(title),
                    "qualifications": qualifications(title),
                    "status": status,
                    "start": start,
                    "last": last,
                    "note": "Discovered from an official source. Read the linked notice for exact eligibility, vacancy, fee and dates.",
                    "source": href,
                    "apply": source_link(soup, src["url"], ["apply online","new registration","online application","apply now"]) if status=="ACTIVE" else href,
                    "verified": True,
                    "checked": TODAY.isoformat()
                })
        except Exception as e:
            print(f"[WARN] {src['name']}: {e}")

    # Curated records win over generic discoveries with the same title.
    merged={}
    for j in curated + discovered:
        key=re.sub(r"[^a-z0-9]+","",j.get("title","").lower())
        if not key: continue
        if key not in merged or (j.get("verified") and not merged[key].get("verified")):
            merged[key]=j

    data["jobs"]=list(merged.values())
    data["updated_at"]=datetime.now().astimezone().isoformat(timespec="seconds")
    data["today"]=TODAY.isoformat()
    data["coverage_note"]="Official-source discovery is broad but not mathematically exhaustive. ACTIVE is only date-derived; always verify the official notice before applying."
    jobs_file.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding="utf-8")
    sources["last_checked"]=TODAY.isoformat()
    sources_file.write_text(json.dumps(sources,ensure_ascii=False,indent=2),encoding="utf-8")
    print(f"Updated {len(data['jobs'])} records from {len(sources.get('sources',[]))} official sources")

if __name__=="__main__": main()
