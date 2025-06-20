from flask import Flask, request, jsonify
from flask_cors import CORS
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
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
    options.add_argument('--single-process')
    options.add_argument('--disable-extensions')
    options.add_argument('--disable-dev-tools')
    options.add_argument('--disable-browser-side-navigation')

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    wait = WebDriverWait(driver, 20)
    actions = ActionChains(driver)
    scrape_jobs[job_id] = {"status": "in_progress", "content": [], "logs": []}

    try:
        driver.get(url)
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
        scrape_jobs[job_id]["logs"].append(f"Loaded page and found elements matching '{selector}'.")

        links = driver.find_elements(By.CSS_SELECTOR, selector)
        scrape_jobs[job_id]["logs"].append(f"Initially found {len(links)} clickable links with selector '{selector}'.")

        scraped = 0
        for idx, link in enumerate(links):
            if scraped >= depth:
                break

            href = link.get_attribute('href')
            link_text = link.text or href or f"Link {idx+1}"
            scrape_jobs[job_id]["logs"].append(f"Preparing to visit: '{link_text}'")

            if not href or "javascript:void(0)" in href:
                scrape_jobs[job_id]["logs"].append(f"Skipping non-navigable or empty link: '{link_text}'")
                continue

            driver.get(href)
            wait.until(lambda d: d.execute_script('return document.readyState') == 'complete')
            time.sleep(5)  # Give extra time for heavy JS rendering

            page_content = {
                "title": driver.title,
                "url": driver.current_url,
                "summary": driver.find_element(By.TAG_NAME, 'body').text[:2000]
            }

            scrape_jobs[job_id]["content"].append(page_content)
            scrape_jobs[job_id]["logs"].append(f"Scraped content from '{link_text}'.")
            scraped += 1

            driver.get(url)
            wait.until(lambda d: d.execute_script('return document.readyState') == 'complete')
            time.sleep(5)

        scrape_jobs[job_id]["status"] = "completed"

    except Exception as e:
        scrape_jobs[job_id]["status"] = "error"
        scrape_jobs[job_id]["error"] = str(e)
        scrape_jobs[job_id]["logs"].append(f"Error occurred: {str(e)}")

    finally:
        scrape_jobs[job_id]["logs"].append("Browser session ended.")
        driver.quit()

@app.route('/scrape', methods=['POST'])
def start_scrape():
    data = request.json
    job_id = str(uuid.uuid4())
    url = data.get('url')
    selector = data.get('navigation_selector', '#sidebar a')
    max_depth = data.get('max_depth', 2)

    threading.Thread(target=scrape_navigation, args=(job_id, url, selector, max_depth)).start()

    return jsonify({"job_id": job_id, "status": "started"})

@app.route('/status/<job_id>', methods=['GET'])
def check_status(job_id):
    job = scrape_jobs.get(job_id)
    if not job:
        return jsonify({"error": "job not found"}), 404
    return jsonify({
        "job_id": job_id,
        "status": job["status"],
        "logs": job["logs"],
        "error": job.get("error", "")
    })

@app.route('/download/<job_id>', methods=['GET'])
def download_results(job_id):
    job = scrape_jobs.get(job_id)
    if not job or job["status"] != "completed":
        return jsonify({"error": "job not ready or not found"}), 404
    return jsonify(job["content"])

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=10000)
