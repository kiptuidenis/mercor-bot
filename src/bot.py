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

def fetch_latest_jobs() -> List[Job]:
    """Scrape the 'Latest roles' from the Mercor homepage."""
    try:
        response = requests.get(MERCOR_URL, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        jobs = []
        # Find all links that look like job details
        # Based on previous research: https://work.mercor.com/jobs/list_...
        for link in soup.find_all('a', href=True):
            href = link['href']
            if 'work.mercor.com/jobs/list_' in href:
                job_id = href.split('list_')[-1]
                # Basic title extraction (might need refinement based on exact DOM)
                # Usually the link contains the title or it's nested
                title = link.get_text(strip=True)
                
                # Cleanup title if it's too long or messy
                if len(title) > 100:
                    title = title[:100] + "..."
                
                jobs.append(Job(id=job_id, title=title, url=href))
        
        # Deduplicate by ID
        unique_jobs = {job.id: job for job in jobs}.values()
        return list(unique_jobs)
        
    except Exception as e:
        logger.error(f"Failed to fetch jobs: {e}")
        return []

def get_job_details(job: Job) -> Job:
    """Fetch specific details for a job."""
    try:
        response = requests.get(job.url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract description - attempting to capture the main content
        # This is a heuristic; actual site structure might vary
        text_content = soup.get_text(separator=' ', strip=True)
        job.description = text_content
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
