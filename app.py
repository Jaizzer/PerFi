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
    
    # Remember user's username
    username = session["username"]
    
    if request.method == "POST":
        
        # Save all the transaction information into a list.
        session["transaction"] = [
            session["username"],
            request.form.get("description"), 
            request.form.get("category"), 
            request.form.get("amount", type=float), 
            request.form.get("account"), 
            request.form.get("description")]
        
        # Reload page if user did not input anything.
        if None in session["transaction"]:
            return redirect("/")

        # Check if user completed all the inputs.
        else:
            
            # Insert description in the database if it still does not exists.
            if len(db.execute("SELECT name FROM ? WHERE name = ?", table_name[4], request.form.get("description"))) == 0:
                db.execute("INSERT INTO ? (name) VALUES (?)", table_name[4], request.form.get("description"))
                
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
                        
        return render_template("home.html", accounts=accounts, categories=categories, username=username, descriptions=descriptions)


@app.route("/regular")
@login_required
def regular():
    
    # Load user's table's name from a session.
    table_name = session["table_name"]

    # Determine whether to use addition or subtraction.
    operation = db.execute("SELECT operation FROM ? WHERE name = ?", table_name[1], session["transaction"][2])[0]["operation"]
        
    # The category is transfer.
    if operation == 0:
    
        # Redirect user to transfer route.
        return redirect("/transfer")

    # The category is either "Income" or "Expense".
    else:
        # Make the amount positive (Income) or negative (Expense).
        session["transaction"][3] = operation * session["transaction"][3]

        # Load user's current transaction information from a session.
        transaction = session["transaction"]

        # Update user's selected account.
        db.execute("UPDATE ? SET balance = balance + ?\
            WHERE name = ?", table_name[0], transaction[3], transaction[4])

        # Swap receiver (user's account) and sender (description) if transaction type is "Expense."
        if transaction[3] < 0:
                        
            temp = transaction[5]
            transaction[5] = transaction[4]
            transaction[4] = temp
                        
    # Update user's transaction history.
    db.execute("INSERT INTO {} (description, category, amount, receiver, sender)\
            VALUES ('{}', '{}', {}, '{}', '{}')".format(*transaction))

    return redirect("/history")


@app.route("/transfer", methods=["GET", "POST"])
@login_required
def transfer():
    
    # Load the user's username.
    username = session["username"]

    # Load user's current transaction information from a session.
    transaction = session["transaction"]
    
    # Load user's table's name from a session.
    table_name = session["table_name"]

    if request.method == "POST":
        
        account_to_transfer = request.form.get("account_to_transfer")
                        
        # Update user's selected account.
        db.execute("UPDATE '{}' SET balance = balance - {} WHERE name = '{}'".format(table_name[0], *transaction[3:5]))
        
        # Update user's selected account.
        db.execute("UPDATE '{}' SET balance = balance + {} WHERE name = '{}'".format(table_name[0], transaction[3], account_to_transfer))
    
        # Update user's transaction history.
        db.execute("INSERT INTO {} (description, category, amount, receiver, sender)\
                VALUES ('{}', '{}', {}, '{}', '{}')".format(*transaction, account_to_transfer))

        return redirect("/history")

    else:
        
        # Load all user's added  accounts.
        accounts = db.execute("SELECT * FROM ? WHERE name != ?", table_name[0], transaction[4])

        return render_template("transfer.html", accounts=accounts, category=transaction[2], username=username)


@app.route("/lend_or_borrow", methods=["GET", "POST"])
@login_required
def lend_or_borrow():
    
    # Load user's table's name from a session.
    table_name = session["table_name"]
    
    # Load user's current transaction information from a session.
    transaction = session["transaction"]
    
    # Load the user's username.
    username = session["username"]

    if request.method == "POST": 
                
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
        
        # Create confirmation message.
        if transaction[2] == 'Debt':
            confirmation =  "Are you sure you want to borrow " + str(transaction[3]) + " from "
        else:
            confirmation =  "Are you sure you want to lend " + str(transaction[3]) + " to "

        # Render the form.
        return render_template("lend_or_borrow.html", category=transaction[2], people=people, amount=transaction[3], confirmation=confirmation, username=username)


@app.route("/synch", methods=["POST","GET"])
@login_required
def synch():
    
    # Load user's table names,
    table_name = session["table_name"]
    
    # Load the user's username.
    username = session["username"]

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
        return render_template("synch_confirmation.html", name=name, opposite_transaction_type=opposite_transaction_type, username=username)
        
        
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
    
    # Load the user's username.
    username = session["username"]

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
            pay_collect=session["pay_collect"], caption=session["caption"], block_title=session["block_title"], username=username)
    
    
@app.route("/edit_description", methods=["GET", "POST"])
@login_required
def edit_description():
    
    # Load the user's username.
    username = session["username"]
    
    # Save the table to edit.
    table_to_edit = username + "_description"
    
    if request.method == "POST":
    
        # Get the chosen edit method.
        method = request.form.get("method")
                                
        # User wants to modify or create.
        if method in ["modify", "create"]:
            
            # User wants to modify.
            if method == "modify":
                
                # Get the modified name for the account and save it into a sesison.
                session["current_description"] = request.form.get("current_description")
                
                # Remember table to edit.
                session["table_to_edit"] = table_to_edit
                
                # Reroute user to the modification form.
                return redirect("/modify_description")
                                        
            # User wants to create
            elif method == "create":
                
                # Get the name to create.
                description_to_create = request.form.get("description_to_create")
                
                # User input an element.
                if description_to_create:
                    
                    # Insert new description in the database if new.
                    if len(db.execute("SELECT name FROM ? WHERE name = ?", table_to_edit, description_to_create)) == 0:
                        db.execute("INSERT INTO ? (name) VALUES (?)", table_to_edit, description_to_create)
                                                                            
                    else:
                    
                        # Send error message to user.
                        return apology(f"{description_to_create} already exists!")

                else:
                    
                    # Return error message.
                    return apology("Input missing")
        
            # User wants to delete.
        else:
                
            # Load the element to delete.
            description_to_delete = request.form.get("description_to_delete")

            # Delete the description
            db.execute("DELETE FROM ? WHERE name = ?", table_to_edit, description_to_delete)
        
        # Reload page.                
        return redirect("/edit_description")
        
    else:
        
        # Get all the descriptions from the database.
        descriptions = db.execute("SELECT name FROM ?", table_to_edit)
        
        # Render the descriptions
        return render_template("edit_description.html", descriptions=descriptions, username=username)
    
    
@app.route("/edit_debt", methods=["GET", "POST"])
@login_required
def edit_debt():
    
    # Load the user's username.
    username = session["username"]
    
    # Save the table to edit.
    table_to_edit = username + "_debt_receivable"
    
    if request.method == "POST":
    
        # Get the chosen edit method.
        method = request.form.get("method")
                                
        # User wants to modify or create.
        if method == "modify":
                            
            # Get the modified name for the debt and save it into a sesison.
            session["current_debt"] = request.form.get("current_debt")
            
            # Reroute user to the modification form.
            return redirect("/modify_debt")
                                                
        # User wants to delete.
        else:
                
            # Load the debt to delete.
            debt_to_delete = request.form.get("debt_to_delete")

            # Delete the debt
            db.execute("DELETE FROM ? WHERE name = ?", table_to_edit, debt_to_delete)
        
        # Reload page.                
        return redirect("/edit_debt")
        
    else:
        
        # Get all the debt from the database.
        debt = db.execute("SELECT name FROM ? WHERE type = 'Debt' OR type ='synched'", table_to_edit)
        
        # Render the descriptions
        return render_template("edit_debt.html", debts=debt, username=username)


@app.route("/edit_lend", methods=["GET", "POST"])
@login_required
def edit_lend():
    
    # Load the user's username.
    username = session["username"]
    
    # Save the table to edit.
    table_to_edit = username + "_debt_receivable"
    
    if request.method == "POST":
    
        # Get the chosen edit method.
        method = request.form.get("method")
                                
        # User wants to modify or create.
        if method == "modify":
                            
            # Get the modified name and save it into a sesison.
            session["current_lend"] = request.form.get("current_lend")
            
            # Reroute user to the modification form.
            return redirect("/modify_lend")
                                                
        # User wants to delete.
        else:
                
            # Load the debt to delete.
            lend_to_delete = request.form.get("lend_to_delete")

            # Delete the debt
            db.execute("DELETE FROM ? WHERE name = ?", table_to_edit, lend_to_delete)
        
        # Reload page.                
        return redirect("/edit_lend")
        
    else:
        
        # Get all the debt from the database.
        lends = db.execute("SELECT name FROM ? WHERE type = 'Lend' OR type ='synched'", table_to_edit)
        
        # Render the descriptions
        return render_template("edit_lend.html", lends=lends, username=username)
  

@app.route("/edit_account", methods=["GET", "POST"])
@login_required
def edit_account():
    
    # Load the user's username.
    username = session["username"]
    
    # Save the table to edit.
    table_to_edit = username + "_accounts"
    
    if request.method == "POST":
    
        # Get the chosen edit method.
        method = request.form.get("method")
                                
        # User wants to modify or create.
        if method in ["modify", "create"]:
            
            # User wants to modify.
            if method == "modify":
                
                # Get the modified name for the account and save it into a sesison.
                session["current_account"] = request.form.get("current_account")
                
                # Reroute user to the modification form.
                return redirect("/modify_account")
                                        
            # User wants to create
            elif method == "create":
                
                # Get the name to create.
                account_to_create = request.form.get("account_to_create")
                
                # User input an element.
                if account_to_create:
                    
                    # Account does not exist yet.
                    if len(db.execute("SELECT name FROM ? WHERE name = ?", table_to_edit, account_to_create)) == 0:
                        
                        # Insert the new account name.
                        db.execute("INSERT INTO ? (name) VALUES (?)", table_to_edit, account_to_create)
                        
                        # Get the balance to put in, if the user insert any.
                        new_account_balance = request.form.get("new_account_balance")
                                                    
                        # User did not input any in the balance form.
                        if not new_account_balance:
                            
                            # Set balance to zero if user did not input any.
                            new_account_balance = float(0)
                            
                        # Put the balance in.
                        db.execute("UPDATE ? SET balance = ? WHERE name = ?", table_to_edit, float(new_account_balance), account_to_create)

                    # Account name already exists.
                    else:
                    
                        # Send error message to user.
                        return apology(f"{account_to_create} already exists!")

                else:
                    
                    # Return error message.
                    return apology("Input missing")
        
            # User wants to delete.
        else:
                
            # Load the element to delete.
            account_to_delete = request.form.get("account_to_delete")

            # Delete the account
            db.execute("DELETE FROM ? WHERE name = ?", table_to_edit, account_to_delete)
        
        # Reload page.                
        return redirect("/edit_account")
        
    else:
        
        # Get all the descriptions from the database.
        accounts = db.execute("SELECT name FROM ?", table_to_edit)
        
        # Render the descriptions
        return render_template("edit_account.html", accounts=accounts, username=username)
    

@app.route("/modify_description", methods=["POST", "GET"])
@login_required
def modify_description():
    
    # Load table to edit.
    table_to_edit = session["table_to_edit"]
    
    # Load the user's username.
    username = session["username"]

    # Load the description to edit.
    current_description = session["current_description"]
    
    if request.method == "POST":
        
        # Get the new decription.
        new_description = request.form.get("new_description")
        
        # Process the user's input for the new description.
        if new_description:
            
            # Check the existence of username in the database.
            existence = db.execute("SELECT name FROM ? where name = ?", table_to_edit, new_description)
            
            # Name already exists.
            if existence:
                return apology(f"{new_description} already exists!")
            
            # Name does not exist.
            else:
                
                # Update description.
                db.execute("UPDATE ? SET name = ? WHERE name = ?",  table_to_edit, new_description, current_description)
                    
            # Set the current description to the new description.
            current_description = new_description
            
        # Redirect back to edit menu.          
        return redirect("/edit_description")

    else:
        
        return render_template("modify_description.html", current_description=current_description, username=username)
        

@app.route("/modify_debt", methods=["POST", "GET"])
@login_required
def modify_debt():
    
    # Load users username.
    username = session["username"]
    
    # Load table to edit.
    table_to_edit = username + "_debt_receivable"
    
    # Load the debt to edit.
    current_debt = session["current_debt"]
    
    if request.method == "POST":
        
        # Get the new decription.
        new_debt = request.form.get("new_debt")
        
        # Process the user's input for the new debt.
        if new_debt:
            
            # Check the existence of username in the database.
            existence = db.execute("SELECT name FROM ? WHERE (name = ? AND (type = 'Debt' or type = 'synched'))", table_to_edit, new_debt)
            
            # Name already exists.
            if existence:
                return apology(f"{new_debt} already exists!")
            
            # Name does not exist.
            else:
                
                # Update debt.
                db.execute("UPDATE ? SET name = ? WHERE name = ?",  table_to_edit, new_debt, current_debt)
                    
            # Set the current debt to the new debt.
            current_debt = new_debt
            
        # Redirect back to edit menu.          
        return redirect("/edit_debt")

    else:
        
        return render_template("modify_debt.html", current_debt=current_debt, username=username)


@app.route("/modify_lend", methods=["POST", "GET"])
@login_required
def modify_lend():
    
    # Load users username.
    username = session["username"]
    
    # Load table to edit.
    table_to_edit = username + "_debt_receivable"
    
    # Load the lend to edit.
    current_lend = session["current_lend"]
    
    if request.method == "POST":
        
        # Get the new decription.
        new_lend = request.form.get("new_lend")
        
        # Process the user's input for the new lend.
        if new_lend:
            
            # Check the existence of username in the database.
            existence = db.execute("SELECT name FROM ? WHERE (name = ? AND (type = 'Lend' or type = 'synched'))", table_to_edit, new_lend)
            
            # Name already exists.
            if existence:
                return apology(f"{new_lend} already exists!")
            
            # Name does not exist.
            else:
                
                # Update lend.
                db.execute("UPDATE ? SET name = ? WHERE name = ?",  table_to_edit, new_lend, current_lend)
                    
            # Set the current lend to the new lend.
            current_lend = new_lend
            
        # Redirect back to edit menu.          
        return redirect("/edit_lend")

    else:
        
        return render_template("modify_lend.html", current_lend=current_lend, username=username)


@app.route("/modify_account", methods=["POST", "GET"])
@login_required
def modify_account():
    
    # Load users username.
    username = session["username"]
    
    # Load table to edit.
    table_to_edit = username + "_accounts"

    # Load the account to edit.
    current_account = session["current_account"]

    # Load the amount.
    current_account_balance = db.execute("SELECT balance FROM ? WHERE name = ?", table_to_edit, current_account)[0]["balance"]

    if request.method == "POST":
        
        # Get the new decription.
        new_account = request.form.get("new_account")

        # Get the new decription.
        new_balance = request.form.get("new_account_balance")
        
        # Process the user's input for the new account.
        if new_account:
            
            # Check the existence of username in the database.
            existence = db.execute("SELECT name FROM ? WHERE name = ?", table_to_edit, new_account)
            
            # Name already exists.
            if existence:
                return apology(f"{new_account} already exists!")
            
            # Name does not exist.
            else:
                
                # Update account.
                db.execute("UPDATE ? SET name = ? WHERE name = ?",  table_to_edit, new_account, current_account)
                    
            # Set the current account to the new account.
            current_account = new_account

        # The user wants to update the account balance.
        if new_balance:  
            db.execute("UPDATE ? SET balance = ? WHERE name = ?",  table_to_edit, float(new_balance), current_account)
            
        # Redirect back to edit menu.          
        return redirect("/edit_account")

    else:
        
        return render_template("modify_account.html", current_account=current_account, current_account_balance=current_account_balance, username=username)

                 
@app.route("/lend",methods=["GET", "POST"])
@login_required
def lend():
    """Show user's lend list."""
        
    # Load users username.
    username = session["username"]

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
        return render_template("lend.html", debts=debts, lends=lends, username=username)

    
@app.route("/debt", methods=["GET", "POST"])
@login_required
def borrow():

    # Load user's table's names.
    table_name = session["table_name"]
        
    # Load users username.
    username = session["username"]

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
        return render_template("debt.html", debts=debts, lends=lends, username=username)
    
@app.route("/history")
@login_required
def history():
    """Show history of transactions"""    
    
    # Load users username.
    username = session["username"]

    transactions = db.execute("SELECT * FROM ? ORDER BY id DESC", session.get("username"))

    return render_template("history.html", transactions=transactions, username=username)


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
        message = ""

        # Error detector.
        error_detector = 0

        # Scenario 1: No username input.
        if not username:
            message = message + "\nno username"
            error_detector = 400

        # Scenario 2: There is username, but not unique.
        if len(db.execute(f"SELECT username FROM users WHERE username LIKE '{username}'")) != 0:
            message = message + "\nUsername not unique"
            error_detector = 400

        # Validate password submitted.
        # Scenario 1: No password input.
        if not password:
            message = message + "\nno password"
            error_detector = 400

        # Scenario 2: Password and confirm password did not match.
        elif password != confirm_password:
            message = message + "\npasswords did not match"
            error_detector = 400

        # Scenario 3: Password is not strong enough.
        elif check_password_strength(password) != 5:
            message = message + "\npassword not strong enough"
            error_detector = 400

        # User's registration has error/s.
        if error_detector != 0:

            # Redirect to apology page.
            return apology(message, error_detector)

        # User's registration is free from errors.
        else:
            
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

