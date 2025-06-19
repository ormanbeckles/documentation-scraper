from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
import uuid
import threading

app = Flask(__name__)
CORS(app)

jobs = {}

def simple_scrape(job_id, url):
    try:
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'lxml')
        title = soup.title.string if soup.title else "No title found"
        text = soup.get_text()
        
        jobs[job_id]["status"] = "completed"
        jobs[job_id]["result"] = {
            "url": url,
            "title": title,
            "content": text[:2000]  # increased limit for now
        }
    except Exception as e:
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = str(e)

@app.route("/")
def home():
    return "Documentation scraper is online!"

@app.route("/scrape", methods=["POST"])
def scrape():
    data = request.json
    url = data.get("url")
    if not url:
        return jsonify({"error": "URL is required"}), 400
    
    job_id = str(uuid.uuid4())
    jobs[job_id] = {"status": "in_progress", "result": None}
    
    thread = threading.Thread(target=simple_scrape, args=(job_id, url))
    thread.start()

    return jsonify({"job_id": job_id, "status": "started"})

@app.route("/status/<job_id>", methods=["GET"])
def status(job_id):
    job = jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    return jsonify({"job_id": job_id, "status": job["status"]})

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
