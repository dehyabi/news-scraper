# Article Scraper

## Overview

This project is an article scraper that retrieves articles from specified web pages using Selenium WebDriver. It extracts titles, URLs, and descriptions of articles and inserts them into a database.

## Features

- Scrapes up to 3 articles per request.
- Extracts article title, URL, and description.
- Inserts scraped data into a database.
- Runs in headless mode for automated scraping.

## Requirements

- Flask
- psycopg2
- python-dotenv
- selenium
- webdriver-manager
- gunicorn==20.1.0

## Installation

1. Create a virtual environment:

   ```bash
   python -m venv venv
   ```

2. Activate the virtual environment:

   - On Windows:
     ```bash
     venv\Scripts\activate
     ```
   - On macOS and Linux:
     ```bash
     source venv/bin/activate
     ```

3. Clone the repository:

   ```bash
   git clone <repository-url>
   cd <repository-directory>
   ```

4. Install the required packages:

   ```bash
   pip install -r requirements.txt
   ```

5. Ensure you have Chrome WebDriver installed and available in your PATH.

## Usage

To run the scraper, execute the following command:

```bash
python app.py
```

To run the application using Flask, use the following command:

```bash
flask run
```

To run the application using Gunicorn, use the following command:

```bash
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

You may need to modify the `app.py` file to set the appropriate search URL and payload for scraping.

## Access Token

To access the endpoints, you need to include an access token in the request headers.

### For GET requests:

```bash
curl -X GET -H "Authorization: Bearer <your_access_token>" "http://localhost:5000/articles?candidate_id=1"
```

### For POST requests:

```bash
curl -X POST -H "Authorization: Bearer <your_access_token>" -H "Content-Type: application/json" -d '{"query": "prabowo", "candidate_id": 1}' http://localhost:5000/scrape
```

Replace `<your_access_token>` with your actual access token and adjust the URL to match your API endpoint.

## Logging

The application logs extracted data and any errors encountered during the scraping process.
