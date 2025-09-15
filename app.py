from flask import Flask, render_template, request, redirect, url_for
from pymongo import MongoClient

app = Flask(__name__)

# 🔹 Connect to MongoDB Atlas
client = MongoClient("mongodb+srv://campus360:swami056@campus360.nisg0xn.mongodb.net/?retryWrites=true&w=majority&appName=campus360")
db = client["campus360"]          # Database name
users_collection = db["data"]    # Collection name

@app.route("/")
def home():
    return redirect(url_for("login"))

# 🔹 Login Route
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        role = request.form.get("role")

        # Check if user exists
        user = users_collection.find_one({"email": email, "password": password, "role": role})
        if user:
            return f"✅ Welcome {role.capitalize()} {user['name']}!"
        else:
            return "❌ Invalid credentials!"

    return render_template("login.html")

# 🔹 Signup Route
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        password = request.form.get("password")
        role = request.form.get("role")

        # Check if user already exists
        existing_user = users_collection.find_one({"email": email})
        if existing_user:
            return "⚠️ User already exists! Please log in."

        # Insert new user
        users_collection.insert_one({
            "name": name,
            "email": email,
            "password": password,
            "role": role
        })

        return redirect(url_for("login"))

    return render_template("signup.html")

if __name__ == "__main__":
    app.run(debug=True)
