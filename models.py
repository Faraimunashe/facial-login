from email.policy import default
from enum import unique
from time import timezone
from unicodedata import name
from flask_login import UserMixin
from app import db
import datetime

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    name = db.Column(db.String(100))
    firstname = db.Column(db.String(100))
    lastname = db.Column(db.String(100))

class Employee(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer)
    firstname = db.Column(db.String(100))
    lastname = db.Column(db.String(100))
    sex = db.Column(db.String(10))
    phone = db.Column(db.String(30))
    natid = db.Column(db.String(30))
    salary = db.Column(db.Integer)

class Intruder(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    period = db.Column(db.DateTime(timezone=True), default=datetime.datetime.now())

class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer)
    arrival = db.Column(db.DateTime(timezone=True), default=datetime.datetime.now())
    depature = db.Column(db.DateTime(timezone=True), default=datetime.datetime.now())
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.datetime.now())
