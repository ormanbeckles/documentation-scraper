FROM python:3.11-slim

RUN apt-get update && apt-get install -y wget gnupg unzip curl xvfb libxi6 libgconf-2-4 && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 10000

CMD ["gunicorn", "-b", "0.0.0.0:10000", "app:app"]
