from flask import Flask, jsonify, render_template, request, redirect, url_for, session, flash
import os
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
users_collection = db["users"]         
login_col = db["student"]              
records_col = db["student_records"]    
documents_col = db["student_documents"]  
faculty_students_col = db["faculty_students"]  
courses_col = db["courses"]  # ✅ courses collection

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
        activities = list(records_col.find({"email": email}, {"_id": 0}))
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
    doc_name = request.form.get("doc_name")  

    if file:
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        file.save(filepath)

        documents_col.insert_one({
            "email": session["user"]["email"],
            "filename": filename,
            "doc_name": doc_name if doc_name else filename  
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
        admin = session["user"]
        faculty_email = session["user"]["email"]

        # Fetch students for this faculty
        students = list(faculty_students_col.find(
            {"faculty_email": faculty_email}, {"_id": 0}
        ))

        # Fetch courses for this faculty
        courses = list(courses_col.find(
            {"faculty_email": faculty_email}, {"_id": 0}
        ))

        # Attach detailed student profiles to courses
        for course in courses:
            detailed_students = []
            for email in course.get("students", []):
                student_user = users_collection.find_one(
                    {"email": email, "role": "student"}, {"_id": 0}
                )
                if student_user:
                    # fetch documents
                    student_docs = list(documents_col.find({"email": email}, {"_id": 0}))
                    student_user["documents"] = student_docs
                    detailed_students.append(student_user)
            course["student_profiles"] = detailed_students   # ✅ attach full student data

        # Search query (if any)
        search_name = request.form.get("search_name", "").strip()

        # Attach documents to faculty’s student list
        for student in students:
            student_docs = list(documents_col.find({"email": student["email"]}, {"_id": 0}))
            student["documents"] = student_docs  

        student_count = len(students)
        course_count = len(courses)

        return render_template(
            "faculty.html",
            user=session["user"],
            students=students,
            courses=courses,
            admin=admin["name"],
            email=admin["email"],
            count=student_count,
            course_count=course_count,
            search_name=search_name
        )
    return redirect(url_for("login"))



# 🔹 Faculty - Add Student
@app.route("/faculty/add_student", methods=["POST"])
def add_student():
    if "user" not in session or session["user"]["role"] != "faculty":
        return redirect(url_for("login"))

    email = request.form.get("email")

    student_user = users_collection.find_one({"email": email, "role": "student"})
    if not student_user:
        flash("⚠️ No student found with this email!", "error")
        return redirect(url_for("faculty_dashboard"))

    if faculty_students_col.find_one({"email": email, "faculty_email": session["user"]["email"]}):
        flash("⚠️ Student already exists in your system!", "warning")
        return redirect(url_for("faculty_dashboard"))

    faculty_students_col.insert_one({
        "name": student_user["name"],
        "email": email,
        "student_id": student_user.get("student_id", ""),
        "course": student_user.get("course", ""),
        "status": "Active",
        "faculty_email": session["user"]["email"]
    })

    flash("✅ Student added successfully!", "success")
    return redirect(url_for("faculty_dashboard"))

# 🔹 Faculty - Add New Course
@app.route("/faculty/add_course", methods=["POST"])
def add_course():
    if "user" not in session or session["user"]["role"] != "faculty":
        return redirect(url_for("login"))

    faculty_email = session["user"]["email"]
    course_name = request.form.get("course_name")

    if not course_name:
        flash("⚠️ Course name is required!", "error")
        return redirect(url_for("faculty_dashboard"))

    courses_col.insert_one({
        "faculty_email": faculty_email,
        "course_name": course_name,
        "students": []
    })

    flash("✅ Course created!", "success")
    return redirect(url_for("faculty_dashboard"))

# 🔹 Faculty - Add Student to Course
@app.route("/faculty/course/<course_name>/add_student", methods=["POST"])
def add_student_to_course(course_name):
    if "user" not in session or session["user"]["role"] != "faculty":
        return redirect(url_for("login"))

    faculty_email = session["user"]["email"]
    email = request.form.get("email")

    student = users_collection.find_one({"email": email, "role": "student"})
    if not student:
        flash("⚠️ Student not found!", "error")
        return redirect(url_for("faculty_dashboard"))

    courses_col.update_one(
        {"faculty_email": faculty_email, "course_name": course_name},
        {"$addToSet": {"students": email}}
    )

    flash("✅ Student added to course!", "success")
    return redirect(url_for("faculty_dashboard"))

# 🔹 Faculty - Remove Student from Course
@app.route("/faculty/course/<course_name>/remove_student/<email>", methods=["POST"])
def remove_student_from_course(course_name, email):
    if "user" not in session or session["user"]["role"] != "faculty":
        return redirect(url_for("login"))

    faculty_email = session["user"]["email"]

    courses_col.update_one(
        {"faculty_email": faculty_email, "course_name": course_name},
        {"$pull": {"students": email}}
    )

    flash("❌ Student removed from course!", "success")
    return redirect(url_for("faculty_dashboard"))

# 🔹 Faculty - Remove Student
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
    documents_col.delete_one({"email": email, "filename": filename})

    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    if os.path.exists(filepath):
        os.remove(filepath)

    return redirect(url_for("student_dashboard"))

# Faculty - Remove a Course
@app.route("/faculty/course/<course_name>/remove", methods=["POST"])
def remove_course(course_name):
    if "user" not in session or session["user"]["role"] != "faculty":
        return redirect(url_for("login"))

    faculty_email = session["user"]["email"]

    courses_col.delete_one({
        "faculty_email": faculty_email,
        "course_name": course_name
    })

    flash("❌ Course removed successfully!", "success")
    return redirect(url_for("faculty_dashboard"))


if __name__ == "__main__":
    app.run(debug=True)
