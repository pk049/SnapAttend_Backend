from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient
from bson.objectid import ObjectId
import json


app = Flask(__name__)
CORS(app)  # Allow requests from Flutter





# Connect to MongoDB
client = MongoClient("mongodb+srv://21uai019:O2OLlukOZ8POqvUg@megaproject-snapattend.tuf5i1s.mongodb.net/")

# Get database --------->
db = client['SA-General']
db2 = client['SA-Attendance']

# Collections ------->
faculty_collection = db['Faculty']
subject_collection = db['subject-class']
lecture_count_collection = db['Lecture_count']
students_collection = db['Students']
genral_lecture_collection = db['Lectures']





#Login Route ------------>

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
            'name': faculty.get('name', 'Unknown'),
            'email': faculty.get('email')
        })
    else:
        return jsonify({'status': 'fail', 'message': 'Invalid email or password'}), 401
    
    
    
    
    

# Getting Subjects   ------------>

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
    
    
    
    
    
    
    

# Attendance summary ----------> 

@app.route('/attendance-summary', methods=['POST'])
def get_attendance_summary():
    data = request.get_json()
    classroom = data.get('class')
    division = data.get('division')

    # Find subjects matching the class
    subjects_cursor = subject_collection.find({'class': classroom})
    course_names = [doc.get('course_name') for doc in subjects_cursor]
    
    if division == "NA":
        pass
    else:
        classroom = classroom + '_' + division
        
    # Find lecture counts per subject
    lecture_count = []    
    for course_name in course_names:
        doc = lecture_count_collection.find_one({'class_name': classroom, 'subject': course_name})
        lecture_count.append(doc.get('count') if doc else 0)

    # Find total number of students in classroom
    total_students = students_collection.count_documents({'class_name': classroom})

    # Calculate total possibilities
    total_possibilities = [count * total_students for count in lecture_count]

    # Collect total students present for each subject
    results = []
    for i, course_name in enumerate(course_names):
        total_students_present = db2[classroom].count_documents({'subject': course_name})
        
        results.append({
            "subject": course_name,
            "total_student_present": total_students_present,
            "total_possibilities": total_possibilities[i]
        })
        print(results)
        
    if not lecture_count:
        return jsonify({'status': 'fail', 'message': 'No lecture count......'}), 401    

    return jsonify(results)





# Lecture History ---------->

@app.route('/get_logs', methods=['POST'])
def get_logs():
    data = request.get_json()

    faculty = data.get("faculty_name")
    date = data.get("date")  # Expecting date in string format e.g. "2024-04-25"
    
    if not (faculty and date):
        return jsonify({'status': 'fail', 'message': 'Missing required fields'}), 400

    try:
        logs = genral_lecture_collection.find({
            "faculty_name": faculty,
            "lecture_date": date,
        })
        
        # Convert MongoDB cursor to list of dictionaries
        logs_list = []
        
        for log in logs:
            logs_list.append({"lecture_number":log.get("lecture_number"),
                              "class_name":log.get("class_name"),
                              "division":log.get("division"),
                              "subject":log.get('subject')
                              })
        
        # ObjectIds are automatically converted by the custom JSONEncoder
        return jsonify({'status': 'success', 'logs': logs_list})
    except Exception as e:
        return jsonify({'status': 'fail', 'message': str(e)}), 500







# Single Lecture Log ---------->

@app.route('/get_lecture_logs', methods=['POST'])
def get_lecture_logs():
    data = request.get_json()

    subject = data.get("subject")
    lecture_number = data.get("lecture_number")
    division = data.get("division")
    class_name = data.get("class_name")
    department = data.get("department")

    # Build collection name
    if division == 'NA' or division =='N/A':
        class_name = f"{class_name}_{department}"
        division='NA'
    else:
        class_name = f"{class_name}_{department}_{division}"

    print("Department:", department)
    print("Collection name:", class_name)

    if class_name not in db2.list_collection_names():
        return jsonify({'status': 'fail', 'message': f'Collection {class_name} not found'}), 404

    if not (subject and lecture_number):
        return jsonify({'status': 'fail', 'message': 'Missing required fields: subject and lecture_number'}), 400

    target_collection = db2[class_name]

    try:
        # Type casting if needed
        if isinstance(lecture_number, str) and lecture_number.isdigit():
            lecture_number = int(lecture_number)

        query = {
            "subject": subject,
            "lecture_number": lecture_number,
            "division": division
        }
        
        logs_cursor = target_collection.find(query)
        
        # Helper function to convert BSON to JSON-serializable format
        def convert_bson_to_json(obj):
            if isinstance(obj, dict):
                return {k: convert_bson_to_json(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_bson_to_json(item) for item in obj]
            elif isinstance(obj, ObjectId):
                return str(obj)
            else:
                return obj
        
        # Process each document
        logs_list = []
        for log in logs_cursor:
            # Convert to JSON-serializable format
            serializable_log = convert_bson_to_json(log)
            logs_list.append(serializable_log)
        
        return jsonify({'status': 'success', 'logs': logs_list})

    except Exception as e:
        print("Error:", str(e))
        return jsonify({'status': 'fail', 'message': str(e)}), 500
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0")