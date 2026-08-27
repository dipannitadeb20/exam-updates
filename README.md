# Govt Job Tracker — Live-ready

This project separates the public website from the update engine.

## Run locally
1. Install Python 3.10+.
2. Run `python updater.py`.
3. Open `index.html` in a browser, or serve the folder with:
   `python -m http.server 8000`
4. Visit `http://localhost:8000`.

## Automatic updates
`updater.py` is a safe starter updater. It checks the configured official sources and keeps a local `jobs.json`. Because government portals differ (HTML, PDFs, notices, anti-bot rules), each source should have its own parser and should only publish verified fields.

For real 24/7 automatic updates, deploy the updater on a server/cron (for example once every hour) and add source-specific parsers. Never mark a job ACTIVE from an unofficial rumor.

## Status rules
ACTIVE = application window is open
ANNOUNCED = official notification exists; dates/application state shown from official notice
EXPECTED = likely/tentative release window from official calendar/verified schedule; not confirmed
UPCOMING = officially scheduled future recruitment
EXAM = application closed, exam/admit card stage
RESULT = result/answer key stage
CLOSED = recruitment cycle finished

Always verify the official notice before applying.


## GitHub automatic mode

The included `.github/workflows/auto-update.yml`:
- runs on every push to `main`;
- runs automatically once per hour;
- checks the official sources in `sources.json`;
- updates known records by their last date;
- discovers new recruitment-like links and adds them as `EXPECTED`;
- deploys the updated site to GitHub Pages.

GitHub Actions schedules can be delayed under load. The collector intentionally does not
promote a newly discovered link to ACTIVE: that requires a source-specific verified parser
because a recruitment page can be an old notice, result, corrigendum, or admit-card notice.

To enable the site:
1. Create a GitHub repository and upload the contents of this folder to `main`.
2. Repository → Settings → Pages → Source → GitHub Actions.
3. Open Actions → "Govt Job Tracker — Auto Update & Deploy" → Run workflow once.
4. The site will then publish at the GitHub Pages URL shown by GitHub.

To expand coverage, add official recruitment source URLs to `sources.json`. For highly
structured sources, add a dedicated parser to `updater.py` that extracts notification date,
application start/end, vacancy, qualification and official apply URL.
