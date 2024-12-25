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

    # Relationships
    student_class = db.relationship("Class", back_populates="students")
    scores = db.relationship("ScoreGrade", back_populates="student", cascade="all, delete-orphan")
    fee_payments = db.relationship("FeePayment", back_populates="student", cascade="all, delete-orphan")

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
    class_id = db.Column(db.Integer, db.ForeignKey("classes.id"), nullable=False)
    tuition_fee = db.Column(db.Float, nullable=False, default=0.0)
    transport_fee = db.Column(db.Float, nullable=False, default=0.0)
    books_fee = db.Column(db.Float, nullable=False, default=0.0)
    miscellaneous_fee = db.Column(db.Float, nullable=False, default=0.0)

    # Relationships
    class_ = db.relationship("Class", back_populates="fee_structure")

    def serialize(self):
        return {
            "id": self.id,
            "class_id": self.class_id,
            "class_name": self.class_.name if self.class_ else None,
            "tuition_fee": self.tuition_fee,
            "transport_fee": self.transport_fee,
            "books_fee": self.books_fee,
            "miscellaneous_fee": self.miscellaneous_fee,
            "total_fee": self.tuition_fee + self.transport_fee + self.books_fee + self.miscellaneous_fee,
        }

    def __repr__(self):
        return (
            f"<FeeStructure(id={self.id}, class_id={self.class_id}, "
            f"tuition_fee={self.tuition_fee}, transport_fee={self.transport_fee}, "
            f"books_fee={self.books_fee}, miscellaneous_fee={self.miscellaneous_fee})>"
        )

class FeePayment(db.Model, SerializerMixin):
    __tablename__ = "fee_payments"

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False)
    date_of_payment = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    amount_paid = db.Column(db.Float, nullable=False)
    payment_method = db.Column(db.String, nullable=False)
    transaction_id = db.Column(db.String, nullable=True)

    # Relationships
    student = db.relationship("Student", back_populates="fee_payments")

    def serialize(self):
        return {
            "id": self.id,
            "student_id": self.student_id,
            "student_name": f"{self.student.first_name} {self.student.last_name}" if self.student else None,
            "date_of_payment": self.date_of_payment.strftime("%Y-%m-%d") if self.date_of_payment else None,
            "amount_paid": self.amount_paid,
            "payment_method": self.payment_method,
            "transaction_id": self.transaction_id,
        }

    def __repr__(self):
        return (
            f"<FeePayment(id={self.id}, student_id={self.student_id}, "
            f"amount_paid={self.amount_paid}, payment_method={self.payment_method})>"
        )
