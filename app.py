import os
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from scrapegraphai.graphs import SmartScraperGraph

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)

# Retrieve OpenAI API key from environment variables
openai_key = os.getenv("OPENAI_API_KEY")

# ScrapeGraphAI configuration
graph_config = {
    "llm": {
        "api_key": openai_key,
        "model": "openai/gpt-4",  # Ensure this model is available in your OpenAI subscription
    },
}

@app.route('/search', methods=['POST'])
def search():
    # Retrieve JSON payload from the request
    data = request.get_json()
    if not data or 'query' not in data:
        return jsonify({"error": "Invalid input. 'query' is required."}), 400

    search_query = data['query']
    # Construct the search URL
    search_url = f"https://www.detik.com/search/searchall?query={search_query}&siteid=2&source_kanal=true"

    # Initialize the SmartScraperGraph
    smart_scraper_graph = SmartScraperGraph(
        prompt="Extract all article titles and their corresponding URLs from the search results page.",
        source=search_url,
        config=graph_config
    )

    # Run the scraper
    result = smart_scraper_graph.run()

    # Return the result as a JSON response
    return jsonify(result)

if __name__ == '__main__':
    app.run(debug=True)
