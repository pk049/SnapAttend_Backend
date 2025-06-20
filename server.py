from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient
from bson.objectid import ObjectId
import json
import pandas as pd
import io
from flask import send_file
import tempfile
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet


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
    
    
    
    
    

# Add this new route to your server.py
@app.route('/update_lecture_logs', methods=['POST'])
def update_lecture_logs():
    data = request.get_json()
    
    # Extract required fields
    subject = data.get('subject')
    lecture_number = data.get('lecture_number')
    division = data.get('division')
    class_name = data.get('class_name')
    department = data.get('department')
    updated_logs = data.get('updated_logs', [])
    
    # Format class name according to your existing logic
    if division == 'NA' or division == 'N/A':
        collection_name = f"{class_name}_{department}"
        division = 'NA'
    else:
        collection_name = f"{class_name}{department}{division}"
    
    # Validate data
    if not all([subject, lecture_number, updated_logs]):
        return jsonify({'status': 'fail', 'message': 'Missing required fields'}), 400
    
    # Check if collection exists
    if collection_name not in db2.list_collection_names():
        return jsonify({'status': 'fail', 'message': f'Collection {collection_name} not found'}), 404
    
    try:
        # Get the target collection
        target_collection = db2[collection_name]
        
        # Update each record
        for log in updated_logs:
            prn = log.get('PRN')
            new_status = log.get('status')
            student_id = log.get('_id')
            reason = log.get('reason')  # Get reason field
            
            # Validate student data
            if not (prn and new_status):
                continue
                
            # Build query to find the specific record
            query = {
                "subject": subject,
                "lecture_number": lecture_number,
                "division": division,
                "PRN": prn
            }
            
            # If we have an ObjectId, use it for more precise targeting
            if student_id:
                try:
                    query["_id"] = ObjectId(student_id)
                except:
                    # If ID conversion fails, continue with PRN-based query
                    pass
            
            # Prepare update data
            update_data = {"status": new_status}
            
            # Add reason field for "not considered" status
            if new_status.lower() == 'not considered' and reason:
                update_data["reason"] = reason
            else:
                # Use $unset to remove the reason field if it exists
                target_collection.update_one(
                    query,
                    {"$unset": {"reason": ""}}
                )
            
            # Update the record
            target_collection.update_one(
                query,
                {"$set": update_data}
            )
            
        # Also update the general lecture collection if needed
        # This depends on your data structure
        
        return jsonify({'status': 'success', 'message': 'Attendance updated successfully'})
        
    except Exception as e:
        return jsonify({'status': 'fail', 'message': str(e)}), 500

    
    
# Server endpoint for subject-based report
@app.route('/subject-based-report', methods=['POST'])
def get_subject_based_report():
    data = request.get_json()
    
    # Extract parameters from request
    class_name = data.get('class')
    division = data.get('division')
    subject = data.get('subject')
    department = data.get('department')
    
    print(f"Subject report request - Class: {class_name}, Division: {division}, Subject: {subject}, Department: {department}")
    
    # Validate required fields
    if not all([class_name, subject, department]):  # Division can be NA
        return jsonify({'status': 'fail', 'message': 'Missing required fields'}), 400
    
    # Format collection name consistently with other endpoints
    if division in ('NA', 'N/A'):
        collection_name = f"{class_name}_{department}"
        division = 'NA'
    else:
        collection_name = f"{class_name}_{department}_{division}"
    
    print(f"Using collection name: {collection_name}")
    
    try:
        # Check if subject has any lectures at all
        lecture_count_doc = lecture_count_collection.find_one({
            'class_name': collection_name,
            'subject': subject
        })
        
        if not lecture_count_doc:
            print(f"No lectures found for subject {subject} in collection {collection_name}")
            return jsonify({'status': 'success', 'report': [], 'total_lectures': 0}), 200
        
        total_lectures = lecture_count_doc.get('count', 0)
        
        if total_lectures == 0:
            return jsonify({'status': 'success', 'report': [], 'total_lectures': 0}), 200
        
        # Get student list
        students_cursor = students_collection.find({'class_name': collection_name})
        attendance_collection = db2[collection_name]
        
        attendance_report = []
        
        for student in students_cursor:
            prn = student.get('prn')
            name = student.get('name')
            print(prn,name) 
            
            # Fetch all attendance records for this student and subject
            attendance_records = list(attendance_collection.find({
                'PRN': prn,
                'subject': subject
            }))
            
            present_count = 0
            effective_total = 0
            
            for record in attendance_records:
                status = record.get('status', '').lower()
                if status == 'present':
                    present_count += 1
                if status != 'not considered':
                    effective_total += 1
            
            percentage = 0
            if effective_total > 0:
                percentage = (present_count / effective_total) * 100
            
            attendance_report.append({
                'PRN': prn,
                'name': name,
                'present_count': present_count,
                'total_lectures': effective_total,
                'percentage': round(percentage, 2)
            })
        
        # Sort the report by name for better readability
        attendance_report.sort(key=lambda x: x.get('name', '').lower())
        
        return jsonify({
            'status': 'success',
            'report': attendance_report,
            'subject': subject,
            'class_name': collection_name,
            'total_lectures': total_lectures
        })
    
    except Exception as e:
        print(f"Error in subject-based report: {str(e)}")  # Add detailed logging
        import traceback
        traceback.print_exc()  # Print stack trace for better debugging
        return jsonify({'status': 'fail', 'message': f"Server error: {str(e)}"}), 500









# Add this new download-report endpoint to your server.py

@app.route('/download-report', methods=['POST'])
def download_report():
    data = request.get_json()
    
    # Extract parameters from request
    class_name = data.get('class')
    division = data.get('division')
    subject = data.get('subject')
    department = data.get('department')
    format = data.get('format', 'csv')  # Default to CSV if not specified
    
    # Validate required fields
    if not all([class_name, subject, department]):
        return jsonify({'status': 'fail', 'message': 'Missing required fields'}), 400
    
    # Format collection name consistently with other endpoints
    if division in ('NA', 'N/A'):
        collection_name = f"{class_name}_{department}"
        division = 'NA'
    else:
        collection_name = f"{class_name}_{department}_{division}"
    
    try:
        # First, get the attendance data using the existing function's logic
        lecture_count_doc = lecture_count_collection.find_one({
            'class_name': collection_name,
            'subject': subject
        })
        
        if not lecture_count_doc:
            return jsonify({'status': 'fail', 'message': f'No lectures found for subject {subject}'}), 404
        
        total_lectures = lecture_count_doc.get('count', 0)
        
        if total_lectures == 0:
            return jsonify({'status': 'fail', 'message': 'No lectures recorded for this subject'}), 404
        
        # Get student list
        students_cursor = students_collection.find({'class_name': collection_name})
        attendance_collection = db2[collection_name]
        
        attendance_report = []
        
        for student in students_cursor:
            prn = student.get('prn')
            name = student.get('name')
            
            # Fetch all attendance records for this student and subject
            attendance_records = list(attendance_collection.find({
                'PRN': prn,
                'subject': subject
            }))
            
            present_count = 0
            effective_total = 0
            
            for record in attendance_records:
                status = record.get('status', '').lower()
                if status == 'present':
                    present_count += 1
                if status != 'not considered':
                    effective_total += 1
            
            percentage = 0
            if effective_total > 0:
                percentage = (present_count / effective_total) * 100
            
            attendance_report.append({
                'PRN': prn,
                'Name': name,  # Capitalize column name for report
                'Present': present_count,
                'Total': effective_total,
                'Percentage': round(percentage, 2)
            })
        
        # Sort the report by name for better readability
        attendance_report.sort(key=lambda x: x.get('Name', '').lower())
        
        # Create title for the report
        report_title = f"Attendance Report - {subject} ({class_name} {division})"
        
        # Generate the requested format
        if format.lower() == 'csv':
            # Convert to pandas DataFrame
            df = pd.DataFrame(attendance_report)
            
            # Create a string buffer to hold the CSV data
            csv_buffer = io.StringIO()
            df.to_csv(csv_buffer, index=False)
            
            # Create bytes buffer for the response
            mem = io.BytesIO()
            mem.write(csv_buffer.getvalue().encode('utf-8'))
            mem.seek(0)
            
            # Set filename for download
            filename = f"attendance_report_{class_name}_{division}_{subject}.csv"
            
            return send_file(
                mem,
                mimetype='text/csv',
                download_name=filename,
                as_attachment=True
            )
            
        elif format.lower() == 'pdf':
            # Create a temporary file for the PDF
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
                # Build PDF with reportlab
                doc = SimpleDocTemplate(tmp.name, pagesize=letter)
                styles = getSampleStyleSheet()
                
                # Content elements for the PDF
                elements = []
                
                # Title
                title = Paragraph(report_title, styles['Title'])
                elements.append(title)
                elements.append(Spacer(1, 20))
                
                # Department and class info
                info_text = f"Department: {department} | Class: {class_name} | Division: {division}"
                info = Paragraph(info_text, styles['Normal'])
                elements.append(info)
                elements.append(Spacer(1, 10))
                
                # Extract data for table
                data = [['PRN', 'Name', 'Present/Total', 'Attendance %']]  # Header row
                
                for student in attendance_report:
                    data.append([
                        student['PRN'],
                        student['Name'],
                        f"{student['Present']}/{student['Total']}",
                        f"{student['Percentage']}%"
                    ])
                
                # Create table and set style
                table = Table(data, repeatRows=1)
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ]))
                
                elements.append(table)
                
                # Footer
                elements.append(Spacer(1, 20))
                footer_text = f"Generated on {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}"
                footer = Paragraph(footer_text, styles['Normal'])
                elements.append(footer)
                
                # Build the PDF
                doc.build(elements)
                
                # Set filename for download
                filename = f"attendance_report_{class_name}_{division}_{subject}.pdf"
                
                return send_file(
                    tmp.name,
                    mimetype='application/pdf',
                    download_name=filename,
                    as_attachment=True
                )
        else:
            return jsonify({'status': 'fail', 'message': f'Unsupported format: {format}'}), 400
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'status': 'fail', 'message': f"Server error: {str(e)}"}), 500






    
if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0")


    