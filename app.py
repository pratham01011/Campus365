from flask import Flask, jsonify, render_template, request, redirect, url_for, session
import  os
from flask_jwt_extended import (
    JWTManager, create_access_token, jwt_required, get_jwt_identity
)
from pymongo import MongoClient
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "supersecretkey"  # Needed for sessions
app.config["JWT_SECRET_KEY"] = "super-secret-key"  
jwt = JWTManager(app)

# 🔹 Upload folder for student documents
UPLOAD_FOLDER = os.path.join("static", "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# 🔹 Connect to MongoDB Atlas
client = MongoClient(
    "mongodb+srv://campus360:swami056@campus360.nisg0xn.mongodb.net/?retryWrites=true&w=majority&appName=campus360"
    
)
db = client["campus360"]           
users_collection = db["users"]         # Users (student/faculty login)
login_col = db["student"]              # Login info (optional legacy)
records_col = db["student_records"]    # Student dashboard activities
documents_col = db["student_documents"]  # Student uploaded docs
faculty_students_col = db["faculty_students"]  # Faculty-managed students

# 🔹 Home → redirect to login
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

        user = users_collection.find_one({"email": email, "password": password, "role": role})
       
        if user:
            session["user"] = {"name": user["name"], "role": user["role"], "email": user["email"]}
            
            if role == "student":
                return redirect(url_for("student_dashboard"))
            elif role == "faculty":
                return redirect(url_for("faculty_dashboard"))
        else:
            return redirect(url_for("login"))

    return render_template("login.html")

# 🔹 Signup Route
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        password = request.form.get("password")
        role = request.form.get("role")

        existing_user = users_collection.find_one({"email": email})
        if existing_user:
            return "⚠️ User already exists! Please log in."

        users_collection.insert_one({
            "name": name,
            "email": email,
            "password": password,   # ⚠️ plain text for now (use hashing in prod)
            "role": role
        })

        return redirect(url_for("login"))

    return render_template("signup.html")

# 🔹 Student Dashboard
@app.route("/student/dashboard")
def student_dashboard():
    if "user" in session and session["user"]["role"] == "student":
        email = session["user"]["email"]
        # Fetch activities
        activities = list(records_col.find({"email": email}, {"_id": 0}))
        # Fetch documents
        documents = list(documents_col.find({"email": email}, {"_id": 0}))
        return render_template(
            "student_dashboard.html",
            user=session["user"],
            activities=activities,
            documents=documents
        )
    return redirect(url_for("login"))

# 🔹 Upload Student Document
@app.route("/student/upload_document", methods=["POST"])
def upload_document():
    if "user" not in session or session["user"]["role"] != "student":
        return redirect(url_for("login"))

    file = request.files.get("document")
    doc_name = request.form.get("doc_name")  # ✅ custom document name

    if file:
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        file.save(filepath)

        documents_col.insert_one({
            "email": session["user"]["email"],
            "filename": filename,
            "doc_name": doc_name if doc_name else filename  # fallback if name empty
        })

    return redirect(url_for("student_dashboard"))


# 🔹 Add new activity
@app.route("/student/add_activity", methods=["POST"])
def add_activity():
    if "user" not in session or session["user"]["role"] != "student":
        return redirect(url_for("login"))

    title = request.form.get("title")
    activity_type = request.form.get("type")
    date = request.form.get("date")
    description = request.form.get("description")

    records_col.insert_one({
        "email": session["user"]["email"],
        "title": title,
        "type": activity_type,
        "date": date,
        "description": description,
        "status": "Pending"
    })

    return redirect(url_for("student_dashboard"))

# 🔹 Faculty Dashboard
@app.route("/faculty/dashboard", methods=["GET", "POST"])
def faculty_dashboard():
    if "user" in session and session["user"]["role"] == "faculty":
        faculty_email = session["user"]["email"]  # ✅ only this faculty's students
        search_name = request.form.get("search_name")

        query = {"faculty_email": faculty_email}
        if search_name:
            query["name"] = {"$regex": search_name, "$options": "i"}

        students = list(faculty_students_col.find(query, {"_id": 0}))

        # ✅ Attach uploaded documents from student_documents
        for student in students:
            student_docs = list(documents_col.find({"email": student["email"]}, {"_id": 0}))
            student["documents"] = student_docs  # add docs to student object

        return render_template(
            "faculty.html",
            user=session["user"],
            students=students
        )
    return redirect(url_for("login"))



# 🔹 Add Student (by Faculty) - Only by Email
@app.route("/faculty/add_student", methods=["POST"])
def add_student():
    if "user" not in session or session["user"]["role"] != "faculty":
        return redirect(url_for("login"))

    email = request.form.get("email")
    faculty_email = session["user"]["email"]  # ✅ link to faculty

    student_user = users_collection.find_one({"email": email, "role": "student"})
    if not student_user:
        return "⚠️ No student found with this email!"

    # Check if already added for this faculty
    if faculty_students_col.find_one({"email": email, "faculty_email": faculty_email}):
        return "⚠️ Student already exists in your list!"

    faculty_students_col.insert_one({
        "faculty_email": faculty_email,  # ✅ ownership
        "name": student_user["name"],
        "email": email,
        "student_id": student_user.get("student_id", ""),
        "course": student_user.get("course", ""),
        "status": "Active"
    })

    return redirect(url_for("faculty_dashboard"))

# 🔹 Remove a student from faculty's student management
@app.route("/faculty/remove_student/<email>", methods=["POST"])
def remove_student(email):
    if "user" not in session or session["user"]["role"] != "faculty":
        return redirect(url_for("login"))

    faculty_students_col.delete_one({"email": email})

    return redirect(url_for("faculty_dashboard"))



# 🔹 Logout
@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("login"))
# 🔹 Remove Student Document
@app.route("/student/remove_document/<filename>", methods=["POST"])
def remove_document(filename):
    if "user" not in session or session["user"]["role"] != "student":
        return redirect(url_for("login"))

    email = session["user"]["email"]

    # Remove from DB
    documents_col.delete_one({"email": email, "filename": filename})

    # Remove from uploads folder if file exists
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    if os.path.exists(filepath):
        os.remove(filepath)

    return redirect(url_for("student_dashboard"))



if __name__ == "__main__":
    app.run(debug=True)
