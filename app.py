from flask import Flask, render_template
import requests

app = Flask(__name__)

@app.route('/')
def home():
    # Call the News API
    url = "https://newsapi.org/v2/top-headlines"
    params = {
        'apiKey': '97a585ab11d1437ea7a196a5feb55681',  # Replace with your actual API key
        'country': 'us',            # Change as needed
        'pageSize': 10               # Number of articles to return
    }
    response = requests.get(url, params=params)

    articles = []
    if response.status_code == 200:
        articles = response.json().get('articles', [])

    return render_template('index.html', articles=articles)

if __name__ == '__main__':
    app.run(debug=True)
