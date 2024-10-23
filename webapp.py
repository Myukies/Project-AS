from flask import Flask, render_template, request, redirect, url_for, session
from pymongo import MongoClient
from datetime import datetime
from bson.objectid import ObjectId
import certifi

app = Flask(__name__)
app.secret_key = 'secret_key'

MONGODB_URI = "mongodb+srv://sysadmin:kraFY1B9omw619ik@attendance-system.cumins2.mongodb.net/?retryWrites=true&w=majority&appName=attendance-system"
client = MongoClient(MONGODB_URI, tls=True, tlsAllowInvalidCertificates=True, tlsCAFile=certifi.where())
db = client["attendance_db"]
attendance_collection = db["attendance"]
assignments_collection = db["assignments"]
announcements_collection = db["announcements"]

users = {
    "teacher": "passteacher",
    "student": "passstudent"
}

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username in users and users[username] == password:
            session['user'] = username
            if username == 'teacher':
                return redirect(url_for('admin_home'))
            else:
                return redirect(url_for('student_home'))
        else:
            return "Login Failed. Try again."
    return render_template('login.html')

@app.route('/admin_home', methods=['GET', 'POST'])
def admin_home():
    if 'user' not in session or session['user'] != 'teacher':
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        announcement = request.form.get('announcement')
        if announcement:
            announcements_collection.insert_one({
                "text": announcement,
                "created_at": datetime.now().isoformat()
            })
    
    announcements = list(announcements_collection.find().sort("created_at", -1))
    
    for announcement in announcements:
        created_at = datetime.fromisoformat(announcement["created_at"])
        announcement["created_at"] = created_at.strftime("%B %d, %Y, %I:%M %p")

    return render_template('admin_home.html', announcements=announcements)

@app.route('/student_home')
def student_home():
    if 'user' not in session or session['user'] != 'student':
        return redirect(url_for('login'))
    
    announcements = list(announcements_collection.find().sort("created_at", -1))
    
    for announcement in announcements:
        created_at = datetime.fromisoformat(announcement["created_at"])
        announcement["created_at"] = created_at.strftime("%B %d, %Y, %I:%M %p")

    return render_template('student_home.html', announcements=announcements)

@app.route('/attendance', methods=['GET', 'POST'])
def attendance():
    if 'user' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        selected_date = request.form.get('date')
        attendance_data = list(attendance_collection.find({
            "date": selected_date
        }))
    else:
        attendance_data = list(attendance_collection.find())
    
    for record in attendance_data:
        time_string = record['time']
        time_object = datetime.strptime(time_string, "%H:%M:%S.%f")
        record['time'] = time_object.strftime("%I:%M %p")

    return render_template('attendance.html', attendance_data=attendance_data)

@app.route('/assignments', methods=['GET', 'POST'])
def assignments():
    if 'user' not in session:
        return redirect(url_for('login'))
    
    assignments_data = list(assignments_collection.find())

    for assignment in assignments_data:
        if "status" not in assignment:
            assignment["status"] = "not done"

    if session['user'] == 'teacher' and request.method == 'POST':
        assignment_text = request.form.get('assignment_text')
        deadline = request.form.get('deadline')
        assignments_collection.insert_one({
            "assignment_text": assignment_text,
            "deadline": deadline,
            "created_at": datetime.now().isoformat(),
            "status": "not done",
            "completed_by": []  
        })
        return redirect(url_for('assignments'))

    return render_template('assignments.html', assignments=assignments_data)

@app.route('/mark_done/<assignment_id>', methods=['POST'])
def mark_done(assignment_id):
    if 'user' not in session or session['user'] != 'student':
        return redirect(url_for('login'))

    student_username = session['user']
    
    assignments_collection.update_one(
        {"_id": ObjectId(assignment_id)},
        {
            "$set": {"status": "done"},
            "$addToSet": {"completed_by": student_username}
        }
    )

    return redirect(url_for('assignments'))

@app.route('/delete_announcement/<id>', methods=['POST'])
def delete_announcement(id):
    if 'user' not in session or session['user'] != 'teacher':
        return redirect(url_for('login'))

    announcements_collection.delete_one({"_id": ObjectId(id)})
    return redirect(url_for('admin_home'))

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
