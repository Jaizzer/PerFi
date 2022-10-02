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
            request.form.get("account"), 
            request.form.get("description")]
        
        # Reload page if user did not input anythin.
        if None in session["transaction"]:
            return redirect("/")

        # Check if user completed all the inputs.
        else:
            
            # Get the current balance of the user's selected account.
            current_balance = db.execute("SELECT balance FROM ? WHERE name = ?", table_name[0], session["transaction"][4])[0]["balance"]
            
            # Check if user has enough money to give/spend/pay.
            if session["transaction"][3] > current_balance and session["transaction"][2] not in ["Income", "Debt"]:
                return apology(f"{session['transaction'][4]} does not have enough balance for the transaction")
            
            # Classify  transaction whether it's regular or involves lend/borrow.
            transaction_classifier = db.execute("SELECT lend_or_borrow FROM ? WHERE name = ?", table_name[1], session["transaction"][2])[0]["lend_or_borrow"]
            
            # Redirect user to the corresponding route.
            route_name = "regular" if transaction_classifier == 0 else "lend_or_borrow"
            
            # Redirect to the corresponding route.
            return redirect(f"/{route_name}")

    else:
        
        # Load all user's accounts.
        accounts = db.execute("SELECT name, balance FROM ?", table_name[0])
        
        # Load all user's descriptions.
        descriptions = db.execute("SELECT name FROM ? ORDER BY name", table_name[4])
        
        # Load transaction categories excluding 'Debt Payment' and 'Lend Collection'.
        categories = db.execute("SELECT name FROM ? WHERE (name != 'Debt Payment' AND name != 'Lend Collection')", table_name[1])
                        
        return render_template("home.html", accounts=accounts, categories=categories, username=table_name[2], descriptions=descriptions)


@app.route("/regular")
@login_required
def regular():
    
    # Load user's table's name from a session.
    table_name = session["table_name"]

    # Determine whether to use addition or subtraction.
    operation = db.execute("SELECT operation FROM ? WHERE name = ?", table_name[1], session["transaction"][2])[0]["operation"]
    
    # Make the amount positive (Income) or negative (Expense).
    session["transaction"][3] = operation * session["transaction"][3]

    # Load user's current transaction information from a session.
    transaction = session["transaction"]

    # The category is transfer.
    if operation == 0:
    
        # Redirect user to transfer route.
        return redirect("/transfer")

    # The category is either "Income" or "Expense".
    else:
        
        # Swap receiver (user's account) and sender (description) if transaction type is "Expense."
        if transaction[3] < 0:
                        
            temp = transaction[5]
            transaction[5] = transaction[4]
            transaction[4] = temp
        
        # Update user's selected account.
        db.execute("UPDATE ? SET balance = balance + ?\
            WHERE name = ?", table_name[0], transaction[3], transaction[4])
                
    # Update user's transaction history.
    db.execute("INSERT INTO {} (description, category, amount, receiver, sender)\
            VALUES ('{}', '{}', {}, '{}', '{}')".format(*transaction))

    return redirect("/history")


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
        db.execute("UPDATE '{}' SET balance = balance - {} WHERE name = '{}'".format(table_name[0], *transaction[3:]))
        
        # Update user's selected account.
        db.execute("UPDATE '{}' SET balance = balance + {} WHERE name = '{}'".format(table_name[0], transaction[3], account_to_transfer))
    
        # Update user's transaction history.
        db.execute("INSERT INTO {} (description, category, amount, receiver, sender)\
                VALUES ('{}', '{}', {}, '{}', '{}')".format(*transaction, account_to_transfer))

        return redirect("/history")

    else:
        
        # Load all user's added  accounts.
        accounts = db.execute("SELECT * FROM ? WHERE name != ?", table_name[0], transaction[4])

        return render_template("transfer.html", accounts=accounts, category=transaction[2])


@app.route("/lend_or_borrow", methods=["GET", "POST"])
@login_required
def lend_or_borrow():
    
    # Load user's table's name from a session.
    table_name = session["table_name"]

    if request.method == "POST": 
        
        # Load user's current transaction information from a session.
        transaction = session["transaction"]
        
        # Get the name where the user borrowed or lended money.
        name = request.form.get("name")
        session["name"] = name
        
        # Reload page if user did not input a name.
        if not name:
            return redirect("/lend_or_borrow")
                
        # Get the type of transaction.
        transaction_type = transaction[2]    
                                                                                 
        # Update transaction 5.
        transaction[5] = name
        
        # Turn amount to positive (Debt/Lend Collection) or negative (Lend/Debt Payment).
        operation = db.execute("SELECT operation FROM ? WHERE name = ?", table_name[1], transaction_type)[0]["operation"]
        transaction[3] = operation * transaction[3]

        # Update user's selected account.
        db.execute("UPDATE ? SET balance = balance + ? WHERE name = ?", table_name[0], transaction[3], transaction[4])
        
        # Check if the person already exists in the user's current debt/lend database.
        existence = len(db.execute("SELECT name FROM ? WHERE ((name = ?) AND (type = ? OR type = 'synched'))", table_name[3], name, transaction_type))
                
        # Insert new table row if the person does not currently exists on the user's debt/lend database.
        if existence == False and transaction_type not in ["Debt Payment", "Lend Collection"]: 
            db.execute("INSERT INTO ? (name, balance, type) VALUES (?, ?, ?)", table_name[3], name, transaction[3], transaction[2])
            
        # Update table row if the person already exists in the user's current debt/lend database.
        else:
            
            # Classify debt payment as lend (subtraction) and payment collection as debt (addition)
            if transaction_type in ["Debt Payment", "Lend Collection"]:
                
                transaction_type = "Debt" if transaction_type == "Debt Payment" else "Lend"
                
                # Remember transaction type.
                session["transaction"][2] = transaction_type
                
            # Update the user's debt/lend database.           
            db.execute("UPDATE ? SET balance = balance + ? WHERE ((name = ?) AND (type = ? OR type = 'synched'))",  table_name[3], transaction[3], name, transaction_type)
            
        # Swap receiver(Account 2) and sender (Account 1) if user will receive the money.
        if transaction[3] < 0:
                        
            temp = transaction[5]
            transaction[5] = transaction[4]
            transaction[4] = temp

        # Update user's transaction history.
        db.execute("INSERT INTO {} (description, category, amount, receiver, sender) VALUES ('{}', '{}', {}, '{}', '{}')".format(*transaction))
        
        # Find th opposite transaction type of the current transaction type.
        opposite_transaction_type = "Lend" if transaction_type == "Debt" else "Debt"     
        session["opposite_transaction_type"] = opposite_transaction_type
        
        # Get the person in the opposite list if exists.
        opposite_person = db.execute("SELECT name FROM ? WHERE name = ? and type = ?", table_name[3], name, opposite_transaction_type)
            
        # Check if the person in the opposite list exists.
        opposite_existence = False if len(opposite_person) == 0 else True
        
        # Ask user if he/she wants to synch two matching names from opposite lists.
        if opposite_existence == True:
            return redirect("/synch")

        # Redirect to transaction history if ther is nothing to synch.
        else:
            # Redirect user to history.  
            return redirect(f"/history")
    
    else:
        
        # Load the people where user borrowed or lended money.        
        people =  db.execute("SELECT * FROM ? WHERE (type = ? OR type = 'synched')", table_name[3], session["transaction"][2])
        
        # Render the form.
        return render_template("lend_or_borrow.html", category=session["transaction"][2], people=people)


@app.route("/synch", methods=["POST","GET"])
@login_required
def synch():
    
    # Load user's table names,
    table_name = session["table_name"]
                
    # Update values if synch request came from debt/edit list.
    if request.form.get("name"):
        name = request.form.get("name")
        type = request.form.get("type")
        opposite_transaction_type = "Debt" if type == "Lend" else "Lend"
        approval = "Yes"
        request_source = request.form.get("request_source")
    
    # Update values if synch request came from actual transaction process.
    else:
        name = session["name"]
        opposite_transaction_type = session["opposite_transaction_type"]
        approval = request.form.get("approval")
        type = session["transaction"][2]
        request_source = "history"

    if request.method == "POST":
        
        # User agreed to synch.
        if approval == "Yes":
            
            # Get the balance of the opposite name.
            opposite_balance = db.execute("SELECT balance FROM ? WHERE name = ? AND type = ?", table_name[3], name, opposite_transaction_type)[0]["balance"]
            
            # Add the balances to row B.
            db.execute("UPDATE ? SET balance = balance + ? WHERE (name = ? AND type = ?)", table_name[3], opposite_balance, name, type)
            
            # Delete row A.
            db.execute("DELETE FROM ? WHERE name = ? AND type = ?", table_name[3], name, opposite_transaction_type)
            
            # Set row B to "synched".
            db.execute("UPDATE ? SET type = 'synched' WHERE name = ? AND type = ?", table_name[3], name, type)
        
        # Redirect user to the current list..
        return redirect(f"/{request_source}")
        
    else:
        
        # Ask user for synch confirmation.
        return render_template("synch_confirmation.html", name=name, opposite_transaction_type=opposite_transaction_type)
        
@app.route("/unsynch", methods=["POST"])
@login_required
def unsynch():
    
    # Load all user's table name.
    table_name = session["table_name"]
    
    # Get the name to synch.
    name = request.form.get("name")
    
    # Get the source of unsynch request.
    request_source = request.form.get("request_source")
    
    # Get the current balance of the synched person.
    balance = db.execute("SELECT balance FROM ? WHERE name = ? and type = 'synched'", table_name[3], name)[0]["balance"]
    
    # Split the table depending on the amount of balance.
    if balance > 0:
        db.execute("UPDATE ? SET balance = balance, type = 'Debt' WHERE name = ?", table_name[3], name)
        db.execute("INSERT INTO ? (name, balance, type) VALUES (?, 0, 'Lend')", table_name[3], name)
        
    elif balance < 0:
        db.execute("UPDATE ? SET balance = balance, type = 'Lend' WHERE name = ?", table_name[3], name)
        db.execute("INSERT INTO ? (name, balance, type) VALUES (?, 0, 'Debt')", table_name[3], name)
        
    else:
        db.execute("UPDATE ? SET balance = 0, type = 'Debt' WHERE name = ?", table_name[3], name)
        db.execute("INSERT INTO ? (name, balance, type) VALUES (?, 0, 'Lend')", table_name[3], name)
    
    # Redirect user back to the list.
    return redirect(f"/{request_source}")


@app.route("/pay_collect", methods=["POST", "GET"])
@login_required
def pay_collect():
     
    # Load user's table names.
    table_name = session["table_name"] 
    
    if request.method == "POST":
        
        # Load description prefix.
        pay_collect = session["pay_collect"]
        name = session["name"]
                
        # Get the transaction amount.
        transaction_amount = request.form.get("amount")
        
        # Save the account the user selected.
        account = request.form.get("account")
        
        # Reload if the user did not input account to use.
        if account == None or transaction_amount == "":
            return redirect("/pay_collect")
        
        # User input an account.
        else:
            
            # Get the account's current balance.
            balance = db.execute("SELECT balance FROM ? WHERE name = ?", table_name[0], account)[0]["balance"]

            # Set transaction amount to type float.
            transaction_amount = float(transaction_amount)
            
            # Send error if current balance is not enough for the transaction that will take money from him/her.
            if balance < transaction_amount and pay_collect == "Payment to":
                return apology(f"{account} does not have enough balance for the transaction.")
            
            # Account has enough balance.
            else:
                                
                # Determine type of transaction
                payment_collection = "Debt Payment" if pay_collect == "Payment to" else "Lend Collection"
                    
                # Update the transaction in the session for processing.
                session["transaction"][1] = pay_collect + " " + name
                session["transaction"][2] = payment_collection
                session["transaction"][3] = transaction_amount
                session["transaction"][4] = account
                session["transaction"][5] = name
                    
                # Determine column title for the confirmation page.
                column_4 = "None"
                column_5 = "None"
                
                if pay_collect == "Payment to":
                    column_4 = "Deducted To "
                    column_5 = "Paid to"
                else:
                    column_4 = "Added to "
                    column_5 = "Collected from"
                
                # process transaction in the "/regular" route.
                return render_template("confirmation.html", transactions=session["transaction"][1:], column_4=column_4, column_5=column_5, name = name)    

    else:
        # Redirect user to a form for debt payment processing.
        return render_template("pay_collect.html", name=session["name"], amount=session["amount"], accounts=session["accounts"],\
            pay_collect=session["pay_collect"], caption=session["caption"], block_title=session["block_title"])
    
    
@app.route("/edit", methods=["GET", "POST"])
@login_required
def edit():
    
    if request.method == "POST":
        
        # Load the user's username.
        username = session["username"]
        
        # Identify what database table to edit.
        table_type = request.form.get("table_to_edit")
        
        # Create a debt or lend filter if invovled in the transaction.
        filter = None
        
        # Create corresponding form placeholder base on the table type.
        placeholder_caption = "Add new " + table_type
            
        # Create corresponding block title.
        block_title = "Edit " + table_type
            
        # The table type is either debt or lend.
        if table_type in ["Lend", "Debt"]:
            
            # Set filter to either debt or lend.
            filter = table_type
                        
            # Create corresponding block title.
            block_title = "Edit " + table_type + " list"
            
            # Get the elements from the table to edit.
            elements = db.execute("SELECT name FROM ? WHERE (type LIKE ? or type = 'synched')", (username + "_debt_receivable"), filter)

            # Set table type as debt_receivable.
            table_type = "debt_receivable"
            
        # The table type is not lend nor lend.
        else:
            
            # Get the elements from the table to edit.
            elements = db.execute("SELECT name FROM ? ", (username + "_" + table_type))
              
        # Make balance form hidden if the user will edit description and visible otherwise.
        balance_visibility = "hidden" if table_type != "accounts" else "number"
        name_visibility = "hidden" if table_type == "debt_receivable" else "text"
        button_visibility = 'hidden' if table_type == "debt_receivable" else "None"
        
        # Remmember html variables for later use.
        session["table_type"] = table_type
        session["balance_visibility"] = balance_visibility
        session["button_visibility"] = button_visibility
        session["name_visibility"] = name_visibility
        session["placeholder_caption"] = placeholder_caption
        session["block_title"] = block_title
        session["filter"] = filter
                
        # Redirect to edit_2 route.
        return redirect("/edit_2")
        
    else:
        
        return render_template("edit.html")

@app.route("/edit_2", methods=["POST", "GET"])
@login_required
def edit_2():
    
    # Load the user's username.
    username = session["username"]
    
    # Load the table type from a session.
    table_type = session["table_type"]
    
    # Get the specific table name to edit.
    table_to_edit = username + "_" + table_type
    
    # Remember table to edit.
    session["table_to_edit"] = table_to_edit
    
    if request.method == "POST":
        
        # Get the chosen edit method.
        method = request.form.get("method")
                                
        # User wants to modify or create.
        if method in ["modify", "create"]:
            
            # Set balance form creator to True if type involves balance (account, debt, lend).
            balance_form_creator = True if table_type != "description" else False
            
            # Set synch button creator to True if type involves debt or lend.
            synch_button_creator = True if table_type in ["debt", "lend"] else False
            
            # User wants to modify.
            if method == "modify":
                
                # Get the modified name for the account and save it into a sesison.
                session["current_element_name"] = request.form.get("current_element_name")
                
                # Reroute user to the modification form.
                return redirect("/modify")
                                        
            # user wants to create
            elif method == "create":
                
                # Get the name to create.
                element_to_create = request.form.get("element_to_create")
                
                # User input an element.
                if element_to_create:
                    
                    # Insert new description in the database if new.
                    if len(db.execute("SELECT name FROM ? WHERE name = ?", table_to_edit, element_to_create)) == 0:
                        db.execute("INSERT INTO ? (name) VALUES (?)", table_to_edit, element_to_create)
                        
                        # The element to create has a balance category.
                        if table_type != "description":
                            
                            # Get the balance to put it there is any.
                            new_element_balance = request.form.get("new_element_balance")
                                                        
                            # User did not input any in the balance form.
                            if not new_element_balance:
                                
                                # Set balance to zero if user did not input any.
                                new_element_balance = float(0)
                                
                            # Put the balance in.
                            db.execute("UPDATE ? SET balance = ? WHERE name = ?", table_to_edit, float(new_element_balance), element_to_create)
                                                    
                    else:
                    
                        # Send error message to user.
                        return apology(f"{element_to_create} already exists!")

                else:
                    
                    # Return error message.
                    return apology("Input missing")
        
            # User wants to delete.
        else:
                
            # Load the element to delete.
            element_to_delete = request.form.get("element_to_delete")

            # Delete the element selected by the user.
            if element_to_delete:
                
                # If user will delete in accounts or descriptions table.
                if table_type in ["accounts", "description"]:
                    db.execute("DELETE FROM ? WHERE name = ?", table_to_edit, element_to_delete)
                
                # User will delete from the debt_receivable table.
                else:
                    db.execute("DELETE FROM ? WHERE ((name = ?) AND (type = ? or type = 'synched'))", table_to_edit, element_to_delete, session["filter"])
                        
        return redirect("/edit_2")
        
    else:
        
        # Unload all html variables from a session.
        balance_visibility = session["balance_visibility"]
        name_visibility = session["name_visibility"]
        button_visibility = session["button_visibility"]
        placeholder_caption = session["placeholder_caption"]
        block_title = session["block_title"]
        filter = session["filter"]
        
        # Identify table type.
        table_type = session["table_type"]
        
        # Load all the elements depending on the type.
        if table_type == "debt_receivable":
            
            # Load all debt/receivable elements.
            elements = db.execute("SELECT name FROM ? WHERE (type LIKE ? or type = 'synched')", table_to_edit, filter)
        
        else:
            
            # Load non debt/receivable elemenets (descriptions or accounts)
            elements = db.execute("SELECT name FROM ? ", table_to_edit)
        
        # Redirect user to the corresponding page.
        return render_template("edit_general.html", elements=elements, placeholder_caption=placeholder_caption,\
            balance_visibility=balance_visibility, name_visibility=name_visibility, button_visibility=button_visibility,\
            table_type=table_type, block_title=block_title, strip_quote=strip_quote)


@app.route("/modify", methods=["POST", "GET"])
@login_required
def modify():
    
    # Load user's username.
    username = request.form.get("username")
    
    # Load all user's table name from a session.
    table_type = session["table_type"]
    
    # Load the table to edit from a session.
    table_to_edit = session["table_to_edit"]
    
    # Load the description to be renamed.
    current_element_name = session["current_element_name"]
    
    # Load the element's current balance if table type is accounts.
    if table_type == "accounts":
        
        current_element_balance = db.execute("SELECT balance FROM ? WHERE name = ?", table_to_edit, current_element_name)[0]["balance"]
        
        # Set the balance form to text.
        visibility = "text"
                
    else:
        
        current_element_balance = None
        
         # Set the balance form's visibility to hidden..
        visibility = "hidden"
    

    if request.method == "POST":
        
        # Get the new element name.
        new_element_name = request.form.get("new_element_name")
        
        # Get the new balance of the element if table type involves balance.
        new_element_balance = request.form.get("new_element_balance")
            
        # Process the user's input for the new name.
        if new_element_name:
            
            # Check the existence of username in the database.
            existence = db.execute("SELECT name FROM ? where name = ?", table_to_edit, new_element_name)
            
            # Name already exists.
            if existence:
                return apology(f"{new_element_name} already exists!")
            
            # Name does not exist.
            else:
                
                # User wants to modify elements from description or account tables.
                if table_type != "debt_receivable":
                    db.execute("UPDATE ? SET name = ? WHERE name = ?",  table_to_edit, new_element_name, current_element_name)
                    
                # User wants to modifyn debt/receivables table.
                else:
                    db.execute("UPDATE ? SET name = ? WHERE ((name = ?) AND (type = ? or type = 'synched'))", table_to_edit, new_element_name, current_element_name, session["filter"])
                
            # Set the current element name to its new name.
            current_element_name = new_element_name
            
        # Update the element's current amound if the user input one.
        if new_element_balance and table_type != "description":
            db.execute("UPDATE ? SET balance = ? WHERE name = ?",  table_to_edit, new_element_balance, current_element_name)

        # Redirect back to edit menu.          
        return redirect("/edit_2")

    else:
        
        #return apology(str(current_element_balance) + str(current_element_name))
        return render_template("modify.html", current_element_name=current_element_name, current_element_balance=current_element_balance,\
            visibility=visibility, table_type=session["table_type"])

                 
@app.route("/lend",methods=["GET", "POST"])
@login_required
def lend():
    """Show user's lend list."""
    
    # Load user's table's names.
    table_name = session["table_name"]
    
    # Load all the entities the user lend money to.
    lends = db.execute("SELECT name, IIF(balance >= 0, 0, ABS(balance)) AS balance, type FROM ? WHERE type = 'Lend' or type = 'synched'", table_name[3])
    
    # Load user's debt list.
    debts = db.execute("SELECT name FROM ? WHERE type = 'Debt'", table_name[3])

    if request.method == "POST":
        
        # Get the name the user is indebted to and the amount.
        session["name"] = request.form.get("name")
        session["amount"] = request.form.get("amount")
        session["pay_collect"] = request.form.get("pay_collect")
        
        # Determine caption for the html.
        if session["pay_collect"] == "Payment to":
            session["caption"] = "Borrowed Money"
            session["block_title"] = "Pay Debt"
            
        else:
            session["caption"] = "Lended Money"
            session["block_title"] = "Collect Lend"
        
        # Load all user's added  accounts.
        session["accounts"] = db.execute("SELECT name, balance FROM ?", table_name[0])

        return redirect("/pay_collect")
    
    else:
        return render_template("lend.html", debts=debts, lends=lends)

    
@app.route("/debt", methods=["GET", "POST"])
@login_required
def borrow():

    # Load user's table's names.
    table_name = session["table_name"]
    
    # Load all the entities where the user borrowed money.
    debts = db.execute("SELECT name, IIF(balance <= 0, 0, ABS(balance)) AS balance, type FROM ? WHERE type = 'Debt' or type = 'synched'", table_name[3])
    
    # Load user's lend list.
    lends = db.execute("SELECT name FROM ? WHERE type = 'Lend'", table_name[3])
    
    if request.method == "POST":
        
        # Get the name the user is indebted to and the amount.
        session["name"] = request.form.get("name")
        session["amount"] = request.form.get("amount")
        session["pay_collect"] = request.form.get("pay_collect")
        
        # Determine caption for the html.
        if session["pay_collect"] == "Payment to":
            session["caption"] = "Borrowed Money"
            session["block_title"] = "Pay Debt"
            
        else:
            session["caption"] = "Lended Money"
            session["block_title"] = "Collect Lend"
        
        # Load all user's added  accounts.
        session["accounts"] = db.execute("SELECT name, balance FROM ?", table_name[0])

        return redirect("/pay_collect")
    
    else:
        return render_template("debt.html", debts=debts, lends=lends)
    
    
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
        
        # Store user's username.
        username = session["username"]
        
        # Remember user's table names.
        session["table_name"] = [
            str(username + "_accounts"),
            str(username + "_categories"),
            username,
            str(username + "_debt_receivable"),
            str(username + "_description")]
        
        # Initialize transaction information list.
        session["transaction"] = [None, None, None, None, None, None]

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
            name TEXT,\
            balance REAL)", table_name[0])
        
        # Populate user's account with default accounts.
        for i in range(3):
            name = str(f"Account {i + 1}")
            db.execute("INSERT INTO ? (name, balance) VALUES (?, ?)", table_name[0], name, 0)        
        for j in range(2):
            name = str(f"Savings {j + 1}")
            db.execute("INSERT INTO ? (name, balance) VALUES (?, ?)", table_name[0], name, 0)        

        # Create users' category database.
        db.execute("CREATE TABLE ? (\
            id INTEGER PRIMARY KEY,\
            name TEXT,\
            operation INTEGER,\
            lend_or_borrow INTEGER)", table_name[1])
        
        # Populate user's transaction category with dafault categories.
        db.execute("INSERT INTO ? (\
            name, operation, lend_or_borrow)\
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
            receiver TEXT,\
            sender TEXT)", table_name[2])
                
        # Create user's debt and receivable tables.
        db.execute("CREATE TABLE ? (id PRIMARY KEY, name TEXT, balance REAL, type TEXT)",  table_name[3])
        
        # Create user's default description.
        db.execute("CREATE TABLE ? (id PRIMARY KEY, name TEXT, group_1 TEXT, group_2 TEXT, group_3 TEXT, group_4 TEXT, group_5 TEXT)", table_name[4])
                        
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

def strip_quote(value):
    """Remove quotation marks."""
    new_value = value.replace('"','')
    return new_value