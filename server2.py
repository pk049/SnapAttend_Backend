from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient

app = Flask(__name__)
CORS(app)  # Allow requests from Flutter

# Connect to MongoDB
client = MongoClient("mongodb+srv://21uai019:O2OLlukOZ8POqvUg@megaproject-snapattend.tuf5i1s.mongodb.net/")

# Get database
db = client['SA-General']

# Collections
faculty_collection = db['Faculty']
subject_collection=db['subject-class']





@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    
    email = data.get('email')
    password = data.get('password')

    # Find faculty by email and password
    faculty = faculty_collection.find_one({'email': email, 'password': password})

    if faculty:
        return jsonify({
            'status': 'success',
            'department': faculty.get('department', 'N/A'),
            'name': faculty.get('name', 'Unknown')
        })
    else:
        return jsonify({'status': 'fail', 'message': 'Invalid email or password'}), 401


@app.route('/get_subjects', methods=['POST'])
def get_subjects():
    data = request.get_json()
    
    classroom = data.get('class')
    print(classroom)
    
    # Find subjects matching the class
    subjects_cursor = subject_collection.find({'class': classroom})

    # Extract only the 'course_name' fields
    course_names = [subject.get('course_name') for subject in subjects_cursor]

    if course_names:
        return jsonify({
            'status': 'success',
            'subjects': course_names
        })
    else:
        return jsonify({'status': 'fail', 'message': 'Invalid Classname......'}), 401



if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0")
