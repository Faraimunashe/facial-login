import face_recognition
import cv2
import numpy as np
import pandas as pd
import os
import mysql.connector
import smtplib
import datetime

# Get a reference to webcam #0 (the default one)
video_capture = cv2.VideoCapture(0)

def fetch_db(userID):
    mydb = mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="facial"
    )

    mycursor = mydb.cursor()

    sql = "SELECT * FROM user WHERE id = "+str(userID)

    mycursor.execute(sql)

    myresult = mycursor.fetchone()

    #print(myresult)
    username = "Not Named"
    if myresult:
        username = myresult[3]
    return username


def send_email():
    TO = 'jimmymotofire@gmail.com'
    SUBJECT = 'System Alert'
    TEXT = 'Intruder detected! Unknown face.'

    # Gmail Sign In
    gmail_sender = ''
    gmail_passwd = ''

    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.ehlo()
    server.starttls()
    server.login(gmail_sender, gmail_passwd)

    BODY = '\r\n'.join(['To: %s' % TO,
                        'From: %s' % gmail_sender,
                        'Subject: %s' % SUBJECT,
                        '', TEXT])

    try:
        server.sendmail(gmail_sender, [TO], BODY)
        print ('email sent')
    except:
        print ('error sending mail')


def save_alert():
    mydb = mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="facial"
    )

    mycursor = mydb.cursor()

    now = datetime.datetime.now()
    formatted_date = now.strftime('%Y-%m-%d %H:%M:%S') 

    sql = "INSERT INTO intruder (msg, period) VALUES (%s, %s)"
    val = ("Intruder Detected",formatted_date)
    mycursor.execute(sql, val)

    mydb.commit()


directory = 'static/known_faces'
known_face_encodings = []
known_face_names = []
 
# iterate over files in
# that directory
for filename in os.listdir(directory):
    f = os.path.join(directory, filename)
    # checking if it is a file
    if os.path.isfile(f):
        obama_image = face_recognition.load_image_file(f)
        obama_face_encoding = face_recognition.face_encodings(obama_image)[0]
        known_face_encodings.append(obama_face_encoding)

        user_id = filename.split('.')[0]
        user = fetch_db(user_id)
        known_face_names.append(user)


# Initialize some variables
face_locations = []
face_encodings = []
face_names = []
process_this_frame = True

while True:
    # Grab a single frame of video
    ret, frame = video_capture.read()

    # Only process every other frame of video to save time
    if process_this_frame:
        # Resize frame of video to 1/4 size for faster face recognition processing
        small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)

        # Convert the image from BGR color (which OpenCV uses) to RGB color (which face_recognition uses)
        rgb_small_frame = small_frame[:, :, ::-1]
        
        # Find all the faces and face encodings in the current frame of video
        face_locations = face_recognition.face_locations(rgb_small_frame)
        face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)

        face_names = []
        for face_encoding in face_encodings:
            # See if the face is a match for the known face(s)
            matches = face_recognition.compare_faces(known_face_encodings, face_encoding)
            name = "Unknown"

            # # If a match was found in known_face_encodings, just use the first one.
            # if True in matches:
            #     first_match_index = matches.index(True)
            #     name = known_face_names[first_match_index]

            # Or instead, use the known face with the smallest distance to the new face
            face_distances = face_recognition.face_distance(known_face_encodings, face_encoding)
            best_match_index = np.argmin(face_distances)
            if matches[best_match_index]:
                name = known_face_names[best_match_index]
            else:
                save_alert()
                send_email()

            face_names.append(name)
            

    process_this_frame = not process_this_frame


    # Display the results
    for (top, right, bottom, left), name in zip(face_locations, face_names):
        # Scale back up face locations since the frame we detected in was scaled to 1/4 size
        top *= 4
        right *= 4
        bottom *= 4
        left *= 4

        # Draw a box around the face
        cv2.rectangle(frame, (left, top), (right, bottom), (0, 0, 255), 2)

        # Draw a label with a name below the face
        cv2.rectangle(frame, (left, bottom - 35), (right, bottom), (0, 0, 255), cv2.FILLED)
        font = cv2.FONT_HERSHEY_DUPLEX
        cv2.putText(frame, name, (left + 6, bottom - 6), font, 1.0, (255, 255, 255), 1)

    # Display the resulting image
    cv2.imshow('Video', frame)

    # Hit 'q' on the keyboard to quit!
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Release handle to the webcam
video_capture.release()
cv2.destroyAllWindows()