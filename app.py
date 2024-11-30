from flask import Flask, render_template, request, redirect, url_for, flash, session, g
import sqlite3
from datetime import datetime
import os
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
DATABASE = 'expenses.db'

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    with app.app_context():
        db = get_db()
        cursor = db.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS user (
                            id INTEGER PRIMARY KEY,
                            username TEXT UNIQUE NOT NULL,
                            password TEXT NOT NULL
                          )''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS expense (
                            id INTEGER PRIMARY KEY,
                            user_id INTEGER,
                            date TEXT,
                            category TEXT,
                            amount REAL,
                            description TEXT,
                            FOREIGN KEY (user_id) REFERENCES user(id)
                          )''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS budget (
                            id INTEGER PRIMARY KEY,
                            user_id INTEGER,
                            month TEXT,
                            amount REAL,
                            FOREIGN KEY (user_id) REFERENCES user(id)
                          )''')
        db.commit()

@app.route('/')
def index():
    # Show the homepage with login/register buttons if not logged in
    if 'user_id' in session:
        return redirect(url_for('summary'))
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        db = get_db()
        cursor = db.cursor()
        cursor.execute("SELECT * FROM user WHERE username = ?", (username,))
        user = cursor.fetchone()
        if user and check_password_hash(user[2], password):
            session['user_id'] = user[0]
            flash('Logged in successfully!', 'success')
            return redirect(url_for('summary'))
        flash('Login failed. Check username and password.', 'danger')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = generate_password_hash(request.form['password'])
        db = get_db()
        cursor = db.cursor()
        try:
            cursor.execute("INSERT INTO user (username, password) VALUES (?, ?)", (username, password))
            db.commit()
            flash('Registration successful!', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Username already exists.', 'danger')
    return render_template('register.html')

@app.route('/add_expense', methods=['GET', 'POST'])
def add_expense():
    if 'user_id' not in session:
        flash('Please log in first', 'danger')
        return redirect(url_for('login'))

    if request.method == 'POST':
        user_id = session.get('user_id')
        date = request.form['date']
        category = request.form['category']
        amount = float(request.form['amount'])
        description = request.form.get('description')

        db = get_db()
        cursor = db.cursor()
        cursor.execute("INSERT INTO expense (user_id, date, category, amount, description) VALUES (?, ?, ?, ?, ?)",
                       (user_id, date, category, amount, description))
        db.commit()
        flash('Expense added successfully!', 'success')
        return redirect(url_for('summary'))
    return render_template('add_expense.html')

@app.route('/budget', methods=['GET', 'POST'])
def budget():
    if 'user_id' not in session:
        flash('Please log in first', 'danger')
        return redirect(url_for('login'))

    user_id = session.get('user_id')
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM budget WHERE user_id = ?", (user_id,))
    budget = cursor.fetchone()

    if request.method == 'POST':
        amount = float(request.form['amount'])
        if budget:
            cursor.execute("UPDATE budget SET amount = ? WHERE user_id = ?", (amount, user_id))
        else:
            cursor.execute("INSERT INTO budget (user_id, month, amount) VALUES (?, ?, ?)",
                           (user_id, datetime.now().strftime('%B'), amount))
        db.commit()
        flash('Budget updated successfully!', 'success')
        return redirect(url_for('budget'))

    return render_template('budget.html', budget=budget)

@app.route('/summary')
def summary():
    if 'user_id' not in session:
        flash('Please log in first', 'danger')
        return redirect(url_for('login'))

    user_id = session.get('user_id')
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM expense WHERE user_id = ?", (user_id,))
    expenses = cursor.fetchall()
    total_expenses = sum(expense[4] for expense in expenses)
    cursor.execute("SELECT amount FROM budget WHERE user_id = ?", (user_id,))
    budget = cursor.fetchone()

    return render_template('summary.html', expenses=expenses, total_expenses=total_expenses, budget=budget)

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('Logged out successfully!', 'success')
    return redirect(url_for('index'))

if __name__ == '__main__':
    if not os.path.exists(DATABASE):
        init_db()
    app.run(debug=True)
