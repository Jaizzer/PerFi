from ast import Interactive
import os
from pickle import GLOBAL

import string
from tokenize import Name

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
    
    # Load user's table name.
    table_name = session["table_name"]
        
    if request.method == "POST":
        
        # Save all the transaction information into a list.
        session["transaction"] = [
            session["username"],
            request.form.get("description"), 
            request.form.get("category"), 
            request.form.get("amount", type=float), 
            request.form.get("account")
        ]
                
        # Get the operation code.
        route_code = db.execute("SELECT lend_borrow FROM ? WHERE category_name = ?", table_name[1], session["transaction"][2])[0]["lend_borrow"]
        
        # Choose route name base on operation code.
        if route_code == 0:
            route_code = "regular"
        else:
            route_code = "complex"
            
        # Redirect to the corresponding route.
        return redirect(f"/{route_code}")
                 
    else:
        # Load all user's added  accounts.
        accounts = db.execute("SELECT account_name, account_balance FROM ?", table_name[0])
        
        # Load user's added categories.
        categories = db.execute("SELECT category_name FROM ?", table_name[1])
        return render_template("home.html", accounts=accounts, categories=categories, username=table_name[2])


@app.route("/regular")
@login_required
def regular():
    
    # Load user's table's name from a session.
    table_name = session["table_name"]
    
    # Load user's current transaction information from a session.
    transaction = session["transaction"]
    
    # Choose what operation to perform based on the category.
    operation = db.execute("SELECT category_operation FROM ? WHERE category_name = ?", table_name[1], session["transaction"][2])[0]["category_operation"]
    
    # Update user's selected account.
    db.execute("UPDATE ? SET account_balance = account_balance + ?\
        WHERE account_name = ?", table_name[0], (operation * transaction[3]), transaction[4])
        
    # Update user's transaction history.
    db.execute("INSERT INTO {} (description, category_name, amount, account,\
        transfer_account) VALUES ('{}', '{}', {}, '{}', 'None')".format(*transaction))

    
    
    return redirect("/history")
    
    # Income/Expense.
    
    
    # Transfer/Savings
    print("hello")


@app.route("/1_0")
@login_required
def one_zero():
    
    # Update user's selected account.
    db.execute("UPDATE ? SET balance = balance + ? WHERE account_name = ?", str(session["transaction"][0] + "_accounts"), session["transaction"][3], session["transaction"][4])
        
    # Update user's transaction history.
    db.execute("INSERT INTO {} (description, category_id, operation, amount, lend_borrow, account, transfer_account) VALUES ('{}', '{}', 1, {}, 0, '{}', 'None')".format(*session["transaction"]))

    return redirect("/history")
    
@app.route("/1_1", methods=["GET", "POST"])
@login_required
def one_one():
    
    if request.method == "POST":
        
        # Load user's username.
        username = session.get("username")
        
        # Get the name that lend or borrowed money from the user.
        name = request.form.get("name")
                
        # Get the amount of money involved.
        amount = session["transaction"][3]
        
        # Check if the name is already in the database.
        owed = db.execute("SELECT name FROM ? WHERE name = ?", str(username + "_debt_receivable"), name)
        if len(owed) == 0:
            db.execute("INSERT INTO ? (name, type, balance) VALUES (?, 1, ?)", str(username + "_debt_receivable"), name, amount)
        else:
            db.execute("UPDATE ? SET balance = balance + ? WHERE name = ?",  str(username + "_debt_receivable"), amount, name)
                    
        # Process user's accounts.
        return redirect("/1_0")

    else:
        debts_receivables  =  db.execute("SELECT name, type, balance FROM ? WHERE type =  1", str(session["username"] + "_debt_receivable"))
        return render_template("lend_borrow.html", category=session["transaction"][2], debts_receivables=debts_receivables)


@app.route("/debt")
@login_required
def debt():
    
    # Load user's debt list from the databse.
    debts = db.execute("SELECT * FROM ? WHERE type = 1", str(session["username"] + "_debt_receivable"))
    
    return render_template("debts.html", debts=debts)


@app.route("/receivable")
@login_required
def receivable():

    # Load user's receivable list from the databse.
    receivables = db.execute("SELECT * FROM ? WHERE type = 2", str(session["username"] + "_debt_receivable"))
    
    return render_template("receivable.html", receivables=receivables)


@app.route("/2_0")
@login_required
def two_zero():
    
    # Update user's selected account.
    db.execute("UPDATE ? SET balance = balance - ? WHERE account_name = ?", str(session["transaction"][0] + "_accounts"), session["transaction"][3], session["transaction"][4])
        
    # Update user's transaction history.
    db.execute("INSERT INTO {} (description, category, operation, amount, lend_borrow, account, transfer_account) VALUES ('{}', '{}', 2, {}, 0, '{}', 'None')".format(*session["transaction"]))

    return redirect("/history")


@app.route("/2_2", methods=["GET", "POST"])
@login_required
def two_two():
    
    if request.method == "POST":
        
        # Load user's username.
        username = session.get("username")
        
        # Get the name that lend or borrowed money from the user.
        name = request.form.get("name")
                
        # Get the amount of money involved.
        amount = session["transaction"][3]
        
        # Check if the name is already in the database.
        receivable = db.execute("SELECT name FROM ? WHERE name = ?", str(username + "_debt_receivable"), name)
        if len(receivable) == 0:
            db.execute("INSERT INTO ? (name, type, balance) VALUES (?, 2, ?)", str(username + "_debt_receivable"), name, amount)
        else:
            db.execute("UPDATE ? SET balance = balance + ? WHERE name = ?",  str(username + "_debt_receivable"), amount, name)
                    
        # Process user's accounts.
        return redirect("/2_0")

    else:
        debts_receivables  =  db.execute("SELECT name, type, balance FROM ? WHERE type = 2", str(session["username"] + "_debt_receivable"))
        return render_template("borrow_lend.html", category=session["transaction"][2], debts_receivables=debts_receivables)

@app.route("/3_0", methods=["GET", "POST"])
@login_required
def three_zero():
    
    if request.method == "POST":
        
        # Get the user's selected account to transfer money.
        account_to_transfer = request.form.get("account_to_transfer")
        
        # Update user's selected account.
        db.execute("UPDATE ? SET balance = balance - ? WHERE account_name = ?", str(session["transaction"][0] + "_accounts"), session["transaction"][3], session["transaction"][4])
        
        # Update user's selected account.
        db.execute("UPDATE ? SET balance = balance + ? WHERE account_name = ?", str(session["transaction"][0] + "_accounts"), session["transaction"][3], account_to_transfer)
    
        # Update user's transaction history.
        db.execute("INSERT INTO {} (description, category, operation, amount, lend_borrow, account, transfer_account) VALUES ('{}', '{}', 2, {}, 0, '{}', '{}')".format(*session["transaction"], account_to_transfer))

        return redirect("/history")

    else:
        
        # Load all user's added  accounts.
        accounts = db.execute("SELECT account_name, balance FROM ? WHERE account_name != ?", str(session["username"] + "_accounts"), session["transaction"][4])

        return render_template("transfer.html", accounts=accounts, category=session["transaction"][2])


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
        
        # Create user table's name.
        table_name = [
            str(username + "_accounts"),
            str(username + "_categories"),
            username,
            str(username + "_debt_receivable")
        ]
        # Store table names into a session.
        session["table_name"] = table_name
        
        # Create users' account database.
        db.execute("CREATE TABLE ? (\
            id INTEGER PRIMARY KEY,\
            account_name TEXT,\
            account_balance REAL)", table_name[0])
        
        # Populate user's account with default accounts.
        for i in range(3):
            account_name = str(f"Account {i + 1}")
            db.execute("INSERT INTO ? (account_name, account_balance) VALUES (?, ?)", table_name[0], account_name, 0)        

        # Create users' category database.
        db.execute("CREATE TABLE ? (\
            id INTEGER PRIMARY KEY,\
            category_name TEXT,\
            category_operation INTEGER,\
            lend_borrow INTEGER)", table_name[1])
        
        # Populate user's transaction category with dafault categories.
        db.execute("INSERT INTO ? (\
            category_name, category_operation, lend_borrow)\
            VALUES ('Income', 1, 0), ('Expense', -1, 0),\
            ('Transfer', 0, 0), ('Savings', 0, 0),\
            ('Debt', 1, 1), ('Lend', -1, 1)", table_name[1])

        # Create user's transaction history database.
        db.execute("CREATE TABLE ? (\
            id INTEGER PRIMARY KEY,\
            time TIMESTAMP DEFAULT (datetime('now', 'localtime')),\
            description TEXT,\
            amount REAL,\
            category_id INTEGER,\
            account1_id,\
            account2_id,\
            FOREIGN KEY(category_id) REFERENCES ?(id),\
            FOREIGN KEY(account1_id) REFERENCES ?(id),\
            FOREIGN KEY (account2_id) REFERENCES ?(id))", table_name[2], table_name[1], table_name[0], table_name[0])
                
        # Create user's debt and receivable tables.
        db.execute("CREATE TABLE ? (id PRIMARY KEY, name TEXT, balance REAL)",  table_name[3])
                
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