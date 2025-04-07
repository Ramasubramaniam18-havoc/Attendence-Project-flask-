from flask import Flask, render_template, request, redirect, url_for, flash, session
import os
from datetime import datetime
import json
import csv
from io import StringIO

class EnhancedAttendanceSystem:
    def __init__(self):
        """Initialize an empty attendance record."""
        self.records = {}
        self.courses = {}  # Added courses feature

    def add_student(self, student_id: str, name: str, email: str = ""):
        """Add a new student to the attendance system with error handling."""
        if not student_id or not name:
            return False, "Student ID and name cannot be empty."
        if student_id in self.records:
            return False, f"Error: Student ID {student_id} already exists."
        else:
            self.records[student_id] = {
                'name': name, 
                'email': email,
                'attendance': {},
                'courses': []  # Track enrolled courses
            }
            return True, f"Student {name} added successfully."

    def mark_attendance(self, student_id: str, date: str, status: str = "Present", course_id: str = None):
        """Mark a student's attendance for a specific date with validation."""
        if student_id not in self.records:
            return False, f"Error: Student ID {student_id} not found."
        
        # Create attendance by course if course_id is provided
        if course_id:
            if course_id not in self.courses:
                return False, f"Error: Course ID {course_id} not found."
            
            if course_id not in self.records[student_id]['courses']:
                return False, f"Error: Student not enrolled in this course."
                
            attendance_key = f"{date}_{course_id}"
        else:
            attendance_key = date
            
        if attendance_key in self.records[student_id]['attendance']:
            return False, f"Error: Attendance for {self.records[student_id]['name']} on {date} is already recorded."
        
        if status not in ["Present", "Absent", "Late", "Excused"]:  # Added more status options
            return False, "Error: Status must be 'Present', 'Absent', 'Late', or 'Excused'."
        
        self.records[student_id]['attendance'][attendance_key] = status
        return True, f"Attendance marked for {self.records[student_id]['name']} on {date} as {status}."

    def edit_attendance(self, student_id: str, date: str, status: str, course_id: str = None):
        """Edit an existing attendance record."""
        if student_id not in self.records:
            return False, f"Error: Student ID {student_id} not found."
            
        attendance_key = f"{date}_{course_id}" if course_id else date
            
        if attendance_key not in self.records[student_id]['attendance']:
            return False, f"Error: No attendance record found for this date."
            
        if status not in ["Present", "Absent", "Late", "Excused"]:
            return False, "Error: Status must be 'Present', 'Absent', 'Late', or 'Excused'."
            
        self.records[student_id]['attendance'][attendance_key] = status
        return True, f"Attendance updated for {self.records[student_id]['name']} on {date} as {status}."

    def get_attendance(self, student_id: str, course_id: str = None):
        """Retrieve the attendance record of a specific student with validation."""
        if student_id not in self.records:
            return False, f"Error: Student ID {student_id} not found.", {}
        
        if course_id:
            # Filter attendance records for the specific course
            course_attendance = {
                k.split('_')[0]: v for k, v in self.records[student_id]['attendance'].items() 
                if k.endswith(f"_{course_id}")
            }
            return True, "Success", course_attendance
        else:
            # Return all attendance records
            return True, "Success", self.records[student_id]['attendance']

    def get_summary(self, course_id: str = None):
        """Generate a summary of attendance for all students, optionally filtered by course."""
        summary = {}
        
        for student_id, data in self.records.items():
            if course_id and course_id not in data['courses']:
                continue  # Skip students not enrolled in this course
                
            # Filter attendance records for the course if specified
            if course_id:
                attendance_records = {
                    k: v for k, v in data['attendance'].items() 
                    if k.endswith(f"_{course_id}")
                }
            else:
                attendance_records = data['attendance']
                
            total_days = len(attendance_records)
            present_days = sum(1 for status in attendance_records.values() if status == "Present")
            absent_days = sum(1 for status in attendance_records.values() if status == "Absent")
            late_days = sum(1 for status in attendance_records.values() if status == "Late")
            excused_days = sum(1 for status in attendance_records.values() if status == "Excused")
            
            summary[student_id] = {
                'name': data['name'],
                'total_days': total_days,
                'present_days': present_days,
                'absent_days': absent_days,
                'late_days': late_days,
                'excused_days': excused_days,
                'attendance_percentage': (present_days / total_days * 100) if total_days > 0 else 0.0
            }
        return summary
        
    def add_course(self, course_id: str, course_name: str, instructor: str = ""):
        """Add a new course to the system."""
        if not course_id or not course_name:
            return False, "Course ID and name cannot be empty."
        if course_id in self.courses:
            return False, f"Error: Course ID {course_id} already exists."
            
        self.courses[course_id] = {
            'name': course_name,
            'instructor': instructor,
            'schedule': []
        }
        return True, f"Course {course_name} added successfully."
        
    def enroll_student(self, student_id: str, course_id: str):
        """Enroll a student in a course."""
        if student_id not in self.records:
            return False, f"Error: Student ID {student_id} not found."
        if course_id not in self.courses:
            return False, f"Error: Course ID {course_id} not found."
        
        # Check if already enrolled
        if course_id in self.records[student_id]['courses']:
            return False, f"Student already enrolled in this course."
            
        self.records[student_id]['courses'].append(course_id)
        return True, f"Student {self.records[student_id]['name']} enrolled in {self.courses[course_id]['name']}."
    
    def unenroll_student(self, student_id: str, course_id: str):
        """Remove a student from a course."""
        if student_id not in self.records:
            return False, f"Error: Student ID {student_id} not found."
        if course_id not in self.courses:
            return False, f"Error: Course ID {course_id} not found."
            
        if course_id not in self.records[student_id]['courses']:
            return False, f"Student not enrolled in this course."
            
        self.records[student_id]['courses'].remove(course_id)
        return True, f"Student {self.records[student_id]['name']} unenrolled from {self.courses[course_id]['name']}."
    
    def export_attendance_csv(self, course_id: str = None):
        """Export attendance data as CSV."""
        output = StringIO()
        writer = csv.writer(output)
        
        # Create header row
        if course_id:
            writer.writerow(['Student ID', 'Name', 'Email', 'Total Days', 'Present', 'Absent', 'Late', 'Excused', 'Attendance %'])
        else:
            writer.writerow(['Student ID', 'Name', 'Email', 'Courses', 'Total Days', 'Present', 'Absent', 'Late', 'Excused', 'Attendance %'])
        
        # Get summary data
        summary = self.get_summary(course_id)
        
        # Write data rows
        for student_id, data in summary.items():
            student = self.records[student_id]
            if course_id:
                writer.writerow([
                    student_id, student['name'], student['email'],
                    data['total_days'], data['present_days'], data['absent_days'],
                    data['late_days'], data['excused_days'], f"{data['attendance_percentage']:.2f}%"
                ])
            else:
                course_names = [self.courses[c]['name'] for c in student['courses']]
                writer.writerow([
                    student_id, student['name'], student['email'], 
                    ', '.join(course_names),
                    data['total_days'], data['present_days'], data['absent_days'],
                    data['late_days'], data['excused_days'], f"{data['attendance_percentage']:.2f}%"
                ])
                
        return output.getvalue()
    
    def save_data(self, filename):
        """Save the system data to a JSON file."""
        data = {
            'records': self.records,
            'courses': self.courses
        }
        with open(filename, 'w') as f:
            json.dump(data, f)
        return True
        
    def load_data(self, filename):
        """Load the system data from a JSON file."""
        if os.path.exists(filename):
            with open(filename, 'r') as f:
                data = json.load(f)
                self.records = data.get('records', {})
                self.courses = data.get('courses', {})
            return True
        return False

# Initialize Flask application
app = Flask(__name__)
app.secret_key = 'attendance_system_secret_key'  # for flash messages and session

# Create a global instance of the attendance system
attendance_system = EnhancedAttendanceSystem()
data_file = 'attendance_data.json'

# Try to load existing data
if os.path.exists(data_file):
    attendance_system.load_data(data_file)

@app.route('/')
def index():
    """Main dashboard page."""
    return render_template('index.html', 
                          student_count=len(attendance_system.records),
                          course_count=len(attendance_system.courses))

@app.route('/students')
def students():
    """View all students."""
    return render_template('students.html', students=attendance_system.records)

@app.route('/students/add', methods=['GET', 'POST'])
def add_student():
    """Add a new student."""
    if request.method == 'POST':
        student_id = request.form.get('student_id')
        name = request.form.get('name')
        email = request.form.get('email', '')
        
        success, message = attendance_system.add_student(student_id, name, email)
        if success:
            flash(message, 'success')
            attendance_system.save_data(data_file)
            return redirect(url_for('students'))
        else:
            flash(message, 'danger')
    
    return render_template('add_student.html')

@app.route('/courses')
def courses():
    """View all courses."""
    return render_template('courses.html', courses=attendance_system.courses)

@app.route('/courses/add', methods=['GET', 'POST'])
def add_course():
    """Add a new course."""
    if request.method == 'POST':
        course_id = request.form.get('course_id')
        name = request.form.get('name')
        instructor = request.form.get('instructor', '')
        
        success, message = attendance_system.add_course(course_id, name, instructor)
        if success:
            flash(message, 'success')
            attendance_system.save_data(data_file)
            return redirect(url_for('courses'))
        else:
            flash(message, 'danger')
    
    return render_template('add_course.html')

@app.route('/attendance', methods=['GET', 'POST'])
def mark_attendance():
    """Mark attendance for students."""
    if request.method == 'POST':
        student_id = request.form.get('student_id')
        date = request.form.get('date')
        status = request.form.get('status')
        course_id = request.form.get('course_id', None)
        
        success, message = attendance_system.mark_attendance(student_id, date, status, course_id)
        if success:
            flash(message, 'success')
            attendance_system.save_data(data_file)
        else:
            flash(message, 'danger')
    
    return render_template('mark_attendance.html', 
                          students=attendance_system.records,
                          courses=attendance_system.courses,
                          today=datetime.now().strftime('%Y-%m-%d'))

@app.route('/attendance/edit/<student_id>', methods=['GET', 'POST'])
def edit_attendance(student_id):
    """Edit attendance for a student."""
    if student_id not in attendance_system.records:
        flash(f"Student ID {student_id} not found.", 'danger')
        return redirect(url_for('students'))
        
    if request.method == 'POST':
        date = request.form.get('date')
        status = request.form.get('status')
        course_id = request.form.get('course_id', None)
        
        success, message = attendance_system.edit_attendance(student_id, date, status, course_id)
        if success:
            flash(message, 'success')
            attendance_system.save_data(data_file)
            return redirect(url_for('student_details', student_id=student_id))
        else:
            flash(message, 'danger')
    
    # Get the student's attendance records
    success, message, attendance_data = attendance_system.get_attendance(student_id)
    
    return render_template('edit_attendance.html',
                          student=attendance_system.records[student_id],
                          student_id=student_id,
                          attendance=attendance_data,
                          courses=attendance_system.courses)

@app.route('/student/<student_id>')
def student_details(student_id):
    """View details for a specific student."""
    if student_id not in attendance_system.records:
        flash(f"Student ID {student_id} not found.", 'danger')
        return redirect(url_for('students'))
    
    success, message, attendance_data = attendance_system.get_attendance(student_id)
    
    # Get courses this student is enrolled in
    enrolled_courses = []
    for course_id in attendance_system.records[student_id]['courses']:
        if course_id in attendance_system.courses:
            enrolled_courses.append({
                'id': course_id,
                'name': attendance_system.courses[course_id]['name']
            })
    
    return render_template('student_details.html',
                          student=attendance_system.records[student_id],
                          student_id=student_id,
                          attendance=attendance_data,
                          enrolled_courses=enrolled_courses)

@app.route('/courses/<course_id>')
def course_details(course_id):
    """View details for a specific course."""
    if course_id not in attendance_system.courses:
        flash(f"Course ID {course_id} not found.", 'danger')
        return redirect(url_for('courses'))
    
    # Find enrolled students
    enrolled_students = []
    for student_id, student_data in attendance_system.records.items():
        if course_id in student_data['courses']:
            enrolled_students.append({
                'id': student_id,
                'name': student_data['name']
            })
    
    return render_template('course_details.html',
                          course=attendance_system.courses[course_id],
                          course_id=course_id,
                          enrolled_students=enrolled_students)

@app.route('/enroll', methods=['GET', 'POST'])
def enroll_student():
    """Enroll a student in a course."""
    if request.method == 'POST':
        student_id = request.form.get('student_id')
        course_id = request.form.get('course_id')
        
        success, message = attendance_system.enroll_student(student_id, course_id)
        if success:
            flash(message, 'success')
            attendance_system.save_data(data_file)
            return redirect(url_for('student_details', student_id=student_id))
        else:
            flash(message, 'danger')
    
    return render_template('enroll.html',
                          students=attendance_system.records,
                          courses=attendance_system.courses)

@app.route('/unenroll/<student_id>/<course_id>')
def unenroll_student(student_id, course_id):
    """Unenroll a student from a course."""
    success, message = attendance_system.unenroll_student(student_id, course_id)
    if success:
        flash(message, 'success')
        attendance_system.save_data(data_file)
    else:
        flash(message, 'danger')
    
    return redirect(url_for('student_details', student_id=student_id))

@app.route('/summary')
def summary():
    """View attendance summary for all students."""
    course_id = request.args.get('course_id', None)
    summary_data = attendance_system.get_summary(course_id)
    
    return render_template('summary.html',
                          summary=summary_data,
                          courses=attendance_system.courses,
                          selected_course=course_id)

@app.route('/export')
def export_csv():
    """Export attendance data as CSV."""
    course_id = request.args.get('course_id', None)
    csv_data = attendance_system.export_attendance_csv(course_id)
    
    course_name = "all_courses"
    if course_id and course_id in attendance_system.courses:
        course_name = attendance_system.courses[course_id]['name'].lower().replace(' ', '_')
    
    return app.response_class(
        csv_data,
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment;filename=attendance_{course_name}_{datetime.now().strftime("%Y%m%d")}.csv'}
    )

if __name__ == "__main__":
    # Create templates directory if it doesn't exist
    if not os.path.exists('templates'):
        os.makedirs('templates')
    
    # Create basic templates for the application
    # In a real application, you'd want to create proper HTML files
    # Here's a simplified approach to get started
    
    # Create a basic layout template
    with open('templates/layout.html', 'w') as f:
        f.write('''
<!DOCTYPE html>
<html>
<head>
    <title>Attendance Management System</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.2.3/dist/css/bootstrap.min.css">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        .sidebar { min-height: 100vh; background-color: #f8f9fa; }
        .main-content { padding: 20px; }
    </style>
</head>
<body>
    <div class="container-fluid">
        <div class="row">
            <div class="col-md-2 sidebar p-3">
                <h3 class="text-center mb-4">Attendance System</h3>
                <ul class="nav flex-column">
                    <li class="nav-item"><a class="nav-link" href="/">Dashboard</a></li>
                    <li class="nav-item"><a class="nav-link" href="/students">Students</a></li>
                    <li class="nav-item"><a class="nav-link" href="/courses">Courses</a></li>
                    <li class="nav-item"><a class="nav-link" href="/attendance">Mark Attendance</a></li>
                    <li class="nav-item"><a class="nav-link" href="/summary">Summary</a></li>
                    <li class="nav-item"><a class="nav-link" href="/export">Export Data</a></li>
                </ul>
            </div>
            <div class="col-md-10 main-content">
                {% with messages = get_flashed_messages(with_categories=true) %}
                    {% if messages %}
                        {% for category, message in messages %}
                            <div class="alert alert-{{ category }} alert-dismissible fade show">
                                {{ message }}
                                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                            </div>
                        {% endfor %}
                    {% endif %}
                {% endwith %}
                
                {% block content %}{% endblock %}
            </div>
        </div>
    </div>
    
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.2.3/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
        ''')
    
    # Create index/dashboard template
    with open('templates/index.html', 'w') as f:
        f.write('''
{% extends "layout.html" %}
{% block content %}
    <h1 class="mb-4">Attendance Management Dashboard</h1>
    
    <div class="row">
        <div class="col-md-4">
            <div class="card text-center mb-4">
                <div class="card-body">
                    <h5 class="card-title">Students</h5>
                    <p class="card-text display-4">{{ student_count }}</p>
                    <a href="/students" class="btn btn-primary">View Students</a>
                </div>
            </div>
        </div>
        
        <div class="col-md-4">
            <div class="card text-center mb-4">
                <div class="card-body">
                    <h5 class="card-title">Courses</h5>
                    <p class="card-text display-4">{{ course_count }}</p>
                    <a href="/courses" class="btn btn-primary">View Courses</a>
                </div>
            </div>
        </div>
        
        <div class="col-md-4">
            <div class="card text-center mb-4">
                <div class="card-body">
                    <h5 class="card-title">Quick Actions</h5>
                    <div class="d-grid gap-2">
                        <a href="/attendance" class="btn btn-success">Mark Attendance</a>
                        <a href="/summary" class="btn btn-info">View Summary</a>
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <div class="card mt-4">
        <div class="card-header">
            <h5 class="card-title">About This System</h5>
        </div>
        <div class="card-body">
            <p>The Enhanced Attendance Management System allows you to:</p>
            <ul>
                <li>Manage students and courses</li>
                <li>Track attendance with multiple status options</li>
                <li>Generate attendance reports</li>
                <li>Export data to CSV format</li>
            </ul>
            <p>Use the navigation menu on the left to access different features.</p>
        </div>
    </div>
{% endblock %}
        ''')
    
    # Create students template
    with open('templates/students.html', 'w') as f:
        f.write('''
{% extends "layout.html" %}
{% block content %}
    <div class="d-flex justify-content-between align-items-center mb-4">
        <h1>Students</h1>
        <a href="/students/add" class="btn btn-primary">Add New Student</a>
    </div>
    
    <div class="card">
        <div class="card-body">
            <div class="table-responsive">
                <table class="table table-striped">
                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>Name</th>
                            <th>Email</th>
                            <th>Courses</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for student_id, student in students.items() %}
                            <tr>
                                <td>{{ student_id }}</td>
                                <td>{{ student.name }}</td>
                                <td>{{ student.email }}</td>
                                <td>{{ student.courses|length }}</td>
                                <td>
                                    <a href="/student/{{ student_id }}" class="btn btn-sm btn-info">View</a>
                                </td>
                            </tr>
                        {% else %}
                            <tr>
                                <td colspan="5" class="text-center">No students found</td>
                            </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>
    </div>
{% endblock %}
        ''')
    
    # Create add student template
    with open('templates/add_student.html', 'w') as f:
        f.write('''
{% extends "layout.html" %}
{% block content %}
    <h1 class="mb-4">Add New Student</h1>
    
    <div class="card">
        <div class="card-body">
            <form method="post">
                <div class="mb-3">
                    <label for="student_id" class="form-label">Student ID</label>
                    <input type="text" class="form-control" id="student_id" name="student_id" required>
                </div>
                <div class="mb-3">
                    <label for="name" class="form-label">Name</label>
                    <input type="text" class="form-control" id="name" name="name" required>
                </div>
                <div class="mb-3">
                    <label for="email" class="form-label">Email</label>
                    <input type="email" class="form-control" id="email" name="email">
                </div>
                <div class="d-flex justify-content-between">
                    <a href="/students" class="btn btn-secondary">Cancel</a>
                    <button type="submit" class="btn btn-primary">Add Student</button>
                </div>
            </form>
        </div>
    </div>
{% endblock %}
        ''')
    
    # Create courses template
    with open('templates/courses.html', 'w') as f:
        f.write('''
{% extends "layout.html" %}
{% block content %}
    <div class="d-flex justify-content-between align-items-center mb-4">
        <h1>Courses</h1>
        <a href="/courses/add" class="btn btn-primary">Add New Course</a>
    </div>
    
    <div class="card">
        <div class="card-body">
            <div class="table-responsive">
                <table class="table table-striped">
                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>Name</th>
                            <th>Instructor</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for course_id, course in courses.items() %}
                            <tr>
                                <td>{{ course_id }}</td>
                                <td>{{ course.name }}</td>
                                <td>{{ course.instructor }}</td>
                                <td>
                                    <a href="/courses/{{ course_id }}" class="btn btn-sm btn-info">View</a>
                                </td>
                            </tr>
                        {% else %}
                            <tr>
                                <td colspan="4" class="text-center">No courses found</td>
                            </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>
    </div>
{% endblock %}
        ''')
    
    # Create add course template
    with open('templates/add_course.html', 'w') as f:
        f.write('''
{% extends "layout.html" %}
{% block content %}
    <h1 class="mb-4">Add New Course</h1>
    
    <div class="card">
        <div class="card-body">
            <form method="post">
                <div class="mb-3">
                    <label for="course_id" class="form-label">Course ID</label>
                    <input type="text" class="form-control" id="course_id" name="course_id" required>
                </div>
                <div class="mb-3">
                    <label for="name" class="form-label">Course Name</label>
                    <input type="text" class="form-control" id="name" name="name" required>
                </div>
                <div class="mb-3">
                    <label for="instructor" class="form-label">Instructor</label>
                    <input type="text" class="form-control" id="instructor" name="instructor">
                </div>
                <div class="d-flex justify-content-between">
                    <a href="/courses" class="btn btn-secondary">Cancel</a>
                    <button type="submit" class="btn btn-primary">Add Course</button>
                </div>
            </form>
        </div>
    </div>
{% endblock %}
        ''')
    
    # Create mark attendance template
    with open('templates/mark_attendance.html', 'w') as f:
        f.write('''
{% extends "layout.html" %}
{% block content %}
    <h1 class="mb-4">Mark Attendance</h1>
    
    <div class="card">
        <div class="card-body">
            <form method="post">
                <div class="row mb-3">
                    <div class="col-md-6">
                        <label for="student_id" class="form-label">Student</label>
                        <select class="form-select" id="student_id" name="student_id" required>
                            <option value="">Select Student</option>
                            {% for student_id, student in students.items() %}
                                <option value="{{ student_id }}">{{ student_id }} - {{ student.name }}</option>
                            {% endfor %}
                        </select>
                    </div>
                    <div class="col-md-6">
                        <label for="date" class="form-label">Date</label>
                        <input type="date" class="form-control" id="date" name="date" value="{{ today }}" required>
                    </div>
                </div>
                <div class="row mb-3">
                    <div class="col-md-6">
                        <label for="status" class="form-label">Status</label>
                        <select class="form-select" id="status" name="status" required>
                            <option value="Present">Present</option>
                            <option value="Absent">
                <option value="Absent">Absent</option>
                            <option value="Late">Late</option>
                            <option value="Excused">Excused</option>
                        </select>
                    </div>
                    <div class="col-md-6">
                        <label for="course_id" class="form-label">Course (Optional)</label>
                        <select class="form-select" id="course_id" name="course_id">
                            <option value="">All Courses</option>
                            {% for course_id, course in courses.items() %}
                                <option value="{{ course_id }}">{{ course.name }}</option>
                            {% endfor %}
                        </select>
                    </div>
                </div>
                <div class="d-flex justify-content-end">
                    <button type="submit" class="btn btn-primary">Mark Attendance</button>
                </div>
            </form>
        </div>
    </div>
{% endblock %}
        ''')
    
    # Create student details template
    with open('templates/student_details.html', 'w') as f:
        f.write('''
{% extends "layout.html" %}
{% block content %}
    <div class="d-flex justify-content-between align-items-center mb-4">
        <h1>Student Details: {{ student.name }}</h1>
        <a href="/students" class="btn btn-secondary">Back to Students</a>
    </div>
    
    <div class="row">
        <div class="col-md-4">
            <div class="card mb-4">
                <div class="card-header">
                    <h5 class="card-title">Student Information</h5>
                </div>
                <div class="card-body">
                    <p><strong>ID:</strong> {{ student_id }}</p>
                    <p><strong>Name:</strong> {{ student.name }}</p>
                    <p><strong>Email:</strong> {{ student.email if student.email else 'Not provided' }}</p>
                </div>
            </div>
            
            <div class="card mb-4">
                <div class="card-header d-flex justify-content-between align-items-center">
                    <h5 class="card-title mb-0">Enrolled Courses</h5>
                    <a href="/enroll" class="btn btn-sm btn-primary">Enroll</a>
                </div>
                <div class="card-body">
                    {% if enrolled_courses %}
                        <ul class="list-group">
                            {% for course in enrolled_courses %}
                                <li class="list-group-item d-flex justify-content-between align-items-center">
                                    {{ course.name }}
                                    <a href="/unenroll/{{ student_id }}/{{ course.id }}" class="btn btn-sm btn-danger" 
                                       onclick="return confirm('Are you sure you want to unenroll this student?')">Unenroll</a>
                                </li>
                            {% endfor %}
                        </ul>
                    {% else %}
                        <p class="text-muted">Not enrolled in any courses</p>
                    {% endif %}
                </div>
            </div>
        </div>
        
        <div class="col-md-8">
            <div class="card">
                <div class="card-header d-flex justify-content-between align-items-center">
                    <h5 class="card-title mb-0">Attendance Records</h5>
                    <a href="/attendance/edit/{{ student_id }}" class="btn btn-sm btn-primary">Edit Attendance</a>
                </div>
                <div class="card-body">
                    {% if attendance %}
                        <div class="table-responsive">
                            <table class="table table-striped">
                                <thead>
                                    <tr>
                                        <th>Date</th>
                                        <th>Course</th>
                                        <th>Status</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {% for date_key, status in attendance.items() %}
                                        <tr>
                                            {% if '_' in date_key %}
                                                {% set date, course_id = date_key.split('_') %}
                                                <td>{{ date }}</td>
                                                <td>{{ courses[course_id].name if course_id in courses else 'Unknown' }}</td>
                                            {% else %}
                                                <td>{{ date_key }}</td>
                                                <td>All</td>
                                            {% endif %}
                                            <td>
                                                <span class="badge bg-{{ 'success' if status == 'Present' else 'danger' if status == 'Absent' else 'warning' if status == 'Late' else 'secondary' }}">
                                                    {{ status }}
                                                </span>
                                            </td>
                                        </tr>
                                    {% endfor %}
                                </tbody>
                            </table>
                        </div>
                    {% else %}
                        <p class="text-muted">No attendance records found</p>
                    {% endif %}
                </div>
            </div>
        </div>
    </div>
{% endblock %}
        ''')
    
    # Create course details template
    with open('templates/course_details.html', 'w') as f:
        f.write('''
{% extends "layout.html" %}
{% block content %}
    <div class="d-flex justify-content-between align-items-center mb-4">
        <h1>Course Details: {{ course.name }}</h1>
        <a href="/courses" class="btn btn-secondary">Back to Courses</a>
    </div>
    
    <div class="row">
        <div class="col-md-4">
            <div class="card mb-4">
                <div class="card-header">
                    <h5 class="card-title">Course Information</h5>
                </div>
                <div class="card-body">
                    <p><strong>ID:</strong> {{ course_id }}</p>
                    <p><strong>Name:</strong> {{ course.name }}</p>
                    <p><strong>Instructor:</strong> {{ course.instructor if course.instructor else 'Not assigned' }}</p>
                </div>
            </div>
        </div>
        
        <div class="col-md-8">
            <div class="card">
                <div class="card-header d-flex justify-content-between align-items-center">
                    <h5 class="card-title mb-0">Enrolled Students</h5>
                    <a href="/enroll" class="btn btn-sm btn-primary">Enroll Student</a>
                </div>
                <div class="card-body">
                    {% if enrolled_students %}
                        <div class="table-responsive">
                            <table class="table table-striped">
                                <thead>
                                    <tr>
                                        <th>ID</th>
                                        <th>Name</th>
                                        <th>Actions</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {% for student in enrolled_students %}
                                        <tr>
                                            <td>{{ student.id }}</td>
                                            <td>{{ student.name }}</td>
                                            <td>
                                                <a href="/student/{{ student.id }}" class="btn btn-sm btn-info">View</a>
                                                <a href="/unenroll/{{ student.id }}/{{ course_id }}" class="btn btn-sm btn-danger"
                                                   onclick="return confirm('Are you sure you want to unenroll this student?')">Unenroll</a>
                                            </td>
                                        </tr>
                                    {% endfor %}
                                </tbody>
                            </table>
                        </div>
                    {% else %}
                        <p class="text-muted">No students enrolled in this course</p>
                    {% endif %}
                </div>
            </div>
        </div>
    </div>
{% endblock %}
        ''')
    
    # Create edit attendance template
    with open('templates/edit_attendance.html', 'w') as f:
        f.write('''
{% extends "layout.html" %}
{% block content %}
    <div class="d-flex justify-content-between align-items-center mb-4">
        <h1>Edit Attendance for {{ student.name }}</h1>
        <a href="/student/{{ student_id }}" class="btn btn-secondary">Back to Student</a>
    </div>
    
    <div class="card">
        <div class="card-body">
            <form method="post">
                <div class="row mb-3">
                    <div class="col-md-4">
                        <label for="date" class="form-label">Date</label>
                        <input type="date" class="form-control" id="date" name="date" required>
                    </div>
                    <div class="col-md-4">
                        <label for="status" class="form-label">Status</label>
                        <select class="form-select" id="status" name="status" required>
                            <option value="Present">Present</option>
                            <option value="Absent">Absent</option>
                            <option value="Late">Late</option>
                            <option value="Excused">Excused</option>
                        </select>
                    </div>
                    <div class="col-md-4">
                        <label for="course_id" class="form-label">Course (Optional)</label>
                        <select class="form-select" id="course_id" name="course_id">
                            <option value="">All Courses</option>
                            {% for course_id, course in courses.items() %}
                                {% if course_id in student.courses %}
                                    <option value="{{ course_id }}">{{ course.name }}</option>
                                {% endif %}
                            {% endfor %}
                        </select>
                    </div>
                </div>
                <div class="d-flex justify-content-end">
                    <button type="submit" class="btn btn-primary">Update Attendance</button>
                </div>
            </form>
            
            <hr>
            
            <h5 class="mt-4">Current Attendance Records</h5>
            {% if attendance %}
                <div class="table-responsive">
                    <table class="table table-striped">
                        <thead>
                            <tr>
                                <th>Date</th>
                                <th>Course</th>
                                <th>Status</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for date_key, status in attendance.items() %}
                                <tr>
                                    {% if '_' in date_key %}
                                        {% set date, course_id = date_key.split('_') %}
                                        <td>{{ date }}</td>
                                        <td>{{ courses[course_id].name if course_id in courses else 'Unknown' }}</td>
                                    {% else %}
                                        <td>{{ date_key }}</td>
                                        <td>All</td>
                                    {% endif %}
                                    <td>
                                        <span class="badge bg-{{ 'success' if status == 'Present' else 'danger' if status == 'Absent' else 'warning' if status == 'Late' else 'secondary' }}">
                                            {{ status }}
                                        </span>
                                    </td>
                                </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
            {% else %}
                <p class="text-muted">No attendance records found</p>
            {% endif %}
        </div>
    </div>
{% endblock %}
        ''')
    
    # Create enroll template
    with open('templates/enroll.html', 'w') as f:
        f.write('''
{% extends "layout.html" %}
{% block content %}
    <h1 class="mb-4">Enroll Student in Course</h1>
    
    <div class="card">
        <div class="card-body">
            <form method="post">
                <div class="mb-3">
                    <label for="student_id" class="form-label">Student</label>
                    <select class="form-select" id="student_id" name="student_id" required>
                        <option value="">Select Student</option>
                        {% for student_id, student in students.items() %}
                            <option value="{{ student_id }}">{{ student_id }} - {{ student.name }}</option>
                        {% endfor %}
                    </select>
                </div>
                <div class="mb-3">
                    <label for="course_id" class="form-label">Course</label>
                    <select class="form-select" id="course_id" name="course_id" required>
                        <option value="">Select Course</option>
                        {% for course_id, course in courses.items() %}
                            <option value="{{ course_id }}">{{ course.name }}</option>
                        {% endfor %}
                    </select>
                </div>
                <div class="d-flex justify-content-between">
                    <a href="javascript:history.back()" class="btn btn-secondary">Cancel</a>
                    <button type="submit" class="btn btn-primary">Enroll Student</button>
                </div>
            </form>
        </div>
    </div>
{% endblock %}
        ''')
    
    # Create summary template
    with open('templates/summary.html', 'w') as f:
        f.write('''
{% extends "layout.html" %}
{% block content %}
    <div class="d-flex justify-content-between align-items-center mb-4">
        <h1>Attendance Summary</h1>
        <a href="/export{% if selected_course %}?course_id={{ selected_course }}{% endif %}" class="btn btn-success">Export to CSV</a>
    </div>
    
    <div class="card mb-4">
        <div class="card-body">
            <form method="get" class="row g-3">
                <div class="col-auto">
                    <label for="course_id" class="visually-hidden">Course</label>
                    <select class="form-select" id="course_id" name="course_id" onchange="this.form.submit()">
                        <option value="">All Courses</option>
                        {% for course_id, course in courses.items() %}
                            <option value="{{ course_id }}" {% if selected_course == course_id %}selected{% endif %}>
                                {{ course.name }}
                            </option>
                        {% endfor %}
                    </select>
                </div>
            </form>
        </div>
    </div>
    
    <div class="card">
        <div class="card-body">
            {% if summary %}
                <div class="table-responsive">
                    <table class="table table-striped">
                        <thead>
                            <tr>
                                <th>ID</th>
                                <th>Name</th>
                                <th>Total Days</th>
                                <th>Present</th>
                                <th>Absent</th>
                                <th>Late</th>
                                <th>Excused</th>
                                <th>Attendance %</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for student_id, data in summary.items() %}
                                <tr>
                                    <td>{{ student_id }}</td>
                                    <td>{{ data.name }}</td>
                                    <td>{{ data.total_days }}</td>
                                    <td>{{ data.present_days }}</td>
                                    <td>{{ data.absent_days }}</td>
                                    <td>{{ data.late_days }}</td>
                                    <td>{{ data.excused_days }}</td>
                                    <td>{{ "%.2f"|format(data.attendance_percentage) }}%</td>
                                    <td>
                                        <a href="/student/{{ student_id }}" class="btn btn-sm btn-info">Details</a>
                                    </td>
                                </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
            {% else %}
                <p class="text-muted">No data available for summary</p>
            {% endif %}
        </div>
    </div>
{% endblock %}
        ''')
    
    # Run the app
    app.run(debug=True)