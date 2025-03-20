import os
import psycopg2
import logging
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import threading

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)

# Retrieve OpenAI API key from environment variables
openai_key = os.getenv("OPENAI_API_KEY")
if not openai_key:
    logging.error("OPENAI_API_KEY environment variable is not set.")
    exit(1)

# Retrieve database connection details from environment variables
database_name = os.getenv("DATABASE_NAME")
database_user = os.getenv("DATABASE_USER")
database_password = os.getenv("DATABASE_PASSWORD")
database_host = os.getenv("DATABASE_HOST")
database_port = os.getenv("DATABASE_PORT")

# Check if all database connection details are set
if not all([database_name, database_user, database_password, database_host, database_port]):
    logging.error("One or more database connection environment variables are not set.")
    exit(1)

# Function to create the 'articles' table if it doesn't exist
def create_table():
    try:
        logging.info("Connecting to the database to create the 'articles' table...")
        conn = psycopg2.connect(
            dbname=database_name,
            user=database_user,
            password=database_password,
            host=database_host,
            port=database_port
        )
        cursor = conn.cursor()

        # SQL query to create the 'articles' table
        create_table_query = """
        CREATE TABLE IF NOT EXISTS articles (
            id SERIAL PRIMARY KEY,
            title TEXT NOT NULL,
            url TEXT NOT NULL UNIQUE
        );
        """
        cursor.execute(create_table_query)
        conn.commit()
        logging.info("Table 'articles' created successfully or already exists.")
    except Exception as e:
        logging.error(f"Error creating table: {e}")
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()
            logging.info("Database connection closed.")

# Insert article into database
def insert_article(title, url):
    try:
        logging.info(f"Attempting to insert article: Title={title}, URL={url}")
        conn = psycopg2.connect(
            dbname=database_name,
            user=database_user,
            password=database_password,
            host=database_host,
            port=database_port
        )
        logging.info("Database connection successful!")
        cursor = conn.cursor()
        cursor.execute('INSERT INTO articles (title, url) VALUES (%s, %s)', (title, url))
        conn.commit()
        logging.info(f"Inserted article: {title} with URL: {url}")
    except Exception as e:
        logging.error(f"Error inserting article: {e}")
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()
            logging.info("Database connection closed.")

def run_scraping(search_url):
    # Set up headless mode
    options = Options()
    options.headless = True  # Run in headless mode

    # Initialize the WebDriver with options
    driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=options)

    # Navigate to the search URL
    driver.get(search_url)

    # Wait for the elements to load
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'figcaption > p > a')))

    # Extract article titles and URLs
    articles = []
    links = driver.find_elements(By.CSS_SELECTOR, 'figcaption > p > a')
    for link in links:
        title = link.text
        url = link.get_attribute('href')
        articles.append({'title': title, 'url': url})

    # Close the WebDriver
    driver.quit()

    # Prepare the result
    result = {'content': articles}
    logging.info(f"Raw scraper result: {result}")  # Log the raw scraper result

    # Check if result contains items
    if 'content' in result:  
        if isinstance(result['content'], list):
            for item in result['content']:
                if isinstance(item, dict):
                    title = item.get('title')
                    url = item.get('url')
                    if title and url:
                        insert_article(title, url)
                    else:
                        logging.warning("Missing title or URL in item: %s", item)
                else:
                    logging.warning("Expected a dictionary but got a string: %s", item)
        else:
            logging.error("Expected a list but got: %s", result['content'])
            return jsonify({'error': 'Unexpected data structure received.'}), 400
    else:
        logging.info("No items found in the result.")

@app.route('/search', methods=['POST'])
def search():
    data = request.get_json()
    if not data or 'query' not in data:
        logging.warning("Invalid input. 'query' is required.")
        return jsonify({"error": "Invalid input. 'query' is required."}), 400

    search_query = data['query']
    logging.info(f"Received search query: {search_query}")
    
    search_url = f"https://www.tempo.co/search?q={search_query}"

    # Run the scraping in a separate thread
    threading.Thread(target=run_scraping, args=(search_url,)).start()

    # Return a success response
    return jsonify({"message": "Scraping started successfully!"})

# Test route to verify database insertion
@app.route('/test-insert', methods=['POST'])
def test_insert():
    data = request.get_json()
    if not data or 'title' not in data or 'url' not in data:
        logging.warning("Invalid input. 'title' and 'url' are required.")
        return jsonify({"error": "Invalid input. 'title' and 'url' are required."}), 400

    title = data['title']
    url = data['url']
    insert_article(title, url)
    return jsonify({"message": "Test article inserted successfully!"})

# Create the 'articles' table when the application starts
create_table()

if __name__ == '__main__':
    logging.info("Starting the Flask application...")
    app.run(debug=True)