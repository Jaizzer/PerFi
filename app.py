from ast import Interactive
import os
from pickle import GLOBAL

import string

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, usd

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///perfi.db")


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/", methods=["GET", "POST"])
@login_required
def index():
    
    # Load user's username from a session.
    username = session.get("username")
        
    if request.method == "POST":
        
        # Save all the transaction information into a list.
        session["transaction"] = [
            username,
            request.form.get("description"), 
            request.form.get("category"), 
            request.form.get("amount", type=float), 
            request.form.get("account")
        ]
                
        # Get the corresponding route code.
        route_code = db.execute("SELECT operation, lend_borrow FROM ? WHERE category_name = ?", str(username + "_categories"), session["transaction"][2])[0]
        
        # Redirect to the corresponding route.
        return redirect(f"/{route_code['operation']}_{route_code['lend_borrow']}")
        
        
                
        
        
                
        # Check whether the user lend or borrowed money.
        if transaction[5] == "Lend":
            # Create or insert into a database of lending transactions.
            print("lend")
        elif transaction[5] == "Borrow":
            # Create or insert into a database of borrowing transactions.
            print("borrow")
        
        # Update the selected account.
        if transaction[6] == 1:
            db.execute("UPDATE ? SET balance = balance + ? WHERE account_name = ?", str(username + "_accounts"), transaction[4], transaction[2])
            
        elif transaction[6] == 2:
            db.execute("UPDATE ? SET balance = balance - ? WHERE account_name = ?", str(username + "_accounts"), transaction[4], transaction[2])            
        
        else:
            db.execute("UPDATE ? SET balance = balance - ? WHERE account_name = ?", str(username + "_accounts"), transaction[4], transaction[2])
            db.execute("UPDATE ? SET balance = balance + ? WHERE account_name = ?", str(username + "_accounts"), transaction[4], transaction[7])
            
        # Insert transaction to the user history.
        db.execute("INSERT INTO {} (description, account_1, category, amount, lend_borrow, operation, 'account_2') VALUES ('{}', '{}', '{}', {}, '{}', '{}', '{}')".format(*transaction))
        
        # Redirect user to the transaction history.
        return redirect("/history")
    else:
        # Load all user's added  accounts.
        accounts = db.execute("SELECT account_name, balance FROM ?", str(username + "_accounts"))
        
        # Load user's added categories.
        categories_list = db.execute("SELECT category_name FROM ?", str(username + "_categories"))
        categories = []
        for category in categories_list:
            categories.append(category["category_name"])
        return render_template("home.html", accounts=accounts, categories=categories, username=username)


@app.route("/1_0")
@login_required
def one_zero():
    
    # Update user's selected account.
    db.execute("UPDATE ? SET balance = balance + ? WHERE account_name = ?", str(session["transaction"][0] + "_accounts"), session["transaction"][3], session["transaction"][4])
    
    #return apology(str(session[]))
    
    # Update user's transaction history.
    db.execute("INSERT INTO {} (description, category, operation, amount, lend_borrow, account, transfer_account) VALUES ('{}', '{}', 1, {}, 0, '{}', 'None')".format(*session["transaction"]))

    return redirect("/history")
    
    
    
    # Goal
        # Complete all other operations

@app.route("/1_1")
@login_required
def one_one():
    return apology("Borrowed Income")

@app.route("/2_0")
@login_required
def two_zero():
    return apology("Normal Expense")

@app.route("/2_2")
@login_required
def two_one():
    return apology("Lended Expense")

@app.route("/3_0")
@login_required
def three_zero():
    return apology("transfer")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    transactions = db.execute("SELECT * FROM ? ORDER BY id DESC", session.get("username"))

    return render_template("history.html", transactions=transactions)

@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["username"] = rows[0]["username"]
        session["user_id"] = rows[0]["id"]
        
        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/login")

@app.route("/register", methods=["GET", "POST"])
def register():
    
    """Register user"""
    if request.method == "POST":

        # Add the user's entry into the userts table in the database.
        username = str(request.form.get("username"))
        password = request.form.get("password")
        confirm_password = request.form.get("confirmation")

        # Validate username submitted.

        # Initialize message.
        message = "Error:"

        # Error detector.
        error_detector = 0

        # Scenario 1: No username input.
        if not username:
            message = message + "\nNo username"
            error_detector = 400

        # Scenario 2: There is username, but not unique.
        if len(db.execute(f"SELECT username FROM users WHERE username LIKE '{username}'")) != 0:
            message = message + "\nUsername not unique"
            error_detector = 400

        # Validate password submitted.
        # Scenario 1: No password input.
        if not password:
            message = message + "\nNo password"
            error_detector = 400

        # Scenario 2: Password and confirm password did not match.
        elif password != confirm_password:
            message = message + "\nPasswords did not match"
            error_detector = 400

        # Scenario 3: Password is not strong enough.
        elif check_password_strength(password) != 5:
            message = message + "\nPassword not strong enough!"

        # User's registration has error/s.
        if error_detector != 0:

            # Redirect to apology page.
            return apology(message, error_detector)

        # User's registration is free from errors.

        # Hash the user's password.
        hash = generate_password_hash(password)

        # Remember registrants inputs.
        db.execute("INSERT INTO users (username, hash) VALUES (?, ?)", username, hash)
        
        # Create user's transaction history database.
        db.execute("CREATE TABLE ? (id INTEGER PRIMARY KEY, time TIMESTAMP DEFAULT (datetime('now', 'localtime')), description TEXT, amount REAL, operation INTEGER, category TEXT, lend_borrow INTEGER, account TEXT, transfer_account TEXT)", username)
                
        # Create user's default accounts.
        db.execute("CREATE TABLE ? (id INTEGER PRIMARY KEY, account_name TEXT, balance REAL)", str(username + "_accounts"))
        for i in range(3):
            account_name = str(f"Account {i + 1}")
            db.execute("INSERT INTO ? (account_name, balance) VALUES (?, ?)", str(username + "_accounts"), account_name, 0)        
        
        # Create user's default transaction categories.
        db.execute("CREATE TABLE ? (id INTEGER PRIMARY KEY, category_name TEXT, operation INTEGER, lend_borrow INTEGER)", str(username + "_categories"))
        db.execute("INSERT INTO ? (category_name, operation, lend_borrow) VALUES ('Expense', 2, 0), ('Income', 1, 0), ('Transfer', 3, 0), ('Savings', 3, 0), ('Debt', 1, 1), ('Lend', 2, 2)", str(username + "_categories"))
                
        # Redirect to a route that shows user's profile porfolio.
        return redirect("/login")

    else:

        # Display to user the place to register.
        return render_template("register.html")

def check_password_strength(password):

    # Initialize list of lowercase alphabet.
    lowercase_alphabet = list(string.ascii_lowercase)

    # Initialize list of uppercase alphabet.
    uppercase_alphabet = list(string.ascii_uppercase)

    # Initialize list of numbers.
    numbers = [str(x) for x in range(9)]

    # Initialize list of special characters.
    # Split into two groups to separate double and single quotation mark symbols.
    special_characters1 = '~`!@#$%^&*()_-+={[}]|\:;"'
    # Split into two groups to separate double and single quotation mark symbols.
    special_characters2 = "'<,>.?/"

    combined_special_characters = special_characters1 + special_characters2
    symbols = list(combined_special_characters)

    # Initialize password strength score.
    password_strength = 0

    # Initialize password character checkers.
    lower = upper = number = symbol = 0

    # Score password strength.
    for character in password:

        # Password contain lower characters.
        if character in lowercase_alphabet:
            lower = 1

        # Password contain upper characters.
        elif character in uppercase_alphabet:
            upper = 1

        # Password contain numbers.
        elif character in numbers:
            number = 1

        # Password contain symbols.
        elif character in symbols:
            symbol = 1

    # Password is atleast 10 characters long.
    if len(password) >= 10:
        password_strength += 1

    # Compute total password strength score.
    password_strength += lower + upper + number + symbol

    return password_strength