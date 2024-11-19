from flask import Flask, render_template, request, redirect, url_for, make_response, session
from flask_pymongo import PyMongo

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # Needed for sessions

# MongoDB URI (local or Atlas)
app.config["MONGO_URI"] = "mongodb+srv://cyrenaburke:ygxYNsTwdrbTAXGC@cluster0.sgudd.mongodb.net/dbname?tls=true&tlsAllowInvalidCertificates=true"
mongo = PyMongo(app)

# Home Route: Check if username is stored in a cookie
@app.route('/')
def home():
    username = request.cookies.get('username')  # Retrieve username from cookie
    if username:
        # Check if user exists in MongoDB
        user = mongo.db.users.find_one({"username": username})
        if user:
            return render_template('home.html', username=username)
        else:
            return redirect(url_for('login'))  # User not found, redirect to login
    else:
        # If no cookie, redirect to /login
        return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    username = request.cookies.get('username')
    if username:
        return redirect(url_for('profile'))  # Redirect to profile if cookie exists

    if request.method == 'POST':
        user_input = request.form['username']

        # Validate username format (firstname_lastname)
        if not user_input or len(user_input.split('_')) != 2:
            return "Invalid username. Please enter your firstname_lastname.", 400

        # Set the cookie with the username, expiry in 30 minutes
        resp = make_response(redirect(url_for('profile')))
        resp.set_cookie('username', user_input, max_age=30*60)  # 30 minutes expiration

        # Initialize session variable to track visit count
        session['visit_count'] = 0

        # Log the MongoDB operation
        print(f"Attempting to store username: {user_input}")

        # Store user info in MongoDB
        result = mongo.db.users.update_one(
            {"username": user_input},
            {"$set": {"username": user_input, "visit_count": 0}},
            upsert=True  # Create a new user if it doesn't exist
        )

        print(f"MongoDB update result: {result.raw_result}")  # This logs the result of the operation

        return resp

    return render_template('login.html')

@app.route('/profile')
def profile():
    username = request.cookies.get('username')  # Get username from cookie
    if not username:
        return redirect(url_for('login'))  # Redirect to login if no cookie

    # Increment visit count stored in session
    session['visit_count'] = session.get('visit_count', 0) + 1

    # Update the visit count in MongoDB
    mongo.db.users.update_one(
        {"username": username},
        {"$inc": {"visit_count": 1}}  # Increment visit_count
    )

    # Retrieve the updated user info
    user = mongo.db.users.find_one({"username": username})

    return render_template('profile.html', username=user['username'], visit_count=user['visit_count'])


# Run the application
if __name__ == '__main__':
    app.run(debug=True)
