# 🇮🇳 Govt Job Tracker

A GitHub Pages government-job tracker for India, with special coverage for West Bengal, SSC, Railway, Banking, Police, Forest, Post, UPSC and state-government recruitment.

## What it does
- Separates **ACTIVE**, **ANNOUNCED**, **EXPECTED/NEXT**, **UPCOMING**, **EXAM**, **RESULT** and **CLOSED**.
- Filters by **10th Pass, 12th Pass, Graduation, ITI/Technical and Diploma**.
- Includes broad categories such as SSC, Railway, Banking, Police, Forest, Group B/C/D, WB Government, Post and UPSC/Defence.
- Links users to the official source/application page.
- Uses a manual GitHub Actions workflow: no hourly schedule.

## Update model
The website's **Update Now** button opens the GitHub Actions workflow. From there click **Run workflow**. GitHub Actions checks the official sources listed in `sources.json`, updates `jobs.json`, and redeploys GitHub Pages.

A public GitHub Pages page must not contain a GitHub access token, so a truly anonymous one-click trigger from the page is intentionally not implemented. The secure flow is: **Update Now → Run workflow → update → deploy**.

## Important accuracy rule
The collector never treats a generic recruitment link as a confirmed open form. `ACTIVE` is assigned only when an explicit date window is detected and today's date falls inside it. `ANNOUNCED` and `EXPECTED` are planning/notice states. Always verify the linked official advertisement for eligibility, vacancy, fee, age limit and dates.

## GitHub setup
1. Put these files in the repository root:
   - `index.html`
   - `jobs.json`
   - `sources.json`
   - `updater.py`
   - `README.md`
   - `.github/workflows/auto-update.yml`
2. Repository → Settings → Pages → Source → **GitHub Actions**.
3. Actions → **Govt Job Tracker — Manual Update** → **Run workflow**.
4. The workflow updates the data and deploys the site.

## Coverage
The source list is deliberately broad, but no public scraper can guarantee every government vacancy in India. Add an official recruitment portal to `sources.json` whenever a new department/board should be covered. Never use unofficial sources as the source of truth for application dates.
