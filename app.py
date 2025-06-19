from flask import Flask, request, jsonify
from flask_cors import CORS
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
import uuid
import threading
from urllib.parse import urljoin, urlparse
import time
import re

app = Flask(__name__)
CORS(app)

jobs = {}

def clean_text(text):
    return re.sub(r'\s+', ' ', text).strip()

def summarize_content(text):
    # Basic summarization: extract first 3 sentences
    sentences = re.split(r'(?<=[.!?]) +', text)
    summary = ' '.join(sentences[:3])
    return summary

def scrape_navigation(job_id, base_url, navigation_selector, max_depth=2):
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    visited = set()
    summarized_results = []

    def scrape_recursive(url, depth):
        if depth > max_depth or url in visited:
            return
        visited.add(url)
        try:
            driver.get(url)
            time.sleep(2)  # Ensure JS loaded
            title = driver.title
            body_text = driver.find_element(By.TAG_NAME, "body").text
            clean_body_text = clean_text(body_text)
            summary = summarize_content(clean_body_text)

            summarized_results.append({
                'url': url,
                'title': title,
                'summary': summary
            })

            nav_elements = driver.find_elements(By.CSS_SELECTOR, f"{navigation_selector} a[href]")
            nav_links = [
                urljoin(base_url, a.get_attribute('href'))
                for a in nav_elements
                if urlparse(urljoin(base_url, a.get_attribute('href'))).netloc == urlparse(base_url).netloc
            ]

            for link in nav_links:
                if link not in visited:
                    scrape_recursive(link, depth + 1)

        except Exception as e:
            jobs[job_id]['errors'].append(str(e))

    scrape_recursive(base_url, 1)
    driver.quit()

    jobs[job_id]['status'] = 'completed'
    jobs[job_id]['result'] = summarized_results

@app.route("/")
def home():
    return "Documentation scraper with summarization is online!"

@app.route("/scrape", methods=["POST"])
def scrape():
    data = request.json
    url = data.get("url")
    navigation_selector = data.get("navigation_selector", "nav")
    max_depth = data.get("max_depth", 2)

    if not url:
        return jsonify({"error": "URL is required"}), 400

    job_id = str(uuid.uuid4())
    jobs[job_id] = {"status": "in_progress", "result": None, "errors": []}

    thread = threading.Thread(target=scrape_navigation, args=(job_id, url, navigation_selector, max_depth))
    thread.start()

    return jsonify({"job_id": job_id, "status": "started"})

@app.route("/status/<job_id>", methods=["GET"])
def status(job_id):
    job = jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    return jsonify({"job_id": job_id, "status": job["status"], "errors": job["errors"]})

@app.route("/download/<job_id>", methods=["GET"])
def download(job_id):
    job = jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    if job["status"] != "completed":
        return jsonify({"error": "Job not completed yet"}), 400
    return jsonify(job["result"])

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "healthy"}), 200

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=10000)
