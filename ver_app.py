from flask import Flask, render_template, request,session, Response
from PIL import Image
import cv2
import numpy as np
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
import sqlite3
import codecs
import random
import time
from OpenSSL import SSL

# Get the camera object
cap = cv2.VideoCapture(0)

# Generate Video
def gen_frames():
    while True:
        success, frame = cap.read()
        if not success:
            break
        else:
            ret, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
            
# Decrypt the Encrypted Data
def decryption(data,key,iv):

    data = codecs.decode(data, 'hex_codec')
    # Create an AES cipher object with the key and IV for decryption
    cipher_decrypt = AES.new(key, AES.MODE_CBC, iv=iv)

    # Decrypt the message using the cipher object and key
    decrypted_message = cipher_decrypt.decrypt(data)

    # Strip the padding from the decrypted message
    stripped_message = decrypted_message.rstrip(b"\0")

    # Print the decrypted message
    print("Decrypted message:", stripped_message)
    print(type(stripped_message))

    return stripped_message

# Get Booking Details from the Database
def get_booking_details(encrytption_message):

    # Ticket Database Connection
    conn = sqlite3.connect('booking_data.db', check_same_thread=False)
    c = conn.cursor()
     # Execute a SELECT statement to retrieve the row with the specified id
    c.execute('SELECT * FROM details WHERE booking_id = ?', (encrytption_message,))
            
    # Fetch the row returned by the SELECT statement
    row = c.fetchone()
    db_encrypted_message,key,iv,otp,status,event_flag = row[0],row[1],row[2],row[3],row[4],row[5]
    
    return db_encrypted_message,key,iv,otp,status,event_flag

# Querry Data from the Database
def update_booking_details(query,values):

    # Ticket Database Connection
    conn = sqlite3.connect('booking_data.db', check_same_thread=False)
    c = conn.cursor()

    # Save ticket information to database
    c.execute(query,values)
    conn.commit()
    conn.close()
    
# Add Performance Metrics
def update_metrics(query,values):
    
    # Ticket Database Connection
    conn = sqlite3.connect('verification_performance_metrics.db', check_same_thread=False)
    c = conn.cursor()

    # Save ticket information to database
    c.execute(query,values)
    
    conn.commit()
    conn.close()
    
# Main Function
app = Flask(__name__)
app.secret_key = 'mysecretkey'

# Video Feed
@app.route('/video_feed')
def video_feed():
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

# Home Page 
@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        qr_start_time = time.time()
        if "image" not in request.files:
            return render_template("ver_home.html", error="No image selected")
        
        image = request.files["image"].read()
        try:
            nparr = np.frombuffer(image, np.uint8)
            cv_image = cv2.imdecode(nparr, cv2.IMREAD_GRAYSCALE)
        except:
            return render_template("ver_home.html", error="Invalid image")
        

        qr_code_detector = cv2.QRCodeDetector()
        data, bbox, _ = qr_code_detector.detectAndDecode(cv_image)

        if data:
            print(type(data))
            print(data)
            encrypted_message = data
            session['encrypted_message'] = encrypted_message
            
            db_encrypted_message,key,iv,otp,status,event_flag = get_booking_details(encrypted_message)
            decrypted_message = decryption(encrypted_message,key,iv)
            db_decrypted_message = decryption(db_encrypted_message,key,iv)

            # Check the status:
            if status == 'verified':
                if event_flag == 'entry':
                    # update database with exit
                    query = " UPDATE details SET event_flag = ? where booking_id =?"
                    values = ('exit',encrypted_message)
                    update_booking_details(query,values)

                    verification_remarks = 'Exit Confirmation'
                else :
                    # update database with entry 
                    verification_remarks = 'Entry Confirmation'
                    query = " UPDATE details SET event_flag = ? where booking_id =?"
                    values = ('entry',encrypted_message)
                    update_booking_details(query,values)

            elif status == 'otp verification':
                otp = random.randint(10000, 99999)
                print("OTP: otpverification",otp)

                # update database with the otp
                query = " UPDATE details SET otp = ? where booking_id =?"
                values = (otp,encrypted_message)
                update_booking_details(query,values)

                return render_template("otp_ver.html",flag=1)
            
            elif status == 'not verified':
                otp = str(random.randint(10000, 99999))
                print("OTP: ",otp)
                # update database with otp
                query = " UPDATE details SET status = ?, otp =? where booking_id =?"
                values = ('otp verification',otp,encrypted_message)
                update_booking_details(query,values)
                

                if decrypted_message == db_decrypted_message:
                    verification_remarks = 'Verfied, next OTP Authentication'
                else:
                    verification_remarks = 'Not Verified'
            else:
                return render_template("ver_home.html", error="Error")
            
            qr_end_time = time.time()
            qr_time = qr_end_time-qr_start_time
            otp_time = 0
            query = "INSERT INTO metrics(booking_id,qr_verification_time, otp_verification_time) VALUES (?,?,?)"
            values = (encrypted_message,qr_time,otp_time)
            update_metrics(query,values)

            return render_template("ver_ticket_details.html", decrypted_message = decrypted_message, verification_remarks = verification_remarks)
        else:
            return render_template("ver_home.html", error="No QR Code Found")
    else:
        return render_template("ver_home.html")
    
# OTP Authorization 
@app.route("/otp_ver", methods=["GET", "POST"])
def otp_ver():
    if request.method == "POST":
        
        otp_start_time = time.time()
        otp = request.form["OTP"]
        encrypted_message = session['encrypted_message']
        # check otp with the database and verify it and return two kinds of template for re entering otp if required
        db_encrypted_message,key,iv,otp_db,status,event_flag = get_booking_details(encrypted_message)
        print(otp,otp_db)
        if otp==otp_db:
            verification_remarks = 'Authentication Verified'
            query = " UPDATE details SET event_flag = ?, status= ? where booking_id =?"
            values = ('entry','verified',encrypted_message)
            update_booking_details(query,values)
        else:
            verification_remarks = 'Authentication failed'
        otp_end_time = time.time()
        otp_time = otp_end_time-otp_start_time

        query = "UPDATE metrics SET otp_verification_time = ? where booking_id = ?"
        values = (otp_time,encrypted_message)
        update_metrics(query,values)

        return render_template("otp_ver.html", verification_remarks=verification_remarks)
    else:
        return render_template("otp_ver.html",flag=1)
    

# # HTTPS Certificate and Key, while Implementing TLS 1.2
# context = SSL.Context(SSL.TLSv1_2_METHOD)
# context.use_privatekey_file('key.pem')
# context.use_certificate_file('cert.pem')

if __name__ == "__main__":
    # Run Flask app with HTTPS enabled
    app.run( debug = True ,port=443)