from flask import Flask, request, jsonify
from flask_cors import CORS
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
import threading
import uuid
import time

app = Flask(__name__)
CORS(app)

scrape_jobs = {}

COMMON_SELECTORS = ['#sidebar a', '.sidebar a', '.navigation a', 'nav a', 'main a', 'a']

def best_selector(driver):
    best_sel = 'a'
    max_links = 0
    for sel in COMMON_SELECTORS:
        links = driver.find_elements(By.CSS_SELECTOR, sel)
        valid_links = [link for link in links if link.get_attribute('href')]
        if len(valid_links) > max_links:
            best_sel = sel
            max_links = len(valid_links)
    return best_sel

def scrape_navigation(job_id, url, depth):
    scrape_jobs[job_id] = {"status": "in_progress", "content": [], "logs": []}

    options = Options()
    options.add_argument('--headless=new')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.page_load_strategy = 'eager'

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    try:
        driver.get(url)
        time.sleep(8)

        selector = best_selector(driver)
        links = driver.find_elements(By.CSS_SELECTOR, selector)
        valid_links = [link for link in links if link.get_attribute('href')]
        scrape_jobs[job_id]["logs"].append(f"Auto-selected '{selector}' with {len(valid_links)} valid links.")

        scraped = 0
        for link in valid_links:
            if scraped >= depth:
                break

            href = link.get_attribute('href')
            scrape_jobs[job_id]["logs"].append(f"Visiting: {href}")
            driver.get(href)
            time.sleep(5)

            content = {
                "title": driver.title,
                "url": driver.current_url,
                "summary": driver.find_element(By.TAG_NAME, 'body').text[:1500]
            }
            scrape_jobs[job_id]["content"].append(content)
            scraped += 1

            driver.get(url)
            time.sleep(5)

        scrape_jobs[job_id]["status"] = "completed"
        scrape_jobs[job_id]["logs"].append("Scraping completed successfully.")

    except Exception as e:
        scrape_jobs[job_id]["status"] = "error"
        scrape_jobs[job_id]["error"] = str(e)
        scrape_jobs[job_id]["logs"].append(f"Error: {str(e)}")

    finally:
        driver.quit()
        scrape_jobs[job_id]["logs"].append("Browser session closed.")

@app.route('/scrape', methods=['POST'])
def start_scrape():
    data = request.json
    job_id = str(uuid.uuid4())
    threading.Thread(
        target=scrape_navigation,
        args=(
            job_id,
            data.get('url'),
            data.get('max_depth', 1)
        )
    ).start()

    return jsonify({"job_id": job_id, "status": "started"})

@app.route('/status/<job_id>', methods=['GET'])
def check_status(job_id):
    job = scrape_jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    return jsonify(job)

@app.route('/download/<job_id>', methods=['GET'])
def download_results(job_id):
    job = scrape_jobs.get(job_id)
    if not job or job["status"] != "completed":
        return jsonify({"error": "Job not ready or not found"}), 404
    return jsonify(job["content"])

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=10000)
