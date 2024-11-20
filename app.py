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

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Replace with a secure key
NEWS_API_KEY = "f3a094f995904af195df8a9c9e45406e"

#ipinfo token
ipinfo_token = 'eea13e49f85493'
ipinfo_handler = ipinfo.getHandler(ipinfo_token)

# MongoDB Configuration
app.config["MONGO_URI"] = "mongodb+srv://cyrenaburke:ygxYNsTwdrbTAXGC@cluster0.sgudd.mongodb.net/dbname?tls=true&tlsAllowInvalidCertificates=true"
mongo = PyMongo(app)
bcrypt = Bcrypt(app)

# MongoDB for Tracking
client = MongoClient("mongodb+srv://cyrenaburke:ygxYNsTwdrbTAXGC@cluster0.sgudd.mongodb.net/user_behavior?tls=true&tlsAllowInvalidCertificates=true")
db = client['user_behavior']
clicks_collection = db['clicks']
context_collection = db['context']

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

@app.route('/like_article/<article_id>', methods=['POST'])
def like_article(article_id):
    username = session.get('username')
    if not username:
        return jsonify({'error': 'Unauthorized'}), 401

    # Fetch the article from MongoDB
    article = mongo.db.articles.find_one({"_id": ObjectId(article_id)})

    if article:
        # Update or initialize likes
        if 'likes' not in article or username not in article['likes']:
            mongo.db.articles.update_one(
                {"_id": ObjectId(article_id)},
                {"$push": {"likes": username}, "$inc": {"like_count": 1}},
                upsert=True
            )
    else:
        # Insert new article with initial like count
        mongo.db.articles.insert_one({
            "_id": ObjectId(article_id),
            "likes": [username],
            "like_count": 1,
            "created_at": datetime.utcnow()
        })

    return redirect(url_for('home'))

@app.route('/home')
def home():
    if 'username' in session:
        # Track contextual data when accessing the home page
        contextual_data()

    # Fetch news articles from News API
    url = f"https://newsapi.org/v2/top-headlines?country=us&apiKey={NEWS_API_KEY}"
    response = requests.get(url)
    
    if response.status_code == 200:
        articles = response.json().get('articles', [])
        for article in articles:
            article['_id'] = str(ObjectId())
    else:
        articles = []

    return render_template(
        'home.html',
        username=session.get('username'),
        articles=articles
    )



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

def content_based_recommendations(articles):
    descriptions = [article.get('description', '') for article in articles]
    tfidf = TfidfVectorizer(stop_words='english')
    tfidf_matrix = tfidf.fit_transform(descriptions)
    cosine_sim = cosine_similarity(tfidf_matrix, tfidf_matrix)

    recommendations = {}
    for idx, article in enumerate(articles):
        sim_scores = list(enumerate(cosine_sim[idx]))
        sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)
        recommendations[article['title']] = [articles[i[0]]['title'] for i in sim_scores[1:4]]
    return recommendations

if __name__ == '__main__':
    app.run(debug=True)
