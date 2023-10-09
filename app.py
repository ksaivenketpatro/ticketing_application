from flask import Flask, render_template, request, redirect, url_for
import random
import qrcode
import sqlite3
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
from PIL import Image
import time
from OpenSSL import SSL


# Functions
# Encryption of Ticket ID
def encryption(message):

    # Generate a random encryption key and IV
    key = get_random_bytes(32)
    iv = get_random_bytes(AES.block_size)

    # Pad the message to the nearest multiple of 16 bytes
    padded_message = message + b"\0" * (AES.block_size - len(message) % AES.block_size)

    # Create an AES cipher object with the key and IV for encryption
    cipher_encrypt = AES.new(key, AES.MODE_CBC, iv=iv)

    # Encrypt the message using the cipher object
    encrypted_message = cipher_encrypt.encrypt(padded_message)

    # Print the encrypted message, key, and IV
    print("Encrypted message:", encrypted_message.hex())

    # Stored as Encrypted Message
    encrypted_message = encrypted_message.hex()
    
    return encrypted_message, key, iv

# Generation of QR Code
def qrCode_generator(encrypted_message,ticket_id):

    # Generate QR code with ticket information and save as file
    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=5, border=4)
    qr.add_data(encrypted_message)
    qr.make(fit=True)
    qr_image = qr.make_image(fill_color="black", back_color="white")

    #Load the second image
    logo_path = f"static/project_logo.jpeg"
    logo_image = Image.open(logo_path)

    # Resize the second image to fit inside the QR code
    logo_image = logo_image.resize((qr_image.size[0]//6, qr_image.size[1]//6))

    # Paste the second image onto the QR code image
    qr_image.paste(logo_image, (qr_image.size[0]//2 - logo_image.size[0]//2, qr_image.size[1]//2 - logo_image.size[1]//2))

    qr_path = f"static/{ticket_id}.png"
    qr_image.save(qr_path)

    return qr_path

# Add Ticket ID to the ticket_database.db
def add_ticket_db(encrypted_message, key, iv,otp=0,status="not verified",event_flag="not_entered" ):
    
    print("Type data: ",type(encrypted_message))
    # Ticket Database Connection
    conn = sqlite3.connect('booking_data.db', check_same_thread=False)
    c = conn.cursor()

    # Save ticket information to database
    c.execute("INSERT INTO details(booking_id,key,iv,otp,status,event_flag) VALUES (?,?,?,?,?,?)", (encrypted_message, 
                                                                                                    key, iv,otp,status,event_flag,))
    conn.commit()
    conn.close()

# add Performan Metrics
def update_metrics(total_time,encrypted_message):
    
    # Ticket Database Connection
    conn = sqlite3.connect('generation_performance_metrics.db', check_same_thread=False)
    c = conn.cursor()

    # Save ticket information to database
    c.execute("INSERT INTO metrics(booking_id,time) VALUES (?,?)", (encrypted_message,total_time,))
    conn.commit()
    conn.close()


# Main 
app = Flask(__name__)

# Home Page
@app.route("/")
def home():
    return render_template("home.html")

# Ticket Generation
@app.route("/ticket", methods=["GET", "POST"])
def generate_ticket():
    if request.method == "POST":

        start_time = time.time()
        name = request.form["name"]
        email = request.form["email"]
        ticket_id = random.randint(10000, 99999)
        print(ticket_id)
        
        # Encypt the ticket_id
        encrypted_message, key, iv = encryption(str(ticket_id).encode('utf-8'))

        # Save details on database
        add_ticket_db(encrypted_message, key, iv)
        #add_encyption_ID_db(key_iv_ID,key,iv)

        # Generate the QR Code
        qr_path = qrCode_generator(encrypted_message,ticket_id)
        end_time = time.time()
        total_time = str(end_time - start_time)

        update_metrics(total_time,encrypted_message)

        return render_template("ticket.html", name=name, email=email, ticket_id=ticket_id,qr_path=qr_path,encrypted_message=encrypted_message)
    else:
        return redirect(url_for("home"))


# # HTTPS Certificate and Key, while Implementing TLS 1.2
# context = SSL.Context(SSL.TLSv1_2_METHOD)
# context.use_privatekey_file('key.pem')
# context.use_certificate_file('cert.pem')

if __name__ == "__main__":

    # Run Flask app with HTTPS enabled
    app.run( debug = True ,port=443)