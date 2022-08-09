import face_recognition
from flask import Flask, jsonify, request, redirect, render_template, url_for, flash, make_response
from flask_session import Session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
from flask_wkhtmltopdf import Wkhtmltopdf
import datetime
import os


# You can change this to any folder on your system
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

db = SQLAlchemy()
app = Flask(__name__)
wkhtmltopdf = Wkhtmltopdf(app)
app.config['SECRET_KEY'] = 'ProfessorSecret'
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://root:''@localhost/facial'

db.init_app(app)

login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

#from .models import User
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

class Attendance(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer)
    arrival = db.Column(db.DateTime(timezone=True), default=datetime.datetime.now())
    depature = db.Column(db.DateTime(timezone=True), default=datetime.datetime.now())
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.datetime.now())

# with app.app_context():
#     db.create_all()

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/login', methods=['GET'])
def login():
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
@login_required
def register_employee():
    if request.method == "POST":
        if "file1" not in request.files:
            return "there is no file1 in form!"
        file1 = request.files["file1"]
        firstname = request.form.get('firstname')
        lastname = request.form.get('lastname')
        name = request.form.get('name')
        email = request.form.get('email')
        sex = request.form.get('sex')
        natid = request.form.get('natid')
        password = request.form.get('password')
        phone = request.form.get('phone')
        salary = request.form.get('salary')

        user = User.query.filter_by(email=email).first()
        if user:
            flash('Email already exists!')
            return redirect(url_for('register_employee'))
        new_user = User(email=email, password=generate_password_hash(password, method='sha256'), name=name, firstname=firstname, lastname=lastname)
        db.session.add(new_user)
        db.session.commit()

        new_employee = Employee(user_id=new_user.id, firstname=firstname, lastname=lastname, sex=sex, phone=phone, natid=natid, salary=salary)
        db.session.add(new_employee)

        db.session.commit()

        extension = file1.filename.split('.')[1]
        path = os.path.join("static/known_faces", str(new_user.id) +"."+ extension)
        file1.save(path)
        flash('Successfully register new employee!')
        return redirect(url_for('register_employee'))
    return render_template('register.html')

@app.route('/home', methods=['GET'])
@login_required
def home():
    attends = db.engine.execute("SELECT attendance.id, attendance.arrival, attendance.depature, employee.firstname, employee.lastname FROM attendance JOIN employee ON employee.user_id = attendance.user_id ORDER BY created_at DESC")
    
    return render_template('home.html', attends=attends)

@app.route('/attendance/report', methods=['GET'])
@login_required
def report():
    return render_template('report.html', download=True, save=False, name='hello')

@app.route('/employees', methods=['GET'])
@login_required
def employees():
    employs = Employee.query.all()
    return render_template('employees.html', employs=employs)


@app.route('/notifications', methods=['GET'])
@login_required
def notifications():
    notifs = Intruder.query.all()
    return render_template('notifications.html', notifs=notifs)


@app.route('/attend', methods=['GET', 'POST'])
@login_required
def attend():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('Image not posted')
            return redirect(url_for(login))

        file = request.files['file']

        if file.filename == '':
            flash('file name is empty')
            return redirect(url_for(login))

        if file and allowed_file(file.filename):
            # The image file seems valid! Detect faces and return the result.
            response = detect_faces_in_image_attend(file)
            print(response['is_picture_known'])
            if response['is_picture_known'] == True:
                return jsonify(response)
            return jsonify(response)
    return render_template('attend.html')

@app.route('/', methods=['GET', 'POST'])
def index():
    # Check if a valid image file was uploaded
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('Image not posted')
            return redirect(url_for(login))

        file = request.files['file']

        if file.filename == '':
            flash('file name is empty')
            return redirect(url_for(login))

        if file and allowed_file(file.filename):
            # The image file seems valid! Detect faces and return the result.
            response = detect_faces_in_image(file)
            print(response['is_picture_known'])
            if response['is_picture_known'] == True:
                #login_user(response['user_id'])
                return jsonify(response)
            flash('INVALID FACIAL LOGIN')
            return jsonify(response)

    # If no valid image file was uploaded, show the file upload form:
    return render_template('login.html')


@app.route('/logout', methods=['GET'])
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))


def detect_faces_in_image(file_stream):
    directory = 'static/known_faces'
    known_face_encoding = []
    known_face_names = []
    
    # iterate over files in
    # that directory
    for filename in os.listdir(directory):
        f = os.path.join(directory, filename)
        # checking if it is a file
        if os.path.isfile(f):
            obama_image = face_recognition.load_image_file(f)
            obama_face_encoding = face_recognition.face_encodings(obama_image)[0]
            known_face_encoding.append(obama_face_encoding)

            known_user_id = filename.split('.')[0]
            user = User.query.filter_by(id=known_user_id).first()
            known_face_names.append(user)
    # # Pre-calculated face encoding of Obama generated with face_recognition.face_encodings(img)
    # known_face_encoding = [-0.09634063,  0.12095481, -0.00436332, -0.07643753,  0.0080383,
    #                         0.01902981, -0.07184699, -0.09383309,  0.18518871, -0.09588896,
    #                         0.23951106,  0.0986533 , -0.22114635, -0.1363683 ,  0.04405268,
    #                         0.11574756, -0.19899382, -0.09597053, -0.11969153, -0.12277931,
    #                         0.03416885, -0.00267565,  0.09203379,  0.04713435, -0.12731361,
    #                        -0.35371891, -0.0503444 , -0.17841317, -0.00310897, -0.09844551,
    #                        -0.06910533, -0.00503746, -0.18466514, -0.09851682,  0.02903969,
    #                        -0.02174894,  0.02261871,  0.0032102 ,  0.20312519,  0.02999607,
    #                        -0.11646006,  0.09432904,  0.02774341,  0.22102901,  0.26725179,
    #                         0.06896867, -0.00490024, -0.09441824,  0.11115381, -0.22592428,
    #                         0.06230862,  0.16559327,  0.06232892,  0.03458837,  0.09459756,
    #                        -0.18777156,  0.00654241,  0.08582542, -0.13578284,  0.0150229 ,
    #                         0.00670836, -0.08195844, -0.04346499,  0.03347827,  0.20310158,
    #                         0.09987706, -0.12370517, -0.06683611,  0.12704916, -0.02160804,
    #                         0.00984683,  0.00766284, -0.18980607, -0.19641446, -0.22800779,
    #                         0.09010898,  0.39178532,  0.18818057, -0.20875394,  0.03097027,
    #                        -0.21300618,  0.02532415,  0.07938635,  0.01000703, -0.07719778,
    #                        -0.12651891, -0.04318593,  0.06219772,  0.09163868,  0.05039065,
    #                        -0.04922386,  0.21839413, -0.02394437,  0.06173781,  0.0292527 ,
    #                         0.06160797, -0.15553983, -0.02440624, -0.17509389, -0.0630486 ,
    #                         0.01428208, -0.03637431,  0.03971229,  0.13983178, -0.23006812,
    #                         0.04999552,  0.0108454 , -0.03970895,  0.02501768,  0.08157793,
    #                        -0.03224047, -0.04502571,  0.0556995 , -0.24374914,  0.25514284,
    #                         0.24795187,  0.04060191,  0.17597422,  0.07966681,  0.01920104,
    #                        -0.01194376, -0.02300822, -0.17204897, -0.0596558 ,  0.05307484,
    #                         0.07417042,  0.07126575,  0.00209804]

    # Load the uploaded image file
    img = face_recognition.load_image_file(file_stream)
    # Get face encodings for any faces in the uploaded image
    unknown_face_encodings = face_recognition.face_encodings(img)

    face_found = False
    is_known = False
    next_url = "/login"

    if len(unknown_face_encodings) > 0:
        face_found = True
        # See if the first face in the uploaded image matches the known face of known
        i = 0
        for face in known_face_encoding:
            
            match_results = face_recognition.compare_faces([face], unknown_face_encodings[0])
            if match_results[0]:
                is_known = True
                user_id = known_face_names[i]
                login_user(user_id)
                next_url = "/home"
            i += 1

    # Return the result as json
    result = {
        "face_found_in_image": face_found,
        "is_picture_known": is_known,
        "next_url": next_url
    }
    return result


def detect_faces_in_image_attend(file_stream):
    directory = 'static/known_faces'
    known_face_encoding = []
    known_face_names = []
    
    # iterate over files in
    # that directory
    for filename in os.listdir(directory):
        f = os.path.join(directory, filename)
        # checking if it is a file
        if os.path.isfile(f):
            obama_image = face_recognition.load_image_file(f)
            obama_face_encoding = face_recognition.face_encodings(obama_image)[0]
            known_face_encoding.append(obama_face_encoding)

            known_user_id = filename.split('.')[0]
            user = User.query.filter_by(id=known_user_id).first()
            known_face_names.append(user.id)

    # Load the uploaded image file
    img = face_recognition.load_image_file(file_stream)
    # Get face encodings for any faces in the uploaded image
    unknown_face_encodings = face_recognition.face_encodings(img)

    face_found = False
    is_known = False

    if len(unknown_face_encodings) > 0:
        face_found = True
        # See if the first face in the uploaded image matches the known face of known
        i = 0
        for face in known_face_encoding:
            
            match_results = face_recognition.compare_faces([face], unknown_face_encodings[0])
            if match_results[0]:
                is_known = True
                user_id = known_face_names[i]
                #login_user(user_id)
                reg_attendance(user_id)
            i += 1

    # Return the result as json
    result = {
        "face_found_in_image": face_found,
        "is_picture_known": is_known
    }
    return result

def reg_attendance(userID):
    emp = Attendance.query.filter_by(user_id=userID).first()
    if emp:
        emp.depature = datetime.datetime.now()
        db.session.commit()
    else:
        ts = datetime.datetime.now().timestamp()
        new_attendance = Attendance(user_id=userID, depature=ts)
        db.session.add(new_attendance)
        db.session.commit()

    



if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5001, debug=True)