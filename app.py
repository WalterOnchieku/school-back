from flask import Flask, request, make_response
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_restful import Resource, Api, reqparse
from models import db, User, Student, Teacher, Class, Subject, ScoreGrade, Test
from datetime import datetime, timedelta
from flask_cors import CORS
from auth import Register, Login, Logout, ProtectedResource
from flask_session import Session
from sqlalchemy import func


# Initialize Flask app
app = Flask(__name__)



# Configurations
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///school.db'  
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config["SESSION_TYPE"] = "filesystem"  # Store sessions in files on the server
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_USE_SIGNER"] = True  # Sign cookies to prevent tampering
app.config["SESSION_KEY_PREFIX"] = "auth_"  # Prefix to avoid conflicts
app.config["SECRET_KEY"] = "your-secure-secret-key"  # Replace with a strong, unique key

# Initialize session
Session(app)

# Initialize extensions
db.init_app(app)
migrate = Migrate(app, db)
api = Api(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"
CORS(app, resources={r"/*": {"origins": "*"}})


# Flask-Login user loader
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

with app.app_context():
    db.create_all()  
#=================================================================================================
# Student endpoints
#=================================================================================================
class StudentListResource(Resource):
    def get(self):
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        
        # Perform the join to include class_name
        students = (
            db.session.query(
                Student.id,
                Student.name,
                Student.date_of_birth,
                Student.gender,
                Student.date_of_admission,
                Student.class_id,
                Class.class_name,  # Include class_name from the Class model
                Student.nemis_no,
                Student.assessment_no
            )
            .join(Class, Student.class_id == Class.id)  # Join on class_id
            .paginate(page=page, per_page=per_page)
        )

        # Construct the response
        return {
            "students": [
                {
                    "id": student.id,
                    "name": student.name,
                    "date_of_birth": student.date_of_birth.strftime("%Y-%m-%d"),
                    "gender": student.gender,
                    "date_of_admission": student.date_of_admission.strftime("%Y-%m-%d"),
                    "class_id": student.class_id,
                    "class_name": student.class_name,  # Include class_name in response
                    "nemis_no": student.nemis_no,
                    "assessment_no": student.assessment_no,
                }
                for student in students.items
            ],
            "total": students.total,
            "pages": students.pages,
            "current_page": students.page,
        }, 200


    def post(self):
        """Create a new student."""
        data = request.json
        try:
            new_student = Student(
                name=data["name"],
                date_of_birth=datetime.strptime(data["date_of_birth"], "%Y-%m-%d").date(),  # Convert to date
                gender=data["gender"],
                date_of_admission=datetime.strptime(data["date_of_admission"], "%Y-%m-%d").date(),  # Convert to date
                class_id=data["class_id"],
                nemis_no=data["nemis_no"],
                assessment_no=data["assessment_no"]
            )
            db.session.add(new_student)
            db.session.commit()
            return new_student.serialize(), 201
        except Exception as e:
            db.session.rollback()
            return {"message": f"Error creating student: {str(e)}"}, 400

class StudentResource(Resource):
    def get(self, student_id):
        """Retrieve a single student by ID."""
        student = Student.query.get(student_id)
        if not student:
            return {"message": "Student not found"}, 404
        return student.serialize(), 200

    def put(self, student_id):
        """Update an existing student."""
        student = Student.query.get(student_id)
        if not student:
            return {"message": "Student not found"}, 404

        data = request.json
        try:
            student.name = data.get("name", student.name)
            if "date_of_birth" in data:
                student.date_of_birth = datetime.strptime(data["date_of_birth"], "%Y-%m-%d").date()
            student.gender = data.get("gender", student.gender)
            if "date_of_admission" in data:
                student.date_of_admission = datetime.strptime(data["date_of_admission"], "%Y-%m-%d").date()
            student.class_id = data.get("class_id", student.class_id)
            student.nemis_no = data.get("nemis_no", student.nemis_no)
            student.assessment_no = data.get("assessment_no", student.assessment_no)
            
            db.session.commit()
            return student.serialize(), 200
        except Exception as e:
            db.session.rollback()
            return {"message": f"Error updating student: {str(e)}"}, 400

    def delete(self, student_id):
        """Delete a student."""
        student = Student.query.get(student_id)
        if not student:
            return {"message": "Student not found"}, 404
        try:
            db.session.delete(student)
            db.session.commit()
            return {"message": "Student deleted successfully"}, 200
        except Exception as e:
            db.session.rollback()
            return {"message": f"Error deleting student: {str(e)}"}, 400


api.add_resource(StudentListResource, "/students")
api.add_resource(StudentResource, "/students/<int:student_id>")

#=================================================================================================
# Teacher endpoints
#=================================================================================================
from sqlalchemy.orm import joinedload
from flask import request
from flask_restful import Resource
from datetime import datetime
from models import Teacher, Subject, db

class TeacherListResource(Resource):
    def get(self):
        """Retrieve a paginated list of teachers with their associated subjects."""
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        search = request.args.get('search', '', type=str)

        query = Teacher.query

        # Add search filter if search query is provided
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                (Teacher.first_name.ilike(search_term)) | 
                (Teacher.last_name.ilike(search_term))
            )

        # Use joinedload for eager loading subject data
        teachers = query.options(joinedload(Teacher.subject)).paginate(page=page, per_page=per_page)

        return {
            "teachers": [
                {
                    **teacher.serialize(),
                    "subject_name": teacher.subject.subject_name if teacher.subject else None,
                }
                for teacher in teachers.items
            ],
            "total": teachers.total,
            "pages": teachers.pages,
            "current_page": teachers.page,
        }, 200

    def post(self):
        """Create a new teacher."""
        data = request.json
        try:
            new_teacher = Teacher(
                first_name=data["first_name"],
                last_name=data["last_name"],
                date_of_admission=datetime.strptime(data["date_of_admission"], "%Y-%m-%d").date(),
                subject_id=data.get("subject_id"),  # Associate with subject if provided
            )
            db.session.add(new_teacher)
            db.session.commit()
            return {
                **new_teacher.serialize(),
                "subject_name": new_teacher.subject.subject_name if new_teacher.subject else None,
            }, 201
        except Exception as e:
            db.session.rollback()
            return {"message": f"Error creating teacher: {str(e)}"}, 400


class TeacherResource(Resource):
    def get(self, teacher_id):
        """Retrieve a single teacher by ID with associated subject."""
        teacher = Teacher.query.options(joinedload(Teacher.subject)).get(teacher_id)
        if not teacher:
            return {"message": "Teacher not found"}, 404
        return {
            **teacher.serialize(),
            "subject_name": teacher.subject.subject_name if teacher.subject else None,
        }, 200

    def put(self, teacher_id):
        """Update an existing teacher."""
        teacher = Teacher.query.get(teacher_id)
        if not teacher:
            return {"message": "Teacher not found"}, 404

        data = request.json
        try:
            teacher.first_name = data.get("first_name", teacher.first_name)
            teacher.last_name = data.get("last_name", teacher.last_name)
            teacher.date_of_admission = datetime.strptime(
                data.get("date_of_admission", teacher.date_of_admission.strftime('%Y-%m-%d')), 
                '%Y-%m-%d'
            ).date()
            teacher.subject_id = data.get("subject_id", teacher.subject_id)

            db.session.commit()
            return {
                **teacher.serialize(),
                "subject_name": teacher.subject.subject_name if teacher.subject else None,
            }, 200
        except Exception as e:
            db.session.rollback()
            return {"message": f"Error updating teacher: {str(e)}"}, 400

    def delete(self, teacher_id):
        """Delete a teacher."""
        teacher = Teacher.query.get(teacher_id)
        if not teacher:
            return {"message": "Teacher not found"}, 404
        try:
            db.session.delete(teacher)
            db.session.commit()
            return {"message": "Teacher deleted successfully"}, 200
        except Exception as e:
            db.session.rollback()
            return {"message": f"Error deleting teacher: {str(e)}"}, 400


# Add resource endpoints to the API
api.add_resource(TeacherListResource, "/teachers")
api.add_resource(TeacherResource, "/teachers/<int:teacher_id>")


#=================================================================================================
# Class endpoints
#=================================================================================================

class ClassListResource(Resource):
    def get(self):
        """Retrieve all classes."""
        classes = Class.query.all()
        response_body = [class_.serialize() for class_ in classes]
        return make_response(response_body, 200)

    def post(self):
        """Create a new class."""
        data = request.get_json()
        new_class = Class(
            class_name=data['class_name'],
            teacher_id=data.get('teacher_id')
        )
        try:
            db.session.add(new_class)
            db.session.commit()
            response_body = {
                "message": "Class created successfully!",
                "class": new_class.serialize()
            }
            return make_response(response_body, 201)
        except Exception as e:
            db.session.rollback()
            return make_response({"error": str(e)}, 400)


class ClassResource(Resource):
    def get(self, class_id):
        """Retrieve a specific class by ID."""
        class_ = Class.query.get_or_404(class_id)
        response_body = class_.serialize()
        return make_response(response_body, 200)

    def put(self, class_id):
        """Update class details."""
        class_ = Class.query.get_or_404(class_id)
        data = request.get_json()
        try:
            class_.class_name = data.get('class_name', class_.class_name)
            class_.teacher_id = data.get('teacher_id', class_.teacher_id)
            db.session.commit()
            response_body = {
                "message": "Class updated successfully!",
                "class": class_.serialize()
            }
            return make_response(response_body, 200)
        except Exception as e:
            db.session.rollback()
            return make_response({"error": str(e)}, 400)

    def delete(self, class_id):
        """Delete a class."""
        class_ = Class.query.get_or_404(class_id)
        try:
            db.session.delete(class_)
            db.session.commit()
            response_body = {"message": "Class deleted successfully!"}
            return make_response(response_body, 200)
        except Exception as e:
            db.session.rollback()
            return make_response({"error": str(e)}, 400)



# Registering resources
api.add_resource(ClassListResource, '/classes')  # /classes for listing and creating
api.add_resource(ClassResource, '/classes/<int:class_id>')  # /classes/<id> for specific operations

#=================================================================================================
# Subject endpoints
#=================================================================================================
class SubjectListResource(Resource):
    def get(self):
        """Retrieve all subjects."""
        subjects = Subject.query.all()
        return [subject.serialize() for subject in subjects], 200

    def post(self):
        """Create a new subject."""
        data = request.json
        try:
            new_subject = Subject(
                subject_name=data["subject_name"]
            )
            db.session.add(new_subject)
            db.session.commit()
            return new_subject.serialize(), 201
        except Exception as e:
            db.session.rollback()
            return {"message": f"Error creating subject: {str(e)}"}, 400


class SubjectResource(Resource):
    def get(self, subject_id):
        """Retrieve a single subject by ID."""
        subject = Subject.query.get(subject_id)
        if not subject:
            return {"message": "Subject not found"}, 404
        return subject.serialize(), 200

    def put(self, subject_id):
        """Update an existing subject."""
        subject = Subject.query.get(subject_id)
        if not subject:
            return {"message": "Subject not found"}, 404

        data = request.json
        try:
            subject.subject_name = data.get("subject_name", subject.subject_name)
            db.session.commit()
            return subject.serialize(), 200
        except Exception as e:
            db.session.rollback()
            return {"message": f"Error updating subject: {str(e)}"}, 400

    def delete(self, subject_id):
        """Delete a subject."""
        subject = Subject.query.get(subject_id)
        if not subject:
            return {"message": "Subject not found"}, 404
        try:
            db.session.delete(subject)
            db.session.commit()
            return {"message": "Subject deleted successfully"}, 200
        except Exception as e:
            db.session.rollback()
            return {"message": f"Error deleting subject: {str(e)}"}, 400

api.add_resource(SubjectListResource, "/subjects")
api.add_resource(SubjectResource, "/subjects/<int:subject_id>")

#=================================================================================================
# Score endpoints
#=================================================================================================

class ScoreGradeResource(Resource):
    parser = reqparse.RequestParser()
    parser.add_argument('student_id', type=int, required=True, help="Student ID is required")
    parser.add_argument('subject_id', type=int, required=True, help="Subject ID is required")
    parser.add_argument('test_id', type=int, required=False, help="Test ID is optional")
    parser.add_argument('score', type=float, required=False, help="Score is optional")
    parser.add_argument('max_score', type=float, default=100.0, help="Maximum score")
    parser.add_argument('term', type=str, required=False, help="Term is optional")
    parser.add_argument('year', type=int, required=False, help="Year is optional")

    def get(self, score_grade_id):
        score_grade = db.session.query(
            ScoreGrade,
            Student.name.label("student_name"),
            Subject.subject_name.label("subject_name")
        ).join(
            Student, ScoreGrade.student_id == Student.id
        ).join(
            Subject, ScoreGrade.subject_id == Subject.id
        ).filter(ScoreGrade.id == score_grade_id).first()

        if not score_grade:
            return {"message": "ScoreGrade not found"}, 404

        sg_data = score_grade.ScoreGrade.serialize()
        sg_data["student_name"] = score_grade.student_name
        sg_data["subject_name"] = score_grade.subject_name
        return sg_data, 200

    def delete(self, score_grade_id):
        score_grade = ScoreGrade.query.get(score_grade_id)
        if not score_grade:
            return {"message": "ScoreGrade not found"}, 404

        db.session.delete(score_grade)
        db.session.commit()
        return {"message": "ScoreGrade deleted successfully"}, 200

    def put(self, score_grade_id):
        score_grade = ScoreGrade.query.get(score_grade_id)
        if not score_grade:
            return {"message": "ScoreGrade not found"}, 404

        data = ScoreGradeResource.parser.parse_args()
        score_grade.student_id = data['student_id']
        score_grade.subject_id = data['subject_id']
        score_grade.test_id = data['test_id']
        score_grade.score = data['score']
        score_grade.max_score = data['max_score']
        score_grade.term = data['term']
        score_grade.year = data['year']

        db.session.commit()
        return score_grade.serialize(), 200


class ScoreGradeListResource(Resource):
    def get(self):
        score_grades = db.session.query(
            ScoreGrade,
            Student.name.label("student_name"),
            Subject.subject_name.label("subject_name")
        ).join(
            Student, ScoreGrade.student_id == Student.id
        ).join(
            Subject, ScoreGrade.subject_id == Subject.id
        ).all()

        results = []
        for sg, student_name, subject_name in score_grades:
            sg_data = sg.serialize()
            sg_data["student_name"] = student_name
            sg_data["subject_name"] = subject_name
            results.append(sg_data)

        return results, 200

    def post(self):
        data = ScoreGradeResource.parser.parse_args()

        # Create a new ScoreGrade object
        score_grade = ScoreGrade(
            student_id=data['student_id'],
            subject_id=data['subject_id'],
            test_id=data['test_id'],
            score=data['score'],
            max_score=data['max_score'],
            term=data['term'],
            year=data['year']
        )

        db.session.add(score_grade)
        db.session.commit()
        return score_grade.serialize(), 201


# Add Resources to API
api.add_resource(ScoreGradeListResource, '/score_grades')
api.add_resource(ScoreGradeResource, '/score_grades/<int:score_grade_id>')

#=================================================================================================
# Report endpoints
#=================================================================================================

class StudentReportResource(Resource):
    def get(self, student_id, term, year):
        # Fetch scores for the specific student, term, and year
        scores = db.session.query(
            ScoreGrade, Subject.subject_name
        ).join(
            Subject, ScoreGrade.subject_id == Subject.id
        ).filter(
            ScoreGrade.student_id == student_id,
            ScoreGrade.term == term,
            ScoreGrade.year == year
        ).all()

        if not scores:
            return {"message": "No scores found for the specified criteria"}, 404

        # Prepare the report data
        report = []
        total_percentage = 0
        count = 0

        for score_grade, subject_name in scores:
            # Dynamically calculate grade based on score and max_score
            grade = None
            if score_grade.score is not None and score_grade.max_score > 0:
                percentage = (score_grade.score / score_grade.max_score) * 100
                grade = self.calculate_grade(percentage)
                total_percentage += percentage
                count += 1

            report.append({
                "subject_name": subject_name,
                "score": score_grade.score,
                "max_score": score_grade.max_score,
                "grade": grade
            })

        # Calculate the average percentage and grade
        average_percentage = total_percentage / count if count > 0 else None
        average_grade = self.calculate_grade(average_percentage) if average_percentage is not None else None

        return {
            "student_id": student_id,
            "term": term,
            "year": year,
            "average_percentage": average_percentage,
            "average_grade": average_grade,
            "subjects": report
        }, 200

    @staticmethod
    def calculate_grade(percentage):
    
        if percentage is None:
            return None
        if percentage >= 80:
            return "A"
        elif percentage >= 75:
            return "A-"
        elif percentage >= 70:
            return "B+"
        elif percentage >= 65:
            return "B"
        elif percentage >= 60:
            return "B-"
        elif percentage >= 55:
            return "C+"
        elif percentage >= 50:
            return "C"
        elif percentage >= 45:
            return "C-"
        elif percentage >= 40:
            return "D+"
        elif percentage >= 35:
            return "D"
        elif percentage >= 30:
            return "D-"
        else:
            return "E"

api.add_resource(StudentReportResource, '/report/<int:student_id>/<string:term>/<int:year>')

#=================================================================================================
# Dashboard endpoints
#=================================================================================================

class DashboardSummaryResource(Resource):
    def get(self):
        """Retrieve summary data for the dashboard."""
        total_students = Student.query.count()
        total_teachers = Teacher.query.count()
        total_classes = Class.query.count()
        total_subjects = Subject.query.count()
        return {
            "total_students": total_students,
            "total_teachers": total_teachers,
            "total_classes": total_classes,
            "total_subjects": total_subjects,
        }, 200


class DashboardNotificationsResource(Resource):
    def get(self):
        """Retrieve recently admitted students as notifications."""
        recent_students = (
            Student.query.order_by(Student.date_of_admission.desc())
            .limit(5)
            .all()
        )
        return [
            {
                "id": student.id,
                "name": student.name,
                "date_of_admission": student.date_of_admission.strftime("%Y-%m-%d"),
            }
            for student in recent_students
        ], 200


class DashboardEnrollmentChartResource(Resource):
    def get(self):
        """Retrieve enrollment data grouped by month for the past year."""
        current_date = datetime.utcnow()
        one_year_ago = current_date - timedelta(days=365)

        data = (
            Student.query.with_entities(
                func.strftime('%Y-%m', Student.date_of_admission).label('month'),
                func.count().label('count'),
            )
            .filter(Student.date_of_admission >= one_year_ago)
            .group_by(func.strftime('%Y-%m', Student.date_of_admission))
            .order_by('month')
            .all()
        )

        chart_data = [{"month": month, "count": count} for month, count in data]
        return chart_data, 200


class DashboardSubjectPopularityChartResource(Resource):
    def get(self):
        """Retrieve data for subject popularity."""
        data = (
            ScoreGrade.query.with_entities(
                Subject.subject_name,
                func.count(ScoreGrade.student_id).label('count'),
            )
            .join(Subject, Subject.id == ScoreGrade.subject_id)
            .group_by(Subject.subject_name)
            .order_by(func.count(ScoreGrade.student_id).desc())
            .all()
        )

        chart_data = [{"subject_name": subject_name, "count": count} for subject_name, count in data]
        return chart_data, 200


class DashboardQuickLinksResource(Resource):
    def get(self):
        """Retrieve quick links metadata."""
        return {
            "quick_links": [
                {"name": "Manage Students", "url": "/students", "icon": "student-icon"},
                {"name": "Manage Teachers", "url": "/teachers", "icon": "teacher-icon"},
                {"name": "Manage Classes", "url": "/classes", "icon": "class-icon"},
                {"name": "View Reports", "url": "/reports", "icon": "report-icon"},
            ]
        }, 200


api.add_resource(DashboardSummaryResource, "/dashboard/summary")
api.add_resource(DashboardNotificationsResource, "/dashboard/notifications")
api.add_resource(DashboardEnrollmentChartResource, "/dashboard/chart/enrollment")
api.add_resource(DashboardSubjectPopularityChartResource, "/dashboard/chart/subject-popularity")
api.add_resource(DashboardQuickLinksResource, "/dashboard/quick-links")

#---------------------------------------------------------
#Auth resources added here
#---------------------------------------------------------
api.add_resource(Register, '/auth/register')
api.add_resource(Login, '/auth/login')
api.add_resource(Logout, '/auth/logout')
api.add_resource(ProtectedResource, "/protected")



if __name__ == '__main__':
    app.run(debug=True)