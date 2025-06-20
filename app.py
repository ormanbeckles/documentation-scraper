from flask import Flask, request, jsonify
from flask_cors import CORS
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import threading
import uuid
import time

app = Flask(__name__)
CORS(app)

jobs = {}

def scrape_navigation(url, selector, depth, job_id):
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.get(url)
    time.sleep(5)

    soup = BeautifulSoup(driver.page_source, 'lxml')
    content = soup.select(selector)

    jobs[job_id]["content"] = []

    for elem in content:
        text = elem.get_text(separator=" ", strip=True)
        jobs[job_id]["content"].append({
            "content": text,
            "title": soup.title.string if soup.title else "",
            "url": url
        })

    driver.quit()
    jobs[job_id]["status"] = "completed"

@app.route('/scrape', methods=['POST'])
def scrape():
    data = request.json
    url = data.get('url')
    selector = data.get('navigation_selector', 'body')
    max_depth = int(data.get('max_depth', 1))

    job_id = str(uuid.uuid4())
    jobs[job_id] = {"status": "started", "content": []}

    thread = threading.Thread(target=scrape_navigation, args=(url, selector, max_depth, job_id))
    thread.start()

    return jsonify({"job_id": job_id, "status": "started"})

@app.route('/status/<job_id>', methods=['GET'])
def get_status(job_id):
    job = jobs.get(job_id, {})
    if not job:
        return jsonify({"status": "not_found"}), 404
    return jsonify({"job_id": job_id, "status": job["status"], "errors": []})

@app.route('/download/<job_id>', methods=['GET'])
def download_content(job_id):
    job = jobs.get(job_id, {})
    if job and job["status"] == "completed":
        return jsonify(job["content"])
    return jsonify({"status": "incomplete or not found"}), 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
