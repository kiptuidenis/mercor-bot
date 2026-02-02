import os
import json
import logging
import smtplib
import smtplib
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from bs4 import BeautifulSoup
from dataclasses import dataclass
from typing import List, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Constants
HISTORY_FILE = 'data/job_history.json'
MERCOR_URL = 'https://mercor.com'

@dataclass
class Job:
    id: str
    title: str
    url: str
    description: str = ""

def load_history() -> List[str]:
    """Load the list of previously seen job IDs."""
    if not os.path.exists(HISTORY_FILE):
        return []
    try:
        with open(HISTORY_FILE, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        logger.error(f"Error loading history: {e}")
        return []

def save_history(history: List[str]):
    """Save the updated list of job IDs."""
    os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
    with open(HISTORY_FILE, 'w') as f:
        json.dump(history, f, indent=2)

from playwright.sync_api import sync_playwright

def fetch_latest_jobs() -> List[Job]:
    """Scrape the 'Latest roles' from the Mercor app or 'Explore' page using Playwright."""
    jobs = []
    try:
        with sync_playwright() as p:
            # Run visible for debugging & ensuring assets load (sometimes headless is blocked)
            browser = p.chromium.launch(headless=False) 
            
            context = browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                viewport={'width': 1366, 'height': 768}
            )
            page = context.new_page()
            
            logger.info(f"Navigating to {MERCOR_URL}...")
            # Use the explore URL clearly
            explore_url = "https://work.mercor.com/explore"
            page.goto(explore_url, timeout=60000)
            
            # Wait for any network activity to settle
            try:
                page.wait_for_load_state("networkidle", timeout=10000)
            except:
                pass # Continue even if network is busy
            
            # Check if redirected to login
            if "/login" in page.url or "auth-wall" in page.url:
                logger.error(f"Redirected to login/auth page: {page.url}. Cannot scrape public jobs.")
                browser.close()
                return []
            
            logger.info("Checking for job cards...")
            # Wait for *any* link that might be a job, or at least the container
            try:
                # Based on user report, links contain 'jobs/list_'
                page.wait_for_selector('a[href*="jobs/list_"]', timeout=30000)
            except Exception as e:
                logger.warning(f"Timeout waiting for job selector on {page.url}. Page title: {page.title()}")
                # Dump content snippet to log for debugging
                content_snippet = page.content()[:500]
                logger.debug(f"Page content snippet: {content_snippet}")
                
            # Pagination Loop
            max_pages = 5
            current_page = 1
            
            while current_page <= max_pages:
                logger.info(f"Scraping page {current_page}...")
                
                # Parse current page
                content = page.content()
                soup = BeautifulSoup(content, 'html.parser')
                
                found_on_page = 0
                for link in soup.find_all('a', href=True):
                    href = link['href']
                    if 'jobs/list_' in href:
                        job_id = href.split('list_')[-1]
                        title = link.get_text(strip=True)
                        
                        if href.startswith('/'):
                            href = f"https://work.mercor.com{href}"
                        elif href.startswith('jobs/'):
                             href = f"https://work.mercor.com/{href}"
    
                        if len(title) > 100:
                            title = title[:100] + "..."
                        
                        if title:
                            jobs.append(Job(id=job_id, title=title, url=href))
                            found_on_page += 1
                
                logger.info(f"Found {found_on_page} jobs on page {current_page}.")
                
                # Check for "Next" button
                # Selector based on inspection: button with title="Next" or text "›"
                try:
                    next_button = page.locator('button[title="Next"]')
                    if next_button.is_visible() and next_button.is_enabled():
                        logger.info("Clicking Next page...")
                        next_button.click()
                        page.wait_for_load_state("networkidle")
                        # Add a small sleep to ensure React hydration
                        page.wait_for_timeout(2000) 
                        current_page += 1
                    else:
                        logger.info("No more pages (Next button not found/disabled).")
                        break
                except Exception as e:
                    logger.warning(f"Pagination error: {e}")
                    break
            
            browser.close()
        
        # Deduplicate
        unique_jobs = {job.id: job for job in jobs}.values()
        return list(unique_jobs)
        
    except Exception as e:
        logger.error(f"Failed to fetch jobs with Playwright: {e}")
        return []

def get_job_details(job: Job) -> Job:
    """Fetch specific details for a job using Playwright."""
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                 user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                 viewport={'width': 1280, 'height': 800}
            )
            page = context.new_page()
            
            logger.info(f"Fetching details for {job.url}...")
            page.goto(job.url, timeout=30000)
            
            # Wait for description content - heuristic selector
            # Usually generic divs or p tags. We just wait for body to settle.
            page.wait_for_load_state("networkidle")
            
            content = page.content()
            soup = BeautifulSoup(content, 'html.parser')
            
            # Extract description
            text_content = soup.get_text(separator=' ', strip=True)
            job.description = text_content
            
            browser.close()
        return job
        
    except Exception as e:
        logger.error(f"Failed to get details for {job.url}: {e}")
        return job

def analyze_job(job: Job) -> bool:
    """Use Gemini to determine if the job matches criteria."""
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        logger.warning("GEMINI_API_KEY not set. Skipping analysis.")
        return False
        
    try:
        from google import genai
    except ImportError:
        logger.error("google-genai module not found. Install it with: pip install google-genai")
        return False

    client = genai.Client(api_key=api_key)
    
    prompt = f"""
    Analyze the following job description to see if it matches these strict criteria:
    
    CRITERIA:
    1. Role Type: Must be a Generalist OR General Annotation/Data Labeling role.
       - It should be suitable for a recent graduate or undergraduate.
       - It MUST NOT require specialized advanced degrees (like MD, PhD, JD) unless acceptable for a fresh grad.
       - It MUST NOT require 5+ years of specialized experience.
    2. Language: Must be English or Swahili only. No other foreign languages.
    3. Location: Remote, US-based, or Worldwide.
    
    Return ONLY a JSON object: {{"match": boolean, "reason": "short explanation"}}
    
    JOB TITLE: {job.title}
    JOB DESCRIPTION:
    {job.description[:10000]}  # Truncate to avoid token limits
    """
    
    try:
        response = client.models.generate_content(
            model='gemini-1.5-flash',
            contents=prompt
        )
        
        # Clean response text to ensure it's valid JSON
        text = response.text.strip()
        if text.startswith('```json'):
            text = text[7:]
        if text.endswith('```'):
            text = text[:-3]
        text = text.strip()
            
        result = json.loads(text)
        
        if result.get('match'):
            logger.info(f"MATCH found: {job.title} - {result.get('reason')}")
            return True
        else:
            logger.info(f"No match: {job.title} - {result.get('reason')}")
            return False
            
    except Exception as e:
        logger.error(f"Gemini analysis failed: {e}")
        return False

def send_email(matches: List[Job]):
    """Send an email with the list of matching jobs."""
    sender_email = os.getenv('SMTP_EMAIL')
    sender_password = os.getenv('SMTP_PASSWORD')
    receiver_email = os.getenv('RECEIVER_EMAIL')
    smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
    smtp_port = int(os.getenv('SMTP_PORT', '587'))
    
    if not (sender_email and sender_password and receiver_email):
        logger.warning("SMTP credentials not set. Skipping email.")
        return

    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = receiver_email
    msg['Subject'] = f"New Mercor Job Matches ({len(matches)})"
    
    body = "<h2>New Job Matches Found</h2><ul>"
    for job in matches:
        body += f"<li><a href='{job.url}'><b>{job.title}</b></a></li>"
    body += "</ul>"
    
    msg.attach(MIMEText(body, 'html'))
    
    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(msg)
        logger.info(f"Email sent to {receiver_email}")
    except Exception as e:
        logger.error(f"Failed to send email: {e}")

def main():
    logger.info("Starting Mercor Job Bot")
    
    history = load_history()
    all_jobs = fetch_latest_jobs()
    
    new_jobs = [j for j in all_jobs if j.id not in history]
    logger.info(f"Found {len(new_jobs)} new jobs to analyze")
    
    matches = []
    processed_ids = []
    
    for job in new_jobs:
        job = get_job_details(job)
        if analyze_job(job):
            matches.append(job)
        processed_ids.append(job.id)
        
    if matches:
        send_email(matches)
    else:
        logger.info("No matches found matching criteria.")
        
    # Update history
    save_history(history + processed_ids)
    logger.info("Bot execution complete")

if __name__ == "__main__":
    main()
