from flask import Flask, render_template, jsonify, request
import requests
from pymongo import MongoClient
from datetime import datetime

app = Flask(__name__)
NEWS_API_KEY = "f3a094f995904af195df8a9c9e45406e"  # Replace with your API key
NEWS_API_URL = "https://newsapi.org/v2/everything/"

# MongoDB connection
#client = MongoClient("mongodb+srv://user-1:cpsc531@cpsc531.uceq9.mongodb.net/testdatabase")
#client = MongoClient("mongodb://localhost:27017/")
MONGO_URI = "mongodb+srv://cyrenaburke:ygxYNsTwdrbTAXGC@cluster0.sgudd.mongodb.net/dbname?tls=true&tlsAllowInvalidCertificates=true"
client = MongoClient(MONGO_URI)
db = client.newsDB  # Database name
collection = db.articles  # Collection name

@app.route('/')

def home():
    # Call the News API
    url = "https://newsapi.org/v2/everything"
    #url = "https://newsapi.org/v2/top-headlines/sources"
    params = {
        'apiKey': NEWS_API_KEY,  # Replace with your actual API key
        'language': 'en',           # Change as needed
        'pageSize': 2 ,             # Number of articles to return
        'q': 'entertainment'
    }
    response = requests.get(url, params=params)

    articles = []
    response = requests.get(NEWS_API_URL, params=params)
    print(f"API Response Status Code: {response.status_code}")
    
    # Fetch articles from NewsAPI
    response = requests.get(NEWS_API_URL, params=params)
    if response.status_code != 200:
        return jsonify({
            'error': response.json().get('message', 'Unknown error'),
            'status_code': response.status_code
        })

    articles = response.json().get('articles', [])
    print(f"Fetched {len(articles)} articles.")
    
    saved_articles = []
    for article in articles:
        article_data = {
            'title': article['title'],
            'description': article['description'],
            'url': article['url'],
            'publishedAt': article['publishedAt'],
            'source': article['source']['name'],
            'load_time': datetime.now()
        }
        try:
            if collection.find_one({'url': article['url']}) is None:
                collection.insert_one(article_data)
                #saved_articles.append(article_data) #updated by HS
                saved_articles.append(article);
                print(f"Article inserted: {article['title']}")
            else:
                print(f"Duplicate article skipped: {article['title']}")
        except Exception as e:
            print(f"Error inserting article: {e}")

    return jsonify({
        'message': f'{len(saved_articles)} new articles saved.',
        'saved_articles': saved_articles
    })

if __name__ == '__main__':
    app.run(debug=True)
