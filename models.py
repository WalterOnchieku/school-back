from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from sqlalchemy_serializer import SerializerMixin
from datetime import datetime
from flask_bcrypt import Bcrypt

bcrypt = Bcrypt()
db = SQLAlchemy()

#=================================================================================================
# User Model
#=================================================================================================
class User(db.Model, UserMixin, SerializerMixin):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String, unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="agent")

    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)

    def is_admin(self):
        return self.role == "admin"

    def __repr__(self):
        return f"<User(id={self.id}, username={self.username}, role={self.role})>"

#=================================================================================================
# Student Model
#=================================================================================================

class Student(db.Model, SerializerMixin):
    __tablename__ = "students"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    date_of_birth = db.Column(db.Date, nullable=False)
    gender = db.Column(db.String, nullable=False)
    date_of_admission = db.Column(db.Date, nullable=False)
    class_id = db.Column(db.Integer, db.ForeignKey("classes.id"), nullable=False)
    nemis_no = db.Column(db.Integer, nullable=True)
    assessment_no = db.Column(db.Integer, nullable=True)
    pickup_location_id = db.Column(db.Integer, db.ForeignKey('pickup_locations.id'), nullable=True)

    # Relationships
    student_class = db.relationship("Class", back_populates="students")
    scores = db.relationship("ScoreGrade", back_populates="student", cascade="all, delete-orphan")
    fee_payments = db.relationship("FeePayment", back_populates="student", cascade="all, delete-orphan")
    pickup_location = db.relationship('PickupLocation', backref='students')

    def serialize(self):
        return {
            "id": self.id,
            "name": self.name,
            "date_of_birth": self.date_of_birth.strftime("%Y-%m-%d") if self.date_of_birth else None,
            "gender": self.gender,
            "date_of_admission": self.date_of_admission.strftime("%Y-%m-%d") if self.date_of_admission else None,
            "class_id": self.class_id,
            "nemis_no": self.nemis_no,
            "assessment_no": self.assessment_no,
            "pickup_location_id": self.pickup_location_id,
            "scores": [score.serialize() for score in self.scores],
        }

    def __repr__(self):
        return f"<Student(id={self.id}, name={self.name})>"


#=================================================================================================
# Teacher Model
#=================================================================================================
class Teacher(db.Model, SerializerMixin):
    __tablename__ = "teachers"

    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String, nullable=False)
    last_name = db.Column(db.String, nullable=False)
    date_of_admission = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    subject_id = db.Column(db.Integer, db.ForeignKey("subjects.id"), nullable=True)

    # Relationships
    subject = db.relationship("Subject", back_populates="teachers")
    classes = db.relationship("Class", back_populates="teacher", cascade="all, delete-orphan")

    def serialize(self):
        return {
            "id": self.id,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "date_of_admission": self.date_of_admission.strftime("%Y-%m-%d") if self.date_of_admission else None,
            "subject_id": self.subject_id,
            "subject_name": self.subject.subject_name if self.subject else None,  # Avoid full serialize()
            "class_ids": [class_.id for class_ in self.classes],  # Only IDs
        }

    def __repr__(self):
        return (
            f"<Teacher(id={self.id}, name={self.first_name} {self.last_name}, "
            f"subject_id={self.subject_id})>"
        )

#=================================================================================================
# Class Model
#=================================================================================================
class Class(db.Model):
    __tablename__ = "classes"

    id = db.Column(db.Integer, primary_key=True)
    class_name = db.Column(db.String, unique=True, nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey("teachers.id"), nullable=True)

    # Relationships
    teacher = db.relationship("Teacher", back_populates="classes")
    students = db.relationship("Student", back_populates="student_class", cascade="all, delete-orphan")
    fee_structure = db.relationship("FeeStructure", back_populates="class_", uselist=False)

    def serialize(self):
        return {
            "id": self.id,
            "class_name": self.class_name,
            "teacher_id": self.teacher_id,
            "teacher": self.teacher.serialize() if self.teacher else None,
            "students": [student.serialize() for student in self.students],
        }

    def __repr__(self):
        return f"<Class(id={self.id}, class_name={self.class_name})>"

#=================================================================================================
# Subject Model
#=================================================================================================
class Subject(db.Model):
    __tablename__ = "subjects"

    id = db.Column(db.Integer, primary_key=True)
    subject_name = db.Column(db.String, unique=True, nullable=False)

    # Relationships
    teachers = db.relationship("Teacher", back_populates="subject", cascade="all, delete-orphan")
    score_grades = db.relationship("ScoreGrade", back_populates="subject", cascade="all, delete-orphan")

    def serialize(self):
        return {
            "id": self.id,
            "subject_name": self.subject_name,
            "teachers": [teacher.serialize() for teacher in self.teachers],
            "score_grades": [score.serialize() for score in self.score_grades],
        }

    def __repr__(self):
        return f"<Subject(id={self.id}, subject_name={self.subject_name})>"

#=================================================================================================
# Test Model
#=================================================================================================
class Test(db.Model):
    __tablename__ = "tests"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    term = db.Column(db.String(50), nullable=False)
    year = db.Column(db.Integer, nullable=False)

    # Relationships
    score_grades = db.relationship("ScoreGrade", back_populates="test", cascade="all, delete-orphan")

    def serialize(self):
        return {
            "id": self.id,
            "name": self.name,
            "term": self.term,
            "year": self.year,
        }

    def __repr__(self):
        return f"<Test(id={self.id}, name={self.name}, term={self.term}, year={self.year})>"

#=================================================================================================
# Score Model
#=================================================================================================
class ScoreGrade(db.Model):
    __tablename__ = "score_grades"

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey("subjects.id"), nullable=True)
    test_id = db.Column(db.Integer, db.ForeignKey("tests.id"), nullable=True)
    score = db.Column(db.Float, nullable=True)
    max_score = db.Column(db.Float, default=100.0, nullable=True)
    term = db.Column(db.String(50), nullable=True)
    year = db.Column(db.Integer, nullable=True)

    # Relationships
    student = db.relationship("Student", back_populates="scores")
    subject = db.relationship("Subject", back_populates="score_grades")
    test = db.relationship("Test", back_populates="score_grades")

    def serialize(self):
        return {
            "id": self.id,
            "student_id": self.student_id,
            "subject_id": self.subject_id,
            "test_id": self.test_id,
            "score": self.score,
            "max_score": self.max_score,
            "term": self.term,
            "year": self.year,
        }

    def __repr__(self):
        return (
            f"<ScoreGrade(id={self.id}, student_id={self.student_id}, subject_id={self.subject_id}, "
            f"test_id={self.test_id}, score={self.score}/{self.max_score}, "
            f"term={self.term}, year={self.year})>"
        )


class FeeStructure(db.Model, SerializerMixin): 
    __tablename__ = "fee_structures"

    id = db.Column(db.Integer, primary_key=True)
    class_id = db.Column(db.Integer, db.ForeignKey('classes.id'), nullable=False)
    tuition_fee = db.Column(db.Float, nullable=False, default=0.0)
    books_fee = db.Column(db.Float, nullable=False, default=0.0)
    miscellaneous_fee = db.Column(db.Float, nullable=False, default=0.0)
    boarding_fee = db.Column(db.Float, nullable=True, default=0.0)
    prize_giving_fee = db.Column(db.Float, nullable=True, default=0.0)
    exam_fee = db.Column(db.Float, nullable=True, default=0.0)
    total_fee = db.Column(db.Float, nullable=False, default=0.0)  # New column for total fee

    # Relationships
    class_ = db.relationship("Class", back_populates="fee_structure")

    def serialize_with_class(self):
        return {
            "id": self.id,
            "class_id": self.class_id,
            "class_details": {
                "id": self.class_.id,
                "class_name": self.class_.class_name
            } if self.class_ else None,
            "tuition_fee": self.tuition_fee,
            "books_fee": self.books_fee,
            "miscellaneous_fee": self.miscellaneous_fee,
            "boarding_fee": self.boarding_fee,
            "prize_giving_fee": self.prize_giving_fee,
            "exam_fee": self.exam_fee,
            "total_fee": self.total_fee,
        }

    def __repr__(self):
        return (
            f"<FeeStructure(id={self.id}, class_id={self.class_id}, tuition_fee={self.tuition_fee}, "
            f"books_fee={self.books_fee}, miscellaneous_fee={self.miscellaneous_fee}, total_fee={self.total_fee})>"
        )
    

class PickupLocation(db.Model, SerializerMixin):
    __tablename__ = "pickup_locations"

    id = db.Column(db.Integer, primary_key=True)
    location_name = db.Column(db.String(255), nullable=False)
    transport_fee = db.Column(db.Float, nullable=False, default=0.0)

    # Relationship
    # fee_structures = db.relationship('FeeStructure', back_populates='pickup_location')

    def serialize(self):
        return {
            "id": self.id,
            "location_name": self.location_name,
            "transport_fee": self.transport_fee,
        }

    def __repr__(self):
        return f"<PickupLocation(id={self.id}, location_name={self.location_name}, transport_fee={self.transport_fee})>"


class FeePayment(db.Model, SerializerMixin):
    __tablename__ = "fee_payments"
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    payment_date = db.Column(db.Date, nullable=False)
    term = db.Column(db.String, nullable=False)
    year = db.Column(db.Integer, nullable=False)
    method = db.Column(db.String, nullable=False)
    balance = db.Column(db.Float, nullable=False)

    # Relationship
    student = db.relationship("Student", back_populates="fee_payments")

    def serialize(self):
        return {
            "id": self.id,
            "student_id": self.student_id,
            "amount": self.amount,
            "payment_date": self.payment_date.strftime("%Y-%m-%d") if self.payment_date else None,
            "term": self.term,
            "year": self.year,
            "method": self.method,
            "balance": self.balance,
        }

    def __repr__(self):
        return f"<FeePayment(id={self.id}, student_id={self.student_id}, amount={self.amount})>"
