import pymysql
import numpy as np
from io import BytesIO
import datetime
import base64
from PIL import Image
import face_recognition
from twilio.rest import Client
from flask import Flask, render_template, request, redirect, url_for, flash, session
import bcrypt

app = Flask(__name__)
app.secret_key = 'your_secret_key'


# Twilio credentials
account_sid = 'YOUR ACCOUNT SID'
auth_token = 'YOUR AUTH TOKEN'
twilio_phone_number = 'YOUR TWILIO PHONE NUMBER'

client = Client(account_sid, auth_token)

# Database connection
def get_db_connection():
    return pymysql.connect(
        host='localhost',
        user='root',
        password='YOUR PASSWORD',
        db='votingFustion',
        cursorclass=pymysql.cursors.DictCursor
    )

def save_face_encoding(voter_id, encoding):
    connection = get_db_connection()
    with connection.cursor() as cursor:
        sql = "INSERT INTO face_encodings (voter_id, encoding) VALUES (%s, %s)"
        cursor.execute(sql, (voter_id, encoding))
    connection.commit()
    connection.close()

def get_face_encodings():
    connection = get_db_connection()
    with connection.cursor() as cursor:
        sql = "SELECT voter_id, encoding FROM face_encodings"
        cursor.execute(sql)
        result = cursor.fetchall()
    connection.close()
    return result

def train_face(image_path, name):
    image = face_recognition.load_image_file(image_path)
    face_encodings = face_recognition.face_encodings(image)
    
    if face_encodings:
        face_encoding = face_encodings[0]
        face_encoding_blob = face_encoding.tobytes()

        save_face_encoding(name, face_encoding_blob)
        return f"Face encoding saved for {name}"
    else:
        return "No face detected in the image."

def compare_face(face_image_path, username):
    known_face_encodings = []
    known_names = []
    
    # Fetch known face encodings and names from the database
    for row in get_face_encodings():
        encoding = np.frombuffer(row['encoding'], dtype=np.float64)
        known_face_encodings.append(encoding)
        known_names.append(row['voter_id'])
    
    # Load and encode the face image
    face_image = face_recognition.load_image_file(face_image_path)
    face_encodings = face_recognition.face_encodings(face_image)
    
    if face_encodings:
        face_encoding = face_encodings[0]
        
        # Compare face encoding with known encodings
        face_matches = [face_recognition.compare_faces([encoding], face_encoding)[0] for encoding in known_face_encodings]
        best_face_match_index = None
        if any(face_matches):
            best_face_match_index = face_matches.index(True)
        
        if best_face_match_index is not None:
            access_granted_name = known_names[best_face_match_index]
            if access_granted_name == username:
                return f'''Access Granted for: <b>{access_granted_name}</b>
                 <a href="#" class="btn-click btn-primary">Click here to proceed</a>
                '''
            else:
                return "Access Denied. Username does not match the access granted name."
        else:
            return "Access Denied."
    else:
        return "No face detected."

def check_password(hashed_password, user_password):
    return bcrypt.checkpw(user_password.encode('utf-8'), hashed_password.encode('utf-8'))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'username' in session:
        return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        connection = None  # Initialize connection to None
        try:
            connection = get_db_connection()
            with connection.cursor() as cursor:
                cursor.execute("SELECT * FROM admin WHERE username = %s", (username,))
                admin = cursor.fetchone()

                if admin and check_password(admin['password'], password):
                    session['username'] = username
                    flash('Login successful. Welcome!', 'success')
                    return redirect(url_for('index'))
                else:
                    flash('Invalid username or password', 'danger')
                    return redirect(url_for('login'))
        except pymysql.MySQLError as e:
            flash(f'Error: {e}', 'danger')
            return redirect(url_for('login'))
        finally:
            if connection:
                connection.close()
    
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.pop('username', None)
    session.pop('voterID', None)  # Remove the voterID from the session
    session.pop('voterInfo', None)  # Remove the voterInfo from the session
    session.pop('remainingAttempts', None)  # Remove the remainingAttempts from the session

    flash('You have been logged out', 'success')
    return redirect(url_for('index'))

def is_eligible_age(dob):
    today = datetime.datetime.today()
    age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
    return age >= 18

@app.route('/train', methods=['GET', 'POST'])
def train():
    if 'username' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        voter_id = request.form['voter_id']
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM users WHERE voter_id=%s", (voter_id,))
            result = cursor.fetchone()
            if result:
               flash("Voter ID already exists.", "error")
               return redirect(url_for('train'))
        voter_name = request.form['voter_name']
        voter_phone_number = request.form['voter_phone_number']
        voter_father_name = request.form['voter_father_name']
        voter_gender = request.form['voter_gender']
        voter_dob = request.form['voter_dob']
        dob = datetime.datetime.strptime(voter_dob, '%Y-%m-%d') 
        if not is_eligible_age(dob):
            # Handle ineligible age
            flash("Voter must be at least 18 years old.", "error")
            return redirect(url_for('train'))
        face_image_data = request.form['face_image']

        try:
            face_image_data = face_image_data.split(',')[1]
            face_image_bytes = base64.b64decode(face_image_data)
            face_image = Image.open(BytesIO(face_image_bytes))
            face_image_path = "captured_image.jpg"
            face_image.save(face_image_path)

            face_result = train_face(face_image_path, voter_id)
        except Exception as e:
            flash(f"Error: {e}")
            return redirect(url_for('train'))

        if face_result.strip().startswith("No"):
            flash(face_result, "error")
            return redirect(url_for('train'))
        
        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute("INSERT INTO users (voter_id, voter_name, voter_phone_number, voter_father_name, voter_Gender, voter_dob) VALUES (%s, %s, %s, %s, %s, %s)", (voter_id, voter_name, voter_phone_number, voter_father_name, voter_gender, voter_dob))
            connection.commit()
            flash(f'{voter_id} successfully registered', 'success')
        flash(face_result, 'success')
        return redirect(url_for('train'))
    return render_template('train.html')

def update_attempts(username, attempts):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("UPDATE users SET attempt1=%s, attempt2=%s, attempt3=%s WHERE voter_id=%s",
                           (attempts[0], attempts[1], attempts[2], username))
            conn.commit()
    finally:
        conn.close()

def get_attempts(voter_id):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT attempt1, attempt2, attempt3 FROM users WHERE voter_id=%s", (voter_id,))
            result = cursor.fetchone()
            if result:
                return [result['attempt1'], result['attempt2'], result['attempt3']]
            else:
                return [False, False, False]
    finally:
        conn.close()

@app.route('/compare', methods=['GET', 'POST'])
def compare():
    if 'username' not in session:
        return redirect(url_for('login'))
    remaining_attempts=None
    voter_info = None  # Initialize user_data
    if 'voterInfo' in session:
        voter_info=session['voterInfo']
    if 'remainingAttempts' in session:
        remaining_attempts=session['remainingAttempts']
        print("session")
        print(session)
        print(remaining_attempts)
    if request.method == 'POST':
        fetchId = request.form.get('id')
        cancel = request.form.get('cancel')
        face_image_data = request.form.get('face_image')
        print(cancel)

        # Debugging output
        print(f"fetchId: {fetchId}")

        if cancel:
            session.pop('voterID', None)  # Remove the voterID from the session
            session.pop('voterInfo', None)  # Remove the voterInfo from the session
            session.pop('remainingAttempts', None)  # Remove the remainingAttempts from the session
            user_data=None
            voter_info = None 
            remaining_attempts=None
            return redirect(url_for('compare'))
        elif fetchId:
            conn = get_db_connection()
            try:
                with conn.cursor() as cursor:
                    cursor.execute('SELECT * FROM users WHERE voter_id = %s LIMIT 1', (fetchId,))
                    user_data = cursor.fetchone()  # Fetch one record
                    if not user_data:
                        if 'voterID' in session:
                            session.pop('voterID', None)  # Remove the voterID from the session
                            session.pop('voterInfo', None)  # Remove the voterInfo from the session
                            session.pop('remainingAttempts', None)  # Remove the remainingAttempts from the session
                            user_data=None
                            voter_info = None 
                            remaining_attempts=None
                        flash("Voter ID not found.", "error")
                        return redirect(url_for('compare'))
                    session['voterID']=user_data["voter_id"]
                    voter_info = {
                        'voter_id': user_data['voter_id'],
                        'voter_name': user_data['voter_name'],
                        'voter_phone_number': user_data['voter_phone_number'],
                        'voter_father_name': user_data['voter_father_name'],
                        'voter_Gender': user_data['voter_Gender'],
                        'voter_dob': user_data['voter_dob']
                    }
                    session['voterInfo'] = voter_info
                    attempts = get_attempts(session['voterID'])
                    # print("attempts")
                    # print(attempts)
                    remaining_attempts = 3 - sum(attempts)  # Calculate remaining attempts
                    # print(remaining_attempts)
                    session["remainingAttempts"]=remaining_attempts

                    # print("remaining_attempts1")
                    # print(remaining_attempts)
                    # print(session['voterID'])
            finally:
                conn.close()
        else:
            if 'voterID' not in session:
                flash("You Need to Fetch info First.", "error")
                return redirect(url_for('compare'))
            voter_id = session['voterID']
            attempts = get_attempts(voter_id)
            remaining_attempts = 3 - sum(attempts)  # Calculate remaining attempts
            session["remainingAttempts"]=remaining_attempts
            if face_image_data:
                # Decode the face image from the base64 string
                face_image_data = face_image_data.split(',')[1]
                face_image_bytes = base64.b64decode(face_image_data)
                face_image = Image.open(BytesIO(face_image_bytes))
                face_image_path = "captured_image.jpg"
                face_image.save(face_image_path)
                print("imp")
                print(remaining_attempts)
                if remaining_attempts != 0 or remaining_attempts!=None:
                    print(remaining_attempts)
                    result = compare_face(face_image_path, voter_id)
                else:
                    flash("Access Denied - You have no more attempts left.", "error")
                    return redirect(url_for('compare'))

                if result.strip().startswith("Access Granted"):
                    session['result'] = result
                    session['sendMessage'] = True
                    session['authentication'] = True
                    print("Access Granted")
                    # Reset attempts on success
                    update_attempts(voter_id, [False, False, False])
                    return redirect(url_for('send_message_route'))
                elif result.strip().startswith("Access Denied"):
                    if remaining_attempts > 0:
                        for i in range(3):
                            if not attempts[i]:
                                attempts[i] = True
                                break
                        update_attempts(voter_id, attempts)
                        remaining_attempts -= 1
                        session["remainingAttempts"]=remaining_attempts
                        if remaining_attempts == 0:
                            session['result'] = result
                            session['sendMessage'] = True
                            session['authentication'] = False
                            print("Access Denied - You have no more attempts left.1")
                            return redirect(url_for('send_message_route'))
                        else:
                            flash(f"Access Denied - You have {remaining_attempts} attempts left.", "error")
                            return redirect(url_for('compare'))
                    else:
                        flash("Access Denied - You have no more attempts left.", "error")
                        session['result'] = result
                        session['sendMessage'] = True
                        session['authentication'] = False
                        print("Access Denied - You have no more attempts left.")
                        return redirect(url_for('send_message_route'))
                else:
                    flash(result, "info")
                    return redirect(url_for('compare'))
            else:
                flash("No face image data received.", "error")
                return redirect(url_for('compare'))
            
    # else: 
    #     session.pop('voterID', None)
    return render_template('compare.html', remaining_attempts=remaining_attempts, user_data= voter_info)


@app.route('/result')
def result():
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template('result.html')

def send_message(phone_number, user_id, is_authenticated):
    # Define the message body
    message_body = 'Successfully authenticated. You are eligible to vote.' if is_authenticated else 'Authentication failed. You are not eligible to vote for the next 5 years.'
    
    try:
        # Send message using Twilio
        message = client.messages.create(
            body=message_body,
            from_=twilio_phone_number,
            to=phone_number
        )
        print(f"Message sent successfully: {message.sid}")
    except Exception as e:
        print(f"An error occurred: {e}")
    session.pop('result', None)  # Remove the result from the session
    session.pop('sendMessage', None)  # Remove the sendOTP from the session
    session.pop('authentication', None)  # Remove the seauthenticationndOTP from the session
    session.pop('voterID', None)  # Remove the voterID from the session
    session.pop('voterInfo', None)  # Remove the voterInfo from the session
    session.pop('remainingAttempts', None)  # Remove the remainingAttempts from the session
    # Connect to the database
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            # Insert authentication data into the user_authentication table
            sql = """
            INSERT INTO user_authentication (voter_id, is_authenticated, authentication_date)
            VALUES (%s, %s, %s)
            """
            cursor.execute(sql, (user_id, is_authenticated, datetime.datetime.now()))
            print("d")
            print(user_id)
            print(is_authenticated)
            connection.commit()
    finally:
        connection.close()

    if is_authenticated:
        flash("Authentication Verified successfully!")
        return redirect(url_for('result'))
    else:
        flash("Apologies, authentication was unsuccessful.","error")
        return redirect(url_for('index'))


@app.route('/send_message_route', methods=['GET', 'POST'])
def send_message_route():
    if 'sendMessage' not in session:
        return redirect(url_for('compare'))
    else:
        username=session['voterID']
        connection = get_db_connection()
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT * FROM users WHERE voter_id = %s", (username,))
                result = cursor.fetchone()
                isAuthention=session['authentication']
                if result:
                    return send_message(result["voter_phone_number"],result['voter_id'],isAuthention) 
        finally:
            connection.close()


@app.route('/success')
def success():
    return f'Authentication Verified successfully for {session['voterID']}!'

if __name__ == "__main__":
    app.run(debug=True)
