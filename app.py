from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)
CORS(app)

@app.route("/")
def home():
    return "Documentation scraper is online!"

@app.route("/scrape", methods=["POST"])
def scrape():
    data = request.json
    url = data.get("url")

    if not url:
        return jsonify({"error": "URL is required"}), 400

    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'lxml')

    # Basic extraction (will refine later)
    title = soup.title.string if soup.title else "No title found"
    text = soup.get_text()

    return jsonify({
        "url": url,
        "title": title,
        "content": text[:500]  # limit initial output to first 500 characters
    })

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=10000)
