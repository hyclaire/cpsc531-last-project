from pymongo import MongoClient

MONGO_URI = "mongodb+srv://cyrenaburke:ygxYNsTwdrbTAXGC@cluster0.sgudd.mongodb.net/dbname?tls=true&tlsAllowInvalidCertificates=true"
#MONGO_URI = "mongodb+srv://cpsc531:cpsc531@cluster0.sgudd.mongodb.net/"


client = MongoClient(MONGO_URI)
db = client.newsDB
collection = db.articles

# Test insert
test_article = {'title': 'Test', 'content': 'This is a test article'}
result = collection.insert_one(test_article)
print(f"Inserted article with ID: {result.inserted_id}")
