#! C:\Program Files\Python312\python.exe

from flask import *
import pymysql
import pymysql.cursors
import bcrypt
from datetime import datetime, timedelta
import math

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
                    email VARCHAR(100) NOT NULL UNIQUE,
                    admin BOOLEAN DEFAULT FALSE
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
                    FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS order_times (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    order_id INT NOT NULL,
                    start_by DATE NOT NULL,
                    started BOOLEAN DEFAULT FALSE,
                    finish_by DATE NOT NULL,
                    finished BOOLEAN DEFAULT FALSE,
                    days_delayed INT DEFAULT 0,
                    FOREIGN KEY (order_id) REFERENCES orders(id)
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
    global preverr_home
    global displayerr
    err = request.args.get('err', 0) # Henter err kode, hvis ikke blir err = 0
    
    if displayerr == False: 
        if preverr_home == err:
                preverr_home = None
                return redirect(url_for('home'))# refresher url hvis error allerede er vist, så error ikke blir på skjermen
    else:
        displayerr = False
        preverr_home = err

    if 'customer_id' in session and session['customer_id'] is not None: # Sjekker om bruker er logget inn
        loggedin = "1"
        firstname = session['firstname']
        lastname = session['lastname']
    else:
        loggedin = "0"
        firstname = None
        lastname = None
    return render_template('index.html', err=err , loggedin=loggedin, firstname=firstname, lastname=lastname)



@app.route('/order')
def order():
    if 'customer_id' not in session or session['customer_id'] == None: # Sjekker om bruker er logget inn
        return redirect(url_for('home', err=4))
    return render_template('order.html')

def estimate_finish_by(book_pages): # Estimerer tid det vil ta å oversette boken, og setter en finish_by dato
    conn = pymysql.connect(**db_config) # Funksjonen regner med at oversetteren jobber 5 dager i uken, og oversetter 20 sider om dagen
    cursor = conn.cursor()

    try:
        sql = """
        SELECT finish_by FROM order_times ORDER BY finish_by DESC LIMIT 1
        """
        cursor.execute(sql)
        date = cursor.fetchone()
        print(date)
    except Exception as e:
        print(f"Error: {e}")
        result = False
    finally:
        conn.close()
    base_days = int(book_pages) / 20 #20 sider om dagen
    weekends = 2 * math.floor(base_days / 5) # helg
    total_days = base_days + weekends + 2 # + 2 dager i tilfelle
    total_days = round(total_days)
    

    if date is not None: 
        latest_finish_by = date['finish_by']
        print(latest_finish_by + timedelta(days=total_days))
        return latest_finish_by + timedelta(days=1), latest_finish_by + timedelta(days=total_days)
    else:
        print(datetime.now() + timedelta(days=total_days))
        return datetime.now() + timedelta(days=1), datetime.now() + timedelta(days=total_days)


@app.route('/process-order', methods=['POST'])
def process_order():
    conn = pymysql.connect(**db_config)
    cursor = conn.cursor()

    book = request.form.get('book')
    book_pages = request.form.get('book_pages')
    translate_from = request.form.get('translate_from')
    translate_to = request.form.get('translate_to')
    customer_id = session['customer_id']
    start_by, finish_by = estimate_finish_by(book_pages)
    print(start_by, finish_by)

    if translate_from == translate_to:
        return redirect(url_for('order', err="3"))

    sql = """
    INSERT INTO orders (customer_id, book, book_pages, translate_from, translate_to)
    VALUES (%s, %s, %s, %s, %s)
    """
    cursor.execute(sql, (customer_id, book, book_pages, translate_from, translate_to))
    conn.commit()

    sql = """
    SELECT id FROM orders WHERE customer_id = %s AND book = %s
    """
    cursor.execute(sql, (customer_id, book))
    order_id = cursor.fetchone()['id']
    sql = """
    INSERT INTO order_times (order_id, start_by, finish_by)
    VALUES (%s, %s, %s)
    """
    cursor.execute(sql, (order_id, start_by, finish_by))
    conn.commit()
    conn.close()
    return redirect(url_for('order_confirmation', order_id=order_id))


@app.route('/order-confirmation')
def order_confirmation():
    conn = pymysql.connect(**db_config)
    cursor = conn.cursor()
    order_id = request.args.get('order_id')
    sql = """
    SELECT book FROM orders WHERE id = %s
    """
    cursor.execute(sql, (order_id,))
    book = cursor.fetchone()['book']
    sql = """
    SELECT start_by, finish_by FROM order_times WHERE order_id = %s
    """
    cursor.execute(sql, (order_id,))
    times = cursor.fetchone()
    start_by = times['start_by']
    finish_by = times['finish_by']
    conn.close()

    start_by_formatted = start_by.strftime("%b %d, %Y")
    finish_by_formatted = finish_by.strftime("%b %d, %Y")
    return render_template('order-confirmation.html', book=book, start_by=start_by_formatted, finish_by=finish_by_formatted)


@app.route('/signup')
def signup(): # Viser register side
    return render_template('signup.html') 

@app.route('/process-signup', methods=['POST'])
def process_signup():
    print("Processing signup")
    conn = pymysql.connect(**db_config)
    cursor = conn.cursor()
    firstname = request.form.get('firstname') # Henter nødvendig data
    lastname = request.form.get('lastname')
    email = request.form.get('email')
    password = request.form.get('password')
    password_bytes = password.encode('utf-8')


    salt = bcrypt.gensalt()

    hashed_password = bcrypt.hashpw(password_bytes, salt) #Hasher passord for tryggere lagring


    try:
        sql = """
            INSERT INTO customers (firstname, lastname, email, password_hash, salt)
            VALUES (%s, %s, %s, %s, %s)
            """
        cursor.execute(sql, (firstname, lastname, email, hashed_password, salt,)) # Lagrer data i databasen
        conn.commit()
        sql = """
        SELECT customer_id FROM customers WHERE email = %s
        """
        cursor.execute(sql, (email,))
        customer_id = cursor.fetchone()
        session['customer_id'] = customer_id['customer_id']
        session['firstname'] = firstname
        session['lastname'] = lastname
        session['email'] = email
        session['admin'] = False

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
    SELECT email, firstname, lastname, customer_id, salt, password_hash, admin FROM customers WHERE email = %s
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
        session['admin'] = result['admin']
    conn.close()
    return redirect(url_for('home'))



@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

@app.route('/validate_email') #sjekker om email allerede er i bruk
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
    

@app.route('/admin-dashboard')
def admin_dashboard():
    if 'customer_id' not in session or session['customer_id'] == None:
        return redirect(url_for('home'))
    if session['admin'] == False:
        return redirect(url_for('home'))
    conn = pymysql.connect(**db_config)
    cursor = conn.cursor()
    admin_id = session['customer_id']
    sql = """
    SELECT firstname FROM customers WHERE customer_id = %s
    """
    cursor.execute(sql, (admin_id,))

    sql = """  
    SELECT * FROM orders
    """
    cursor.execute(sql)
    orders = cursor.fetchall()
    for order in orders:
        sql = """
        SELECT * FROM order_times WHERE order_id = %s
        """
        cursor.execute(sql, (order['id'],))
        times = cursor.fetchone()
        customer_id = order['customer_id']
        sql = """
        SELECT firstname, lastname FROM customers WHERE customer_id = %s
        """
        cursor.execute(sql, (customer_id,))
        customer = cursor.fetchone()
        order['customer'] = f"{customer['firstname']} {customer['lastname']}"
        order['start_by'] = times['start_by']
        order['finish_by'] = times['finish_by']
    conn.close()
    return render_template('admin-dashboard.html', orders=orders)
    

if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=8080)