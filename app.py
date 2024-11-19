from flask import Flask, render_template, jsonify, request
import requests
from pymongo import MongoClient

app = Flask(__name__)

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
        'apiKey': '97a585ab11d1437ea7a196a5feb55681',  # Replace with your actual API key
        'language': 'en',           # Change as needed
        #'pageSize': 5               # Number of articles to return
        'q': 'science'
    }
    response = requests.get(url, params=params)

    articles = []
    if response.status_code == 200:
        articles = response.json().get('articles', [])

        if articles:
            for article in articles:
                article.pop('_id', None)  # Avoid MongoDB duplicate key error

            collection.insert_many(articles)

    return render_template('index.html', articles=articles)

@app.route('/add', methods=['POST'])
def add_document():
    data = request.json
    collection.insert_one(data)
    return jsonify(message="Document added!", data=data)

@app.route('/documents', methods=['GET'])
def get_documents():
    documents = list(collection.find({}, {'_id': 0}))
    return jsonify(documents=documents)

if __name__ == '__main__':
    app.run(debug=True)
