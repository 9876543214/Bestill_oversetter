#! C:\Program Files\Python312\python.exe

from flask import *
import pymysql
import pymysql.cursors
import bcrypt

app = Flask(__name__)

app.secret_key = 'your secret key'

db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'db': 'translate_books',
    'cursorclass': pymysql.cursors.DictCursor
}

def create_database(config):
    connection = pymysql.connect(
        host=config['host'],
        user=config['user'],
        password=config['password']
    )
    try:
        with connection.cursor() as cursor:
            # Lag database hvis den ikke finnes
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS `translate_books`")

            connection.select_db(config['db'])

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS customers (
                    customer_id INT AUTO_INCREMENT PRIMARY KEY,
                    firstname VARCHAR(50) NOT NULL,
                    lastname VARCHAR(50) NOT NULL,
                    password_hash VARCHAR(100) NOT NULL,
                    salt VARCHAR(100) NOT NULL,
                    email VARCHAR(100) NOT NULL
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS orders (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    customer_id INT NOT NULL,
                    book TEXT NOT NULL,
                    book_pages INT NOT NULL,
                    translate_from VARCHAR(50) NOT NULL,
                    translate_to VARCHAR(50) NOT NULL,
                    finish_by DATE NOT NULL,
                    FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
                )
            """)
    finally:
        connection.close()

create_database(db_config)


displayerr = False
preverr_home = None
preverr_login = None



@app.route('/')
def home():
    return render_template('index.html')






@app.route('/signup')
def signup(): # Viser register side
    return render_template('signup.html') 

@app.route('/process-signup', methods=['POST'])
def process_signup():
    print("Processing signup")
    conn = pymysql.connect(**db_config)
    cursor = conn.cursor()
    name = request.form.get('name') # Henter nødvendig data
    email = request.form.get('email')
    password = request.form.get('password')
    password_bytes = password.encode('utf-8')


    salt = bcrypt.gensalt()

    hashed_password = bcrypt.hashpw(password_bytes, salt) #Hasher passord for tryggere lagring


    try:
        sql = """
            INSERT INTO customers (name, email, password_hash, salt)
            VALUES (%s, %s, %s, %s)
            """
        cursor.execute(sql, (name, email, hashed_password, salt,)) # Lagrer data i databasen
        conn.commit()
        sql = """
        SELECT customer_id FROM customers WHERE email = %s
        """
        cursor.execute(sql, (email,))
        customer_id = cursor.fetchone()
        session['customer_id'] = customer_id['customer_id']
        session['name'] = name
        session['email'] = email

    except Exception as e:
        print(f"Error: {e}")
        conn.rollback()
        return redirect(url_for('signup', err = {e}))
    finally:
        cursor.close()
        conn.close()
    return redirect(url_for('home'))


@app.route('/login')
def login_page():
    global preverr_login
    global displayerr
    err = request.args.get('err', 0) # Henter err kode, hvis ikke blir err = 0
    
    if displayerr == False: 
        if preverr_login == err:
                preverr_login = None
                return redirect(url_for('home'))# refresher url hvis error allerede er vist, så error ikke blir på skjermen
    else:
        displayerr = False
        preverr_login = err

    return render_template('login.html', err=err)


@app.route('/login_process', methods=['POST'])
def login_process():
    global displayerr
    email = request.form.get('email')
    password = request.form.get('password')
    conn = pymysql.connect(**db_config)
    cursor = conn.cursor()

    password_bytes = password.encode('utf-8')

    sql = """
    SELECT email, firstname, lastname, customer_id, salt, password_hash FROM customers WHERE email = %s
    """ 
    cursor.execute(sql, (email,)) # Sjekker om email finnes i databasen
    result = cursor.fetchone()

    if result == None:
        conn.close()
        return redirect(url_for('login_page', err=1)) # Hvis email eller navn ikke finnes, retuneres err 1
    
    print(result)
    salt = result['salt']
    salt_bytes = salt.encode('utf-8')
    hashed_password = bcrypt.hashpw(password_bytes, salt_bytes)# Gjør dette passordet lik som den i databasen
    decoded_hash = hashed_password.decode('utf-8') 
    password = None # Tømmer ikke-hashed passord


    if decoded_hash != result['password_hash']:
        displayerr = True
        return redirect(url_for('login_page', err=2)) # Hvis passord ikke er lik den i databasen, retuneres err 2
    else:
        session['customer_id'] = result['customer_id']
        session['firstname'] = result['firstname']
        session['lastname'] = result['lastname']
        session['email'] = result['email']
    conn.close()
    return redirect(url_for('home'))

@app.route('/validate_email')
def validate_email():
    email = request.args.get('email')
    conn = pymysql.connect(**db_config) 
    cursor = conn.cursor()

    sql = """
    SELECT email FROM customers WHERE email = %s
    """
    cursor.execute(sql, (email,))
    result = cursor.fetchone()

    conn.close()

    print(result)

    if result != None:
        print("Email exists")
        return jsonify({"exists": True, "email": result[0]})
    else:
        print("Email does not exist")
        return jsonify({"exists": False})
    



if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=8080)