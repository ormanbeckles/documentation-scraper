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

def scrape_navigation(job_id, url, selector, depth):
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    scrape_jobs[job_id] = {"status": "in_progress", "content": [], "logs": []}

    try:
        scrape_jobs[job_id]["logs"].append(f"Opening initial URL: {url}")
        driver.get(url)
        time.sleep(10)

        links = driver.find_elements(By.CSS_SELECTOR, selector)
        scrape_jobs[job_id]["logs"].append(f"Found {len(links)} links using selector '{selector}'.")

        count = 0
        for link in links:
            if depth and count >= depth:
                break

            href = link.get_attribute('href')

            if not href:
                scrape_jobs[job_id]["logs"].append(f"Skipped link without href attribute.")
                continue

            scrape_jobs[job_id]["logs"].append(f"Navigating to link {count + 1}: {href}")
            driver.get(href)
            time.sleep(10)

            page_content = {
                "title": driver.title,
                "url": href,
                "summary": driver.find_element(By.TAG_NAME, 'body').text[:2000]
            }

            scrape_jobs[job_id]["content"].append(page_content)
            count += 1

        scrape_jobs[job_id]["status"] = "completed"

    except Exception as e:
        scrape_jobs[job_id]["status"] = "error"
        scrape_jobs[job_id]["errors"] = str(e)
        scrape_jobs[job_id]["logs"].append(f"Error: {str(e)}")

    finally:
        driver.quit()
        scrape_jobs[job_id]["logs"].append("Browser session ended.")

@app.route('/scrape', methods=['POST'])
def start_scrape():
    data = request.json
    job_id = str(uuid.uuid4())
    url = data.get('url')
    selector = data.get('navigation_selector', 'body a')
    max_depth = data.get('max_depth', 0)

    threading.Thread(target=scrape_navigation, args=(job_id, url, selector, max_depth)).start()

    return jsonify({"job_id": job_id, "status": "started"})

@app.route('/status/<job_id>', methods=['GET'])
def check_status(job_id):
    job = scrape_jobs.get(job_id, None)
    if not job:
        return jsonify({"error": "job not found"}), 404
    return jsonify({"job_id": job_id, "status": job["status"], "logs": job["logs"], "errors": job.get("errors", "")})

@app.route('/download/<job_id>', methods=['GET'])
def download_results(job_id):
    job = scrape_jobs.get(job_id, None)
    if not job or job["status"] != "completed":
        return jsonify({"error": "job not ready or not found"}), 404
    return jsonify(job["content"])

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=10000)
