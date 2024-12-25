from flask import request, jsonify
from flask_restful import Resource
from flask_login import login_user, logout_user, current_user, login_required
from models import User, db

class Register(Resource):
    def post(self):
        data = request.get_json()
        username = data.get("username")
        password = data.get("password")
        role = data.get("role", "agent")

        if not username or not password:
            return {"message": "Username and password are required."}, 400

        if User.query.filter_by(username=username).first():
            return {"message": "Username already exists."}, 409

        user = User(username=username, role=role)
        user.set_password(password)

        db.session.add(user)
        db.session.commit()

        return {"message": "User registered successfully."}, 201


class Login(Resource):
    def post(self):
        data = request.get_json()
        username = data.get("username")
        password = data.get("password")

        if not username or not password:
            return {"message": "Username and password are required."}, 400

        user = User.query.filter_by(username=username).first()
        if not user or not user.check_password(password):
            return {"message": "Invalid username or password."}, 401

        login_user(user)
        return {"message": f"Welcome, {user.username}!"}, 200


class Logout(Resource):
    @login_required
    def post(self):
        logout_user()
        return {"message": "Logged out successfully."}, 200
    
class ProtectedResource(Resource):
    @login_required
    def get(self):
        return {"message": "This is a protected route."}, 200


