from flask import Flask, render_template, redirect, url_for, request, session, flash, jsonify
from flask_pymongo import PyMongo
from pymongo import MongoClient
import requests
from flask_bcrypt import Bcrypt
from datetime import datetime
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import hashlib
from user_agents import parse

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Replace with a secure key
NEWS_API_KEY = "f3a094f995904af195df8a9c9e45406e"

# MongoDB Configuration
app.config["MONGO_URI"] = "mongodb+srv://cyrenaburke:ygxYNsTwdrbTAXGC@cluster0.sgudd.mongodb.net/dbname?tls=true&tlsAllowInvalidCertificates=true"
mongo = PyMongo(app)
bcrypt = Bcrypt(app)

# MongoDB Configuration Click Tracker

client = MongoClient("mongodb+srv://cyrenaburke:ygxYNsTwdrbTAXGC@cluster0.sgudd.mongodb.net/user_behavior?tls=true&tlsAllowInvalidCertificates=true")
db = client['user_behavior']
clicks_collection = db['clicks']
context_collection = db['context']

#Routes
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
            # need to push contextual data to MongoDB
            #context_data_return = contextual_data(username)
            return redirect(url_for('home'))
        else:
            flash("Invalid username or password.", "danger")

    return render_template('login.html')


def contextual_data(username):
    #location
    #ip_address = request.headers.get('X-Forwarded-For', request.remote_addr)
    #response_from_ip = requests.get(f"https://ipapi.co/{ip_address}/json/")
    #location_data_city = response_from_ip.json().get("city")
    #location_data_region = response_from_ip.json().get("region")
    #location_data_country = response_from_ip.json().get("country")
    #location_data_latitude = response_from_ip.json().get("latitude")
    #location_data_longitude = response_from_ip.json().get("longitude")
    #device_info
    #user_agent = request.headers.get('User-Agent')
    #parsed_agent = parse(user_agent)
    
    #browser =  parsed_agent.browser.family
    #browser_version = parsed_agent.browser.version_string
    #os =  parsed_agent.os.family
    #os_version =  parsed_agent.os.version_string
    #device = parsed_agent.device.family
    #is_mobile = parsed_agent.is_mobile
    #is_tablet = parsed_agent.is_tablet
    #is_pc = parsed_agent.is_pc
    
    #time_of_access
    request_data = request.get_json(force=True)
    user_time = request_data.get('userTime') #ISO format time
    time_zone = request_data.get('timeZone') #Timezone name

    context_collection.insert_one(
        {
        "user_id":username,
        #"location_data_city":location_data_city,
        #"location_data_region":location_data_region,
        #"location_data_country":location_data_country,
        #"location_data_latitude":location_data_latitude,
        #"location_data_longitude":location_data_longitude,
        #"browser":browser,
        #"browser_version":browser_version,
        #"os":os,
        #"os_version":os_version,
        #"device":device,
        #"is_mobile":is_mobile,
        #"is_tablet":is_tablet,
        #"is_pc":is_pc,
        "user_time":user_time,
        "time_zone":time_zone
        }
    )

    return True


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        users_collection = mongo.db.users
        existing_user = users_collection.find_one({"username": username})

        if existing_user:
            flash("Username already exists.", "danger")
            return redirect(url_for('register'))

        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        users_collection.insert_one({"username": username, "password": hashed_password})
        flash("Registration successful! Please log in.", "success")
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    flash("You have been logged out.", "success")
    return redirect(url_for('login'))

@app.route('/home')
def home():
    # Fetch news articles from News API
    url = f"https://newsapi.org/v2/top-headlines?country=us&apiKey={NEWS_API_KEY}"
    response = requests.get(url)

    if response.status_code == 200:
        articles = response.json().get('articles', [])
    else:
        articles = []

    # Perform content-based and collaborative filtering recommendations
    content_recs = content_based_recommendations(articles)
    user_recs = collaborative_filtering_recommendations()

    # Combine both recommendations using an ensemble approach
    final_recommendations = combine_recommendations(content_recs, user_recs)

    # Pass articles, final recommendations, and session data to the template
    return render_template(
        'home.html',
        username=session.get('username'),
        visit_count=session.get('visit_count', 0),
        articles=articles,
        recommendations=final_recommendations
    )


def content_based_recommendations(articles):
    """Content-based recommendation based on TF-IDF and cosine similarity."""
    titles = [article['title'] for article in articles]
    descriptions = [article['description'] for article in articles]

    # TF-IDF Vectorizer to convert text data to vectors
    tfidf = TfidfVectorizer(stop_words='english')
    tfidf_matrix = tfidf.fit_transform(descriptions)

    # Cosine similarity between articles based on content
    cosine_sim = cosine_similarity(tfidf_matrix, tfidf_matrix)

    # Recommend top 3 similar articles for each article
    recommendations = {}
    for idx, article in enumerate(articles):
        sim_scores = list(enumerate(cosine_sim[idx]))
        sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)
        recommendations[article['title']] = sim_scores[1:4]  # Top 3 similar articles

    return recommendations


def collaborative_filtering_recommendations():
    """Collaborative filtering recommendation based on user behavior (clicks)."""
    interactions = list(mongo.db.user_interactions.find())
    user_article_matrix = {}

    # Build user-article interaction matrix
    for interaction in interactions:
        user = interaction['username']
        article_id = interaction['article_id']
        if user not in user_article_matrix:
            user_article_matrix[user] = {}
        user_article_matrix[user][article_id] = 1  # Assuming click interaction

    # Calculate item-item similarity based on user interactions
    item_similarity = {}
    for user, articles in user_article_matrix.items():
        for article_id in articles:
            if article_id not in item_similarity:
                item_similarity[article_id] = {}
            for other_article_id in articles:
                if other_article_id != article_id:
                    if other_article_id not in item_similarity[article_id]:
                        item_similarity[article_id][other_article_id] = 0
                    item_similarity[article_id][other_article_id] += 1  # Count how many users clicked on both articles

    # Recommend articles based on item-item similarity
    recommendations = {}
    for article_id, similar_articles in item_similarity.items():
        recommendations[article_id] = sorted(similar_articles.items(), key=lambda x: x[1], reverse=True)[:3]

    return recommendations


def combine_recommendations(content_recs, collaborative_recs, alpha=0.7, beta=0.3):
    """Combine content-based and collaborative filtering recommendations using weighted average."""
    combined_recs = {}

    for article, content_sim in content_recs.items():
        if article in collaborative_recs:
            collaborative_sim = collaborative_recs[article]
            combined_recs[article] = alpha * content_sim + beta * collaborative_sim

    # Sort recommendations by combined score
    sorted_recs = sorted(combined_recs.items(), key=lambda x: x[1], reverse=True)
    return sorted_recs


@app.route('/track_click', methods=['POST'])
def track_click():
    # Extract data from the request
    data = request.json
    username = session.get('username', 'Anonymous')
    
    # Create a document for the click event
    click_event = {
        "username": username,
        "article_title": data.get('title'),
        "article_url": data.get('url'),
        "clicked_at": datetime.utcnow()
    }

    # Insert the click event into MongoDB
    clicks_collection.insert_one(click_event)

    # Return a success response
    return {"status": "success"}, 200

if __name__ == '__main__':
    app.run(debug=True)