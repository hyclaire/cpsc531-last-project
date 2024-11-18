import requests

# Define the endpoint and parameters
url = "https://newsapi.org/v2/top-headlines"
params = {
    'apiKey': '97a585ab11d1437ea7a196a5feb55681',
    'country': 'us',  # Change as needed
    'pageSize': 5     # Number of articles to return
}

# Make the API request
response = requests.get(url, params=params)

# Check if the request was successful
if response.status_code == 200:
    articles = response.json().get('articles', [])
    for article in articles:
        print(article['title'])
else:
    print(f"Error: {response.status_code}")
