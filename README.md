# Mercor Bot

An automated job discovery, AI evaluation, and notification system for the Mercor job platform. The bot scrapes available listings from Mercor, parses job descriptions, evaluates candidate fit using Google Gemini, and sends automated email notifications for matching positions while maintaining a history to prevent duplicate alerts.

---

## Features

- **Automated Web Scraping**: Uses Playwright and BeautifulSoup to navigate and paginate through job listings on Mercor (`https://work.mercor.com/explore`), dynamically rendering JavaScript and extracting job details.
- **AI-Powered Evaluation**: Integrates with Google Gemini (`gemini-2.5-flash`) to analyze job descriptions against custom criteria, including role type, experience level, language requirements, and work location.
- **Deduplication and State Management**: Persists processed job IDs to a JSON history file (`data/job_history.json`) to ensure jobs are evaluated and notified only once.
- **Email Notifications**: Generates and dispatches HTML-formatted email alerts via SMTP (e.g., Gmail) containing direct links to matching roles.
- **Continuous Execution via GitHub Actions**: Includes a scheduled workflow that runs every 5 hours, installs dependencies and Playwright browsers, executes the bot, and automatically commits updated history back to the repository.

---

## Architecture Overview

```
+---------------------------+
|  Mercor Job Board Explore |
+-------------+-------------+
              |
              v
+---------------------------+
|    Playwright Scraper     |  --> Extracts Job IDs, Titles, and URLs across pages
+-------------+-------------+
              |
              v
+---------------------------+
|  Deduplication & History  |  --> Filters out previously processed IDs (data/job_history.json)
+-------------+-------------+
              |
              v
+---------------------------+
| Job Details Page Fetcher  |  --> Extracts full job description content
+-------------+-------------+
              |
              v
+---------------------------+
|   Google Gemini Analysis  |  --> Evaluates role fit against criteria (gemini-2.5-flash)
+-------------+-------------+
              |
              +--------------------------+
              |                          |
              v                          v
+---------------------------+  +---------------------------+
|     SMTP Email Alert      |  |   Save Updated History    |
| (If matching roles found) |  |   (data/job_history.json) |
+---------------------------+  +---------------------------+
```

---

## Project Structure

```
mercor-bot/
|-- .github/
|   `-- workflows/
|       `-- daily_bot.yml         # GitHub Actions cron workflow (every 5 hours)
|-- data/
|   `-- job_history.json          # Persistent record of processed job IDs
|-- src/
|   `-- bot.py                    # Main scraper, AI evaluator, and email dispatcher
|-- tests/                        # Diagnostic and exploratory test scripts
|   |-- check_api_endpoints.py
|   |-- check_pagination.py
|   |-- debug_dom.py
|   |-- inspect_job_details.py
|   |-- list_models.py
|   `-- verify_scraping.py
|-- .gitignore
|-- requirements.txt              # Python dependencies
`-- README.md                     # Project documentation
```

---

## Requirements

- Python 3.10 or higher
- Playwright Chromium browser binary
- Google Gemini API key
- SMTP email credentials (e.g., Gmail App Password)

---

## Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/kiptuidenis/mercor-bot.git
   cd mercor-bot
   ```

2. **Create and activate a virtual environment**:
   - **Linux / macOS**:
     ```bash
     python3 -m venv venv
     source venv/bin/activate
     ```
   - **Windows (PowerShell)**:
     ```powershell
     python -m venv venv
     .\venv\Scripts\Activate.ps1
     ```

3. **Install Python dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Install Playwright browser binaries**:
   ```bash
   playwright install chromium
   ```

---

## Configuration

Create a `.env` file in the root directory with the following variables:

```env
# Gemini API Configuration
GEMINI_API_KEY=your_gemini_api_key_here

# Email Notification Settings
SMTP_EMAIL=your_email@gmail.com
SMTP_PASSWORD=your_app_specific_password
RECEIVER_EMAIL=recipient_email@example.com
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587

# Execution Settings (Optional)
HEADLESS=true
```

> **Note for Gmail users**: If using Gmail for SMTP, generate an **App Password** from your Google Account security settings rather than using your primary account password.

---

## Evaluation Criteria

The bot evaluates each listing in `src/bot.py` using the following criteria:

- **Role Type**: Must be a Generalist or General Annotation / Data Labeling role suitable for recent graduates or undergraduates. It filters out roles requiring specialized advanced degrees (MD, PhD, JD) or 5+ years of specialized experience.
- **Language**: Restricted to English or Swahili.
- **Location**: Remote, US-based, or Worldwide.

To adjust criteria, update the prompt inside the `analyze_job()` function in `src/bot.py`.

---

## Running Locally

To run the bot locally:

```bash
python src/bot.py
```

### Visual Debugging (Headed Mode)

To watch the browser navigate and interact with pages during local execution, set `HEADLESS=false` in your `.env` or run:

```bash
# Windows PowerShell
$env:HEADLESS="false"; python src/bot.py

# Linux / macOS
HEADLESS=false python src/bot.py
```

---

## Automation with GitHub Actions

The workflow located at `.github/workflows/daily_bot.yml` runs automatically every 5 hours and can also be triggered manually from the GitHub Actions tab (`workflow_dispatch`).

### Required GitHub Secrets

Configure the following secrets under **Repository Settings** > **Secrets and variables** > **Actions**:

- `GEMINI_API_KEY`
- `SMTP_EMAIL`
- `SMTP_PASSWORD`
- `RECEIVER_EMAIL`

The workflow automatically installs dependencies, runs the bot in headless mode, and pushes updates to `data/job_history.json` back to the repository using `stefanzweifel/git-auto-commit-action`.

---

## Testing and Utilities

The `tests/` directory contains helper scripts for inspecting page structures and verifying API integrations:

- `verify_scraping.py`: Validates page extraction and job description retrieval.
- `list_models.py`: Lists available Gemini models accessible with your API key.
- `check_pagination.py`: Tests pagination controls on the explore page.
- `inspect_job_details.py`: Inspects DOM elements on individual listing pages.

Run any test script using:

```bash
python tests/verify_scraping.py
```

---

## License

This project is available for personal and educational use.
