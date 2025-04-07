import os
import psycopg2
import logging
import tempfile
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from datetime import datetime

# Load environment variables
load_dotenv()
ACCESS_TOKEN_KEY = os.getenv('ACCESS_TOKEN_KEY')

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# Initialize Flask app
app = Flask(__name__)

# Retrieve DB credentials from env
DATABASE_NAME = os.getenv("DATABASE_NAME")
DATABASE_USER = os.getenv("DATABASE_USER")
DATABASE_PASSWORD = os.getenv("DATABASE_PASSWORD")
DATABASE_HOST = os.getenv("DATABASE_HOST")
DATABASE_PORT = os.getenv("DATABASE_PORT")

# Ensure DB credentials exist
if not all([DATABASE_NAME, DATABASE_USER, DATABASE_PASSWORD, DATABASE_HOST, DATABASE_PORT]):
    logging.error("Missing database environment variables.")
    exit(1)

# Create articles table if not exists
def create_table():
    try:
        logging.info("Connecting to DB to create table...")
        conn = psycopg2.connect(
            dbname=DATABASE_NAME,
            user=DATABASE_USER,
            password=DATABASE_PASSWORD,
            host=DATABASE_HOST,
            port=DATABASE_PORT
        )
        cursor = conn.cursor()

        # Buat sequence jika belum ada
        cursor.execute("""
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_class WHERE relname = 'articles_id_seq') THEN
                    CREATE SEQUENCE articles_id_seq;
                END IF;
            END
            $$;
        """)

        # Buat table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS articles (
                id INTEGER PRIMARY KEY DEFAULT nextval('articles_id_seq'),
                title TEXT NOT NULL,
                url TEXT NOT NULL UNIQUE,
                description TEXT,
                candidate_id INTEGER,
                candidate_name TEXT,
                scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        logging.info("Table 'articles' created or already exists.")
    except Exception as e:
        logging.error(f"Error creating table: {e}")
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn' in locals(): conn.close()

def insert_articles(cursor, title, url, description=None, candidate_id=None, candidate_name=None, scraped_at=None):
    try:
        if scraped_at is None:
            scraped_at = datetime.now().strftime('%Y-%m-%d %H:%M')
        cursor.execute('''
            INSERT INTO articles (title, url, description, candidate_id, candidate_name, scraped_at)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (url) DO NOTHING
        ''', (title, url, description, candidate_id, candidate_name, scraped_at))
        logging.info(f"Inserted article: {title}")
    except Exception as e:
        logging.error(f"Insert error: {e}")

class WebDriver:
    def __init__(self):
        pass

    def run_scraping(self, cursor, search_url, payload):
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')

        # ✅ Use unique user data dir per session
        temp_dir = tempfile.mkdtemp()
        options.add_argument(f'--user-data-dir={temp_dir}')

        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

        try:
            logging.debug(f"Visiting: {search_url}")
            driver.get(search_url)

            article_elements = driver.find_elements(By.CSS_SELECTOR, '.gsc-expansionArea .gsc-webResult.gsc-result')[:3]

            for article in article_elements:
                try:
                    title_element = article.find_element(By.CSS_SELECTOR, '.gs-title')
                    url = article.find_element(By.CSS_SELECTOR, '.gsc-thumbnail-left a').get_attribute('href')
                    title = title_element.text.strip()

                    desc_elem = article.find_element(By.CSS_SELECTOR, '.gs-snippet')
                    description = desc_elem.text.strip() if desc_elem else None

                    logging.info(f"Scraped: {title}, {url}")
                    insert_articles(
                        cursor, title, url, description,
                        payload['candidate_id'], payload['candidate_name']
                    )
                except Exception as inner_e:
                    logging.warning(f"Failed scraping one article: {inner_e}")
        except Exception as e:
            logging.error(f"Scraping error: {e}")
        finally:
            driver.quit()

web_driver = WebDriver()

@app.before_request
def require_token():
    token = request.headers.get('Authorization')
    if not token or not token.startswith('Bearer '):
        return jsonify({'message': 'Access token missing or invalid.'}), 401
    if token.split(" ")[1] != ACCESS_TOKEN_KEY:
        return jsonify({'message': 'Access token is invalid.'}), 403

@app.route('/scrape', methods=['POST'])
def scrape():
    data = request.get_json()
    if not data or 'query' not in data:
        return jsonify({"error": "'query' is required."}), 400

    query = data['query']
    candidate_id = data.get('candidate_id')
    search_url = f'https://search.kompas.com/search/?q={query}'

    payload = {
        'search_query': query,
        'candidate_id': candidate_id,
        'candidate_name': query
    }

    try:
        conn = psycopg2.connect(
            dbname=DATABASE_NAME,
            user=DATABASE_USER,
            password=DATABASE_PASSWORD,
            host=DATABASE_HOST,
            port=DATABASE_PORT
        )
        cursor = conn.cursor()
        web_driver.run_scraping(cursor, search_url, payload)
        conn.commit()
    except Exception as e:
        logging.error(f"DB Insert error: {e}")
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn' in locals(): conn.close()

    return jsonify({"message": "Scraping complete."})

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
        cursor.execute("SELECT * FROM articles WHERE candidate_id = %s", (candidate_id,))
        rows = cursor.fetchall()

        result = [{
            "id": row[0],
            "title": row[1],
            "url": row[2],
            "description": row[3],
            "candidate_id": row[4],
            "candidate_name": row[5],
            "scraped_at": row[6].strftime('%Y-%m-%d %H:%M') if row[6] else None
        } for row in rows]

        return jsonify(result), 200
    except Exception as e:
        logging.error(f"Fetch error: {e}")
        return jsonify({"error": "Internal error."}), 500
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn' in locals(): conn.close()

# Create table on start
create_table()
