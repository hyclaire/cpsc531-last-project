from flask import Flask, render_template, redirect, url_for, request, session, flash, jsonify
from flask_pymongo import PyMongo
from pymongo import MongoClient
import requests
from flask_bcrypt import Bcrypt
from datetime import datetime
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from bson.objectid import ObjectId
from user_agents import parse
import ipinfo
from bson import ObjectId
from keybert import KeyBERT
import urllib


app = Flask(__name__)

app.secret_key = 'your_secret_key'  # Replace with a secure key

# NewsAPI Key
#NEWS_API_KEY = 'f3a094f995904af195df8a9c9e45406e'
NEWS_API_KEY = '97a585ab11d1437ea7a196a5feb55681'
NEWS_API_URL = 'https://newsapi.org/v2/top-headlines'

#ipinfo token
ipinfo_token = 'eea13e49f85493'
ipinfo_handler = ipinfo.getHandler(ipinfo_token)

# MongoDB Atlas connection like button
client = MongoClient("mongodb+srv://cyrenaburke:ygxYNsTwdrbTAXGC@cluster0.sgudd.mongodb.net/dbname?tls=true&tlsAllowInvalidCertificates=true")
db = client.dbname  # 'dbname' is your database name
articles_collection = db.articles  # 'articles' is your collection name

# MongoDB Configuration
app.config["MONGO_URI"] = "mongodb+srv://cyrenaburke:ygxYNsTwdrbTAXGC@cluster0.sgudd.mongodb.net/dbname?tls=true&tlsAllowInvalidCertificates=true"
mongo = PyMongo(app)
bcrypt = Bcrypt(app)

# MongoDB for Tracking
client = MongoClient("mongodb+srv://cyrenaburke:ygxYNsTwdrbTAXGC@cluster0.sgudd.mongodb.net/user_behavior?tls=true&tlsAllowInvalidCertificates=true")
db = client['user_behavior']
clicks_collection = db['clicks']
context_collection = db['context']

@app.route('/keybert', methods=['POST'])
def keybert():
    #for testing semantic keyword extraction
    # Initialize KeyBERT
    kw_model = KeyBERT()

# Test
    keywords = kw_model.extract_keywords("This is a test description for keyword extraction.")
    #print(keywords)
    flash(keywords, "danger")
    return {"status": "success"}, 200

@app.route('/contextual_data', methods=['POST'])
def contextual_data():
    # Get IP address 
    ip_address = request.remote_addr

    # Extract location details
    location = {
        "city": ipinfo_handler.getDetails().city,
        "region": ipinfo_handler.getDetails().region,
        "country": ipinfo_handler.getDetails().country
    } 

    # Extract device details
    user_agent = request.headers.get('User-Agent')
    parsed_agent = parse(user_agent)
    device_info = {
        "browser": parsed_agent.browser.family,
        "browser_version": parsed_agent.browser.version_string,
        "os": parsed_agent.os.family,
        "os_version": parsed_agent.os.version_string,
        "device": parsed_agent.device.family,
        "is_mobile": parsed_agent.is_mobile,
        "is_tablet": parsed_agent.is_tablet,
        "is_pc": parsed_agent.is_pc,
    }

    # Access time
    time_of_access = datetime.now()

    # Construct the contextual data object
    context_data = {
        "user_id": session.get('username', 'Anonymous'),
        "ip_address": ip_address,
        "location": location,
        "device_info": device_info,
        "time_of_access": time_of_access.isoformat(),  # ISO 8601 format
        "timezone": ipinfo_handler.getDetails().timezone # Optional from client
    }

    # Insert into MongoDB
    context_collection.insert_one(context_data)

    return {"status": "success"}, 200

@app.route('/')
def landing():

    return render_template('landing.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'username' in session:
        return redirect(url_for('home'))

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        users_collection = mongo.db.users
        user = users_collection.find_one({"username": username})

        if user and bcrypt.check_password_hash(user['password'], password):
            session['username'] = username
            flash("Login successful!", "success")

            # Track contextual data
            contextual_data()
        
            return redirect(url_for('home'))
        else:
            flash("Invalid username or password.", "danger")

    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        existing_user = mongo.db.users.find_one({"username": username})

        if existing_user:
            flash("Username already exists.", "danger")
            return redirect(url_for('register'))

        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        mongo.db.users.insert_one({"username": username, "password": hashed_password})
        flash("Registration successful! Please log in.", "success")
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    flash("You have been logged out.", "success")
    return redirect(url_for('login'))

# Route: Home page (protected)
@app.route('/home')
def home():
    if 'username' in session:
        username = session['username']
        # Fetch user's news from MongoDB
        news = fetch_news(username)  # Pass username to fetch user-specific info
        return render_template('home.html', username=username, news=news)
    else:
        return redirect(url_for('login'))  # Redirect to login if not authenticated

@app.route('/track_click', methods=['POST'])
def track_click():
    data = request.json
    username = session.get('username', 'Anonymous')

    click_event = {
        "username": username,
        "article_title": data.get('title'),
        "article_url": data.get('url'),
        "clicked_at": datetime.utcnow()
    }
    clicks_collection.insert_one(click_event)
    return {"status": "success"}, 200

# Route to handle liking an article
@app.route('/like-article', methods=['POST'])
def like_article():
    if 'username' not in session:
        return jsonify({'error': 'Unauthorized'}), 401  # User must be logged in

    data = request.get_json()
    article_id = data['article_id']  # Get the article ID from the request
    username = session['username']  # Get the logged-in username

    # Find the article in the MongoDB collection by its ObjectId
    article = articles_collection.find_one({'_id': ObjectId(article_id)})

    if article:
        # Check if the user already liked the article
        if username in article.get('liked_by', []):
            return jsonify({'error': 'Already liked'}), 400  # User already liked the article

        # Increment the like count and add the user to the liked_by list
        articles_collection.update_one(
            {'_id': ObjectId(article_id)},
            {
                '$inc': {'likes': 1},  # Increment the like count
                '$addToSet': {'liked_by': username}  # Add user to liked_by list
            }
        )

        # Return the updated like count as JSON
        updated_article = articles_collection.find_one({'_id': ObjectId(article_id)})
        return jsonify({'likes': updated_article['likes']})
    
    return jsonify({'error': 'Article not found'}), 404

# Function to fetch news from NewsAPI and store in MongoDB if not already stored
def fetch_news(username=None):
    
    # Fetch all articles from MongoDB
    articles = list(mongo.db.articles.find())

    # Add liked_by_user field for each article
    for article in articles:
        article['_id'] = str(article['_id'])  # Convert ObjectId to string for frontend
        article['liked_by_user'] = username in article.get('liked_by', [])

    #return articles
    # Check if news is already stored in the database
    existing_articles = list(mongo.db.articles.find())  # Fetch articles from MongoDB

    if not existing_articles:  # If no news articles are found, fetch from API
        # Define parameters for NewsAPI request

        #testing for query
        query = 'korea'
        #encoded_query = urllib.parse.quote(query)
        params = {
            'q': query,
            'apiKey': NEWS_API_KEY,
            'language': 'en',  # Change to the country code you want
            'pageSize': 7,  # Fetch top 5 articles
        }

        # Fetch news from NewsAPI
        response = requests.get(NEWS_API_URL, params=params)

        if response.status_code == 200:
            articles = response.json().get('articles', [])

            # Store articles in MongoDB if not already stored
            for article in articles:
                mongo.db.articles.update_one(
                    {'url': article['url']},  # Use URL as a unique identifier
                    {'$set': article},  # Update or insert the article
                    upsert=True  # Insert the article if it doesn't already exist
                )
        else:
            print(f"Error fetching news from NewsAPI: {response.status_code}")
            return []  # Return an empty list if API fetch fails

        # Return articles from the database
        return list(mongo.db.articles.find())

    # If articles already exist, return them from the database
    return existing_articles

if __name__ == '__main__':
    app.run(debug=True)
