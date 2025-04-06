import os
import psycopg2
import logging
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from datetime import datetime

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# Initialize Flask app
app = Flask(__name__)

# Retrieve database connection details from environment variables
DATABASE_NAME = os.getenv("DATABASE_NAME")
DATABASE_USER = os.getenv("DATABASE_USER")
DATABASE_PASSWORD = os.getenv("DATABASE_PASSWORD")
DATABASE_HOST = os.getenv("DATABASE_HOST")
DATABASE_PORT = os.getenv("DATABASE_PORT")

# Check if all database connection details are set
if not all([DATABASE_NAME, DATABASE_USER, DATABASE_PASSWORD, DATABASE_HOST, DATABASE_PORT]):
    logging.error("One or more database connection environment variables are not set.")
    exit(1)

# Function to create the 'articles' table if it doesn't exist
def create_table():
    try:
        logging.info("Connecting to the database to create the 'articles' table...")
        conn = psycopg2.connect(
            dbname=DATABASE_NAME,
            user=DATABASE_USER,
            password=DATABASE_PASSWORD,
            host=DATABASE_HOST,
            port=DATABASE_PORT
        )
        cursor = conn.cursor()

        # SQL query to create the 'articles' table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS articles (
                id SERIAL PRIMARY KEY,
                title TEXT NOT NULL,
                url TEXT NOT NULL UNIQUE,
                description TEXT,
                candidate_id INTEGER,
                candidate_name TEXT,
                scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        logging.info("'articles' table created successfully.")
    except Exception as e:
        logging.error(f"Error creating table: {e}")
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()
            logging.info("Database connection closed.")

def insert_articles(cursor, title, url, description=None, candidate_id=None, candidate_name=None, scraped_at=None):
    try:
        # Ensure the timestamp is formatted correctly when captured
        if scraped_at is None:
            scraped_at = datetime.now().strftime('%Y-%m-%d %H:%M')
        
        cursor.execute('''
            INSERT INTO articles (title, url, description, candidate_id, candidate_name, scraped_at)
            VALUES (%s, %s, %s, %s, %s, %s)
        ''', (title, url, description, candidate_id, candidate_name, scraped_at))
        logging.info("Article inserted successfully.")
    except Exception as e:
        logging.error(f"Error inserting article: {e}")

class WebDriver:
    def __init__(self):
        pass

    def run_scraping(self, cursor, search_url, payload):
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')  # Run in headless mode (no GUI)
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        
        try:
            driver.get(search_url)
            # Extract title from the specified selector
            title_element = driver.find_element(By.CSS_SELECTOR, '.gs-title > a')
            title = title_element.text.strip() if title_element else None

            # Extract URL from the specified selector
            url_element = driver.find_element(By.CSS_SELECTOR, '.gs-title > a')
            url = url_element.get_attribute('href') if url_element else None

            # Extract description from the specified selector
            description_element = driver.find_element(By.CSS_SELECTOR, '.gs-bidi-start-align.gs-snippet')
            description = description_element.text.strip() if description_element else None

            logging.info(f"Extracted title: {title}")
            logging.info(f"Extracted URL: {url}")
            logging.info(f"Extracted description: {description}")
        finally:
            driver.quit()  # Ensure the WebDriver is closed

        # Insert scraped data into the database
        if title or url or description:
            insert_articles(cursor, title, url, description, payload['candidate_id'], payload['candidate_name'])
        logging.info("Scraped data inserted into the database.")

web_driver = WebDriver()

@app.route('/scrape', methods=['POST'])
def search():
    data = request.get_json()
    if not data or 'query' not in data:
        logging.warning("Invalid input. 'query' is required.")
        return jsonify({"error": "Invalid input. 'query' is required."}), 400

    search_query = data['query']
    logging.info(f"Received search query: {search_query}")
    
    search_url = f'https://search.kompas.com/search/?q={search_query}'

    try:
        logging.info("Connecting to the database to insert article...")
        conn = psycopg2.connect(
            dbname=DATABASE_NAME,
            user=DATABASE_USER,
            password=DATABASE_PASSWORD,
            host=DATABASE_HOST,
            port=DATABASE_PORT
        )
        cursor = conn.cursor()

        candidate_id = request.json.get('candidate_id')

        payload = {
            'search_query': search_query,
            'candidate_id': candidate_id,
            'candidate_name': search_query  # Set candidate_name to be the same as search_query
        }

        # Run the scraping
        web_driver.run_scraping(cursor, search_url, payload)
        conn.commit()
    except Exception as e:
        logging.error(f"Error inserting article: {e}")
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()
            logging.info("Database connection closed.")

    # Return a success response
    return jsonify({"message": "Articles scraped successfully!"})

@app.route('/articles', methods=['GET'])
def get_articles():
    candidate_id = request.args.get('candidate_id')
    
    if not candidate_id:
        return jsonify({"error": "candidate_id is required"}), 400
    
    try:
        conn = psycopg2.connect(
            dbname=DATABASE_NAME,
            user=DATABASE_USER,
            password=DATABASE_PASSWORD,
            host=DATABASE_HOST,
            port=DATABASE_PORT
        )
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM articles WHERE candidate_id = %s
        ''', (candidate_id,))
        
        articles = cursor.fetchall()
        
        # Format the articles for JSON response
        articles_list = []
        for article in articles:
            articles_list.append({
                "id": article[0],
                "title": article[1],
                "url": article[2],
                "description": article[3],
                "candidate_id": article[4],
                "candidate_name": article[5],
                "scraped_at": article[6].strftime('%Y-%m-%d %H:%M') if article[6] else None
            })
        
        return jsonify(articles_list), 200
    
    except Exception as e:
        logging.error(f"Error fetching articles: {e}")
        return jsonify({"error": "An error occurred while fetching articles"}), 500
    
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

create_table()