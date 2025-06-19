from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
import uuid
import threading
from urllib.parse import urljoin, urlparse

app = Flask(__name__)
CORS(app)

jobs = {}

def scrape_navigation(job_id, base_url, navigation_selector, max_depth=2):
    visited = set()
    content_results = []

    def scrape_recursive(url, depth):
        if depth > max_depth or url in visited:
            return
        visited.add(url)
        try:
            response = requests.get(url)
            soup = BeautifulSoup(response.text, 'lxml')

            content = {
                'url': url,
                'title': soup.title.string if soup.title else "No title",
                'content': soup.get_text()[:5000]  # expanded content length
            }
            content_results.append(content)

            # find navigation links clearly
            nav_links = [urljoin(base_url, a['href']) for a in soup.select(navigation_selector + ' a[href]')]
            nav_links = [link for link in nav_links if urlparse(link).netloc == urlparse(base_url).netloc]

            for link in nav_links:
                scrape_recursive(link, depth + 1)

        except Exception as e:
            jobs[job_id]['errors'].append(str(e))

    scrape_recursive(base_url, 1)
    jobs[job_id]['status'] = 'completed'
    jobs[job_id]['result'] = content_results

@app.route("/")
def home():
    return "Documentation scraper is online!"

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
