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
            request.form.get("account"), 'None']
                
        # Get the operation code.
        operation_code = db.execute("SELECT lend_borrow FROM ? WHERE category_name = ?", table_name[1], session["transaction"][2])[0]["lend_borrow"]
        
        # Choose route name base on operation code.
        route_code = "regular" if operation_code == 0 else "lend_borrow"
        
        # Redirect to the corresponding route.
        return redirect(f"/{route_code}")
                 
    else:
        # Load all user's added  accounts.
        accounts = db.execute("SELECT account_name, account_balance FROM ?", table_name[0])
        
        # Load all user's description.
        descriptions = db.execute("SELECT description FROM ? ORDER BY description", table_name[4])
        
        # Load user's added categories.
        categories = db.execute("SELECT category_name FROM ? WHERE (category_name != 'Debt Payment' AND category_name != 'Lend Collection')", table_name[1])
                        
        return render_template("home.html", accounts=accounts, categories=categories, username=table_name[2], descriptions=descriptions)


@app.route("/regular")
@login_required
def regular():
    
    # Load user's table's name from a session.
    table_name = session["table_name"]

    # Choose what operation to perform based on the category.
    operation = db.execute("SELECT category_operation FROM ? WHERE category_name = ?", table_name[1], session["transaction"][2])[0]["category_operation"]
    
    # Change the sign of the amound base on the operation.
    session["transaction"][3] = operation * session["transaction"][3]

    # Load user's current transaction information from a session.
    transaction = session["transaction"]

    # Operation does not involve transfers.
    if operation != 0:        
        # Update user's selected account.
        db.execute("UPDATE ? SET account_balance = account_balance + ?\
            WHERE account_name = ?", table_name[0], transaction[3], transaction[4])
            
    # Operation involved transfers.
    else:
        
        return redirect("/transfer")
         
    # Update user's transaction history.
    db.execute("INSERT INTO {} (description, category, amount, account_1, account_2)\
            VALUES ('{}', '{}', {}, '{}', '{}')".format(*transaction))

    return redirect("/history")


@app.route("/lend_borrow_prompt")
@login_required
def lend_borrow_prompt():
    
    # Load user's table's name from a session.
    table_name = session["table_name"]
    
    people_entities =  db.execute("SELECT * FROM ?", table_name[3])
    return render_template("lend_borrow.html", category=session["transaction"][2], people_entities=people_entities)


@app.route("/lend_borrow")
@login_required
def lend_borrow():
    
        
    # Load user's table's name from a session.
    table_name = session["table_name"]

    # Choose what operation to perform based on the category.
    operation = db.execute("SELECT category_operation FROM ? WHERE category_name = ?", table_name[1], session["transaction"][2])[0]["category_operation"]
        
    # Change the sign of the amound base on the operation.
    session["transaction"][3] = operation * session["transaction"][3]

    # Load user's current transaction information from a session.
    transaction = session["transaction"]

    # Transaction is lend/borrow.
    if transaction[2] in {"Debt", "Lend"}:
        
        # Determine what column to use for a debt/lend transaction.
        lend_borrow = "lend" if transaction[3] < 0 else "borrow"
            
        # Get the name where the user borrowed or lended money.
        name = request.form.get("name")

    # Transaction is payment/collection.
    else:
            
        # Determine what column to use for a payment/collection transaction.
        lend_borrow = "account_2"
            
        # Get the name of the person/entity the user is going to pay/collect money.
        name = transaction[5]
            
    # Update user's selected account.
    db.execute("UPDATE ? SET account_balance = account_balance + ?\
        WHERE account_name = ?", table_name[0], transaction[3], transaction[4])
                
    # Update user's lend/borrow database.
    if len(db.execute("SELECT name FROM ? WHERE name = ?", table_name[3], name)) == 0: # Check if the person/entity exists in user's database.
        db.execute("INSERT INTO ? (name, balance) VALUES (?, ?)", table_name[3], name, transaction[3])
    else:
        db.execute("UPDATE ? SET balance = balance + ? WHERE name = ?",  table_name[3], transaction[3], name)

    # Update user's transaction history.
    db.execute("INSERT INTO {} (description, category, amount, account_1, '{}')\
            VALUES ('{}', '{}', {}, '{}', '{}')".format(transaction[0], lend_borrow, *transaction[1:-1], name))
        
    # Redirect user to history.  
    return redirect(f"/history")
        

@app.route("/edit", methods=["GET", "POST"])
@login_required
def edit():
    
    if request.method == "POST":
        
        table_to_edit = request.form.get("table_to_edit")
                        
        return redirect(f"/edit_{table_to_edit}")
        
    else:
        
        return render_template("edit.html")


@app.route("/edit_description", methods=["GET", "POST"])
@login_required
def edit_description():
            
    # Load user's table name.
    table_name = session["table_name"]    

    if request.method == "POST":
        
        # Get the description to rename and save it into a session.
        session["description_to_rename"] = request.form.get("description_to_edit")
        
        return redirect("/rename_description")
    
    else:
        
        # Load all user's description.
        descriptions = db.execute("SELECT description FROM ?", table_name[4])
        
        return render_template("edit_description.html", descriptions=descriptions)


@app.route("/rename_description", methods=["POST", "GET"])
@login_required
def rename_description():
    
    # Load all user's table name from a session.
    table_name = session["table_name"]
    
    # Load the description to be renamed.
    description_to_rename = session["description_to_rename"]
    
    if request.method == "POST":
        
        # Get the new name for the description.
        new_description = request.form.get("new_description")
        
        # Udpate the entire database for description.
        db.execute("UPDATE ? SET description = ? WHERE description = ?",  table_name[4], new_description, description_to_rename)
        
        # Update the previous transaction to the new description.
        db.execute("UPDATE ? SET description = ? WHERE description = ?",  table_name[2], new_description, description_to_rename)

        # Redirect back to the edit description route.
        # Load all user's description.
        descriptions = db.execute("SELECT description FROM ?", table_name[4])
            
        return render_template("edit_description.html", descriptions=descriptions)

    else:
        return render_template("rename_description.html", description_to_rename=description_to_rename)
        
        
@app.route("/create_description", methods=["POST"])
@login_required
def create_description():
    
    if request.method == "POST":
        
        # Load user's table name.
        table_name = session["table_name"]
        
        # Get the inputted description by the user.
        new_description = request.form.get("created_description")
        
        # User input a description.
        if new_description:
            # Insert new description in the database if new.
            if len(db.execute("SELECT description FROM ? WHERE description = ?", table_name[4], new_description)) == 0:
                db.execute("INSERT INTO ? (description) VALUES (?)", table_name[4], new_description)
            else:
                return apology("Description already exists!")
            
        # User did not input a description, just reload the page.
        else:
            return redirect("/edit_description")
        
    # Redirect back to the edit description route.
    # Load all user's description.
    descriptions = db.execute("SELECT description FROM ?", table_name[4])
            
    return render_template("edit_description.html", descriptions=descriptions)

    
@app.route("/delete_description", methods=["POST"])
@login_required
def delete_description():
    
    # Load all user's table name from a session.
    table_name = session["table_name"]
    
    if request.method == "POST":
        # Remove the description selected by the user.
        description_to_delete = request.form.get("description_to_delete")
        
        if description_to_delete:
            db.execute("DELETE FROM ? WHERE description = ?", table_name[4], description_to_delete)

    # Redirect back to the edit description route.
    # Load all user's description.
    descriptions = db.execute("SELECT description FROM ?", table_name[4])
        
    return render_template("edit_description.html", descriptions=descriptions)
    
    
@app.route("/edit_account", methods=["GET", "POST"])
@login_required
def edit_account():
            
    # Load user's table name.
    table_name = session["table_name"]    

    if request.method == "POST":
        
        # Get the description to rename and save it into a session.
        session["account_to_rename"] = request.form.get("account_to_edit")
        
        return redirect("/rename_account")
    
    else:
        
        # Load all user's description.
        accounts = db.execute("SELECT account_name FROM ?", table_name[0])
        
        return render_template("edit_account.html", accounts=accounts)


@app.route("/rename_account", methods=["POST", "GET"])
@login_required
def rename_account():
    
    # Load all user's table name from a session.
    table_name = session["table_name"]
    
    # Load the description to be renamed.
    account_to_rename = session["account_to_rename"]
    
    # Get account's current balance.
    current_account_balance = db.execute("SELECT account_balance FROM ? WHERE account_name = ?", table_name[0], account_to_rename)[0]["account_balance"]
        
    if request.method == "POST":
        
        # Get the new name for the account.
        new_account = request.form.get("new_account")
        
        # Get the new balance for the account.
        new_balance = request.form.get("new_balance")
            
        # Update user's balance if the user changed the balance.
        if new_balance:
            db.execute("UPDATE ? SET account_balance = ? WHERE account_name = ?", table_name[0], new_balance, account_to_rename)

        # Update the user's seelcted account.
        if new_account:
            # Udpate the entire database for account.
            db.execute("UPDATE ? SET account_name = ? WHERE account_name = ?",  table_name[0], new_account, account_to_rename)
                    
            # Update the previous transaction to the new account.
            db.execute("UPDATE ? SET account_1 = ? WHERE account_1 = ?",  table_name[2], new_account, account_to_rename)

            
        # Redirect back to the edit account route.
        # Load all user's accounts..
        accounts = db.execute("SELECT account_name FROM ?", table_name[0])
                    
        return render_template("edit_account.html", accounts=accounts)

    else:
        return render_template("rename_account.html", account_to_rename=account_to_rename, current_account_balance=current_account_balance)


@app.route("/create_account", methods=["POST"])
@login_required
def create_account():
    
    if request.method == "POST":
        
        # Load user's table name.
        table_name = session["table_name"]
        
        # Get the inputted description by the user.
        new_account = request.form.get("created_account")
        
        # Proceed account creation if user input a new account.
        if new_account:
            
            # Get the initial amount the user set.
            initial_amount = request.form.get("initial_amount")
            initial_amount = 0 if not initial_amount else int(initial_amount)
            
            # Insert new description in the database if new.
            if len(db.execute("SELECT account_name FROM ? WHERE account_name = ?", table_name[0], new_account)) == 0:
                db.execute("INSERT INTO ? (account_name, account_balance) VALUES (?, ?)", table_name[0], new_account, initial_amount)
            else:
                return apology("Account already exists!")
        else:
            return redirect("/edit_account")
        
    # Redirect back to the edit description route.
    # Load all user's description.
    accounts = db.execute("SELECT account_name FROM ? ORDER BY id ASC", table_name[0])
            
    return render_template("edit_account.html", accounts=accounts)


@app.route("/delete_account", methods=["POST"])
@login_required
def delete_account():
    
    # Load all user's table name from a session.
    table_name = session["table_name"]
    
    if request.method == "POST":
        # Remove the description selected by the user.
        account_to_delete = request.form.get("account_to_delete")
        
        if account_to_delete:
            db.execute("DELETE FROM ? WHERE account_name = ?", table_name[0], account_to_delete)
        
    # Redirect back to the edit account route.
    # Load all user's description.
    accounts = db.execute("SELECT account_name FROM ?", table_name[0])
    
    return render_template("edit_account.html", accounts=accounts)
    

@app.route("/pay_debt", methods=["POST"])
@login_required
def pay_debt():
     
    # Load user's table names.
    table_name = session["table_name"] 
             
    # Get the name the user is indebted to and the amount.
    name = request.form.get("name")
    amount = request.form.get("amount")

    # Load all user's added  accounts.
    accounts = db.execute("SELECT account_name, account_balance FROM ?", table_name[0])
        
    # Redirect user to a form for debt payment processing.
    return render_template("pay_debt.html", name=name, amount=amount, accounts=accounts)
    


@app.route("/pay_debt_2", methods=["POST"])
@login_required
def pay_debt_2():
                
    # Update the transaction in the session for processing.
    session["transaction"][1] = "Payment to " + request.form.get("name")
    session["transaction"][2] = "Debt Payment"
    session["transaction"][3] = float(request.form.get("amount"))
    session["transaction"][4] = request.form.get("account")
    session["transaction"][5] = request.form.get("name")
    
    # process transaction in the "/regular" route.
    return redirect("/lend_borrow")

                 
@app.route("/edit_debt_lend", methods=["GET", "POST"])
@login_required
def edit_debt_lend():
            
    return render_template("edit_debt_lend.html")


@app.route("/lend")
@login_required
def lend():
    """Show user's lend list."""
    
    # Load user's table's names.
    table_name = session["table_name"]
    
    # Load all the entities the user lend money to.
    lends = db.execute("SELECT name, ABS(balance) as balance FROM ? WHERE balance < 0", table_name[3])

    return render_template("lend.html", lends=lends)

    
@app.route("/borrow")
@login_required
def borrow():

    # Load user's table's names.
    table_name = session["table_name"]
    
    # Load all the entities where the user borrowed money.
    debts = db.execute("SELECT name, ABS(balance) as balance FROM ? WHERE balance > 0", table_name[3])

    return render_template("debt.html", debts=debts)


@app.route("/transfer", methods=["GET", "POST"])
@login_required
def transfer():
    
    # Load user's current transaction information from a session.
    transaction = session["transaction"]
    
    # Load user's table's name from a session.
    table_name = session["table_name"]

    if request.method == "POST":
        
        account_to_transfer = request.form.get("account_to_transfer")
                
        # Update user's selected account.
        db.execute("UPDATE '{}' SET account_balance = account_balance - {} WHERE account_name = '{}'".format(table_name[0], *transaction[3:]))
        
        # Update user's selected account.
        db.execute("UPDATE '{}' SET account_balance = account_balance + {} WHERE account_name = '{}'".format(table_name[0], transaction[3], account_to_transfer))
    
        # Update user's transaction history.
        db.execute("INSERT INTO {} (description, category, amount, account_1, account_2)\
                VALUES ('{}', '{}', {}, '{}', '{}')".format(*transaction, account_to_transfer))

        return redirect("/history")

    else:
        
        # Load all user's added  accounts.
        accounts = db.execute("SELECT * FROM ? WHERE account_name != ?", table_name[0], transaction[4])

        return render_template("transfer.html", accounts=accounts, category=transaction[2])
    
    
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
            str(username + "_debt_receivable"),
            str(username + "_description")]
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

        for j in range(2):
            account_name = str(f"Savings {j + 1}")
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
            ('Transfer', 0, 0),\
            ('Debt', 1, 1), ('Lend', -1, 1),\
            ('Debt Payment', -1, 0), ('Lend Collection', 1, 0)", table_name[1])

        # Create user's transaction history database.
        db.execute("CREATE TABLE ? (\
            id INTEGER PRIMARY KEY,\
            time TIMESTAMP DEFAULT (datetime('now', 'localtime')),\
            description TEXT,\
            amount REAL,\
            category TEXT,\
            account_1 TEXT,\
            account_2 TEXT,\
            lend TEXT,\
            borrow TEXT)", table_name[2])
                
        # Create user's debt and receivable tables.
        db.execute("CREATE TABLE ? (id PRIMARY KEY, name TEXT, balance REAL)",  table_name[3])
        
        # Create user's default description.
        db.execute("CREATE TABLE ? (id PRIMARY KEY, description TEXT, group_1 TEXT, group_2 TEXT, group_3 TEXT, group_4 TEXT, group_5 TEXT)", table_name[4])
                        
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