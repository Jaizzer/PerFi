import os

import werkzeug
import string

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

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
db = SQL("sqlite:///finance.db")

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""

    # Load user id from a session.
    user_id = session.get("user_id")

    # Get the symbol of user-owned companies.
    symbols = db.execute("SELECT symbol FROM user_?", user_id)

    # Load user's current balance into a session.
    session["cash"] = round((float(db.execute("SELECT cash FROM users WHERE id = ?", user_id)[0]["cash"])), 2)

    # Initialize the list of dictionaries containing user-owned stock infos.
    portfolio = []

    # Update user-owned companies' current prices.
    symbols = db.execute("SELECT symbol FROM user_?", user_id)
    for symbol in symbols:

        # Lookup companies current price.
        current_price = lookup(symbol["symbol"])["price"]

        # Populate portfolio,=.
        portfolio += db.execute(
            "SELECT company, symbol, {0} AS price, CAST(shares AS INT) AS shares, round(shares * {0}, 2) AS total FROM user_{1} WHERE symbol = '{2}'".format(
                current_price, user_id, symbol["symbol"]))

    # Load user portfolio.
    return render_template("portfolio.html", transactions=portfolio, cash=session.get("cash"))


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():

    # Lookup the user's searched stock.
    if request.method == "POST":

        # Load the user's id from a session.
        user_id = session.get("user_id")

        # Store the symbol the user searched.
        symbol = (request.form.get("symbol")).upper()

        # Store user's inputted number of shares.
        shares_to_buy = request.form.get("shares")

        # User had incomplete inputs.
        if not symbol or not shares_to_buy:
            return apology("Lacks input/s")

        # The user inputted a non-numeric character.
        if shares_to_buy.isnumeric == False or shares_to_buy.isdigit() == False or int(shares_to_buy) <= 0:
            return apology("Input a positive integer")

        # Lookup the stock the user searched.
        stock_info = lookup(symbol)

        # User searched an invalid stock.
        if stock_info == None:
            return apology(f"No match found for '{symbol}'")

        # Get the user's total purchase price.
        total_purchase_price = float(shares_to_buy) * stock_info["price"]

        # The user can't afford the purchase.
        if total_purchase_price > session.get("cash"):
            return apology("You don't have enough cash")

        # Set activity to "BUY".
        activity = "BUY"

        # Get user's current shares of the stock.
        current_shares = 0 if len(db.execute(
            "SELECT shares FROM user_? WHERE symbol = ?", user_id, symbol)) == 0 else db.execute(
            "SELECT shares FROM user_? WHERE symbol = ?", user_id, symbol)[0]["shares"]

        # Add the user's current shares to the shares to be bought.
        shares = current_shares + int(shares_to_buy)

        # Update user's cash.
        post_purchase_balance = session.get("cash") - total_purchase_price
        session["cash"] = post_purchase_balance
        db.execute(
            "UPDATE users SET cash = ? WHERE id = ?", post_purchase_balance, user_id)

        # Get the time of transaction.
        time = str(db.execute(
            "SELECT datetime('now')")[0]["datetime('now')"]) + " (UTC)"

        # Save all transaction data to a list.
        transaction = [user_id, stock_info["name"], stock_info["symbol"],
                       shares, stock_info["price"], total_purchase_price, activity, time]

        # Update user's portfolio.
        db.execute(
            "REPLACE INTO user_{} (company, symbol, shares, price, total) VALUES('{}', '{}', {}, {}, {})".format(
                *transaction[:-2]))

        # Set "shares" to purchase' current shares only (not the user's total shares after the purchase).
        transaction[3] = shares_to_buy

        # Update the global transaction database.
        db.execute("INSERT INTO transactions (user_id, company, symbol, shares, price, total, activity, time) VALUES ({}, '{}', '{}', {}, {}, {}, '{}', '{}')".format(
            *transaction))

        return render_template("purchase_summary.html", stock=stock_info, shares=shares_to_buy, total=total_purchase_price, cash=session.get("cash"))

    # Render search form to user.
    else:
        return render_template("buy.html", cash=session.get("cash"))


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    transactions = db.execute("SELECT * FROM transactions WHERE user_id = ? ORDER BY id DESC", session.get("user_id"))

    return render_template("history.html", transactions=transactions, cash=session.get("cash"))


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

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
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    if request.method == "POST":

        # Store user's entry into a variable.
        symbol = request.form.get("symbol")

        # Look for the stock information the user searched.
        stock_info = (lookup(symbol))

        # Stock that the use is searching does not exist in database.
        if stock_info == None:
            message = 'Your search "' + symbol + '" did not match any stock in our database.'
            return apology(message)

        # Display the search result to the user.
        return render_template("quoted.html", company=stock_info, cash=session.get("cash"))

    else:
        # Display to user the form to search the stock.
        return render_template("quote.html", cash=session.get("cash"))


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "POST":

        # Add the user's entry into the userts table in the database.
        username = request.form.get("username")
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
        hash = werkzeug.security.generate_password_hash(password, method='pbkdf2:sha256', salt_length=8)

        # Remember registrants inputs.
        db.execute("INSERT INTO users (username, hash) VALUES (?, ?)", username, hash)

        # Get user id.
        user_id = db.execute("SELECT id FROM users WHERE username = ?", username)[0]["id"]

        session["user_id"] = user_id

        # Give user a database of transaction.
        db.execute("CREATE TABLE user_? (id INTEGER PRIMARY KEY, company TEXT NOT NULL, symbol TEXT NOT NULL, shares REAL, price REAL, total REAL)", user_id)

        # Ensure company name is unique
        db.execute("CREATE UNIQUE INDEX idx_user_?_company ON user_? (company)", user_id, user_id)

        # Redirect to a route that shows user's profile porfolio.
        return redirect("/login")

    else:

        # Display to user the place to register.
        return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():

    # Load the user's id from a session.
    user_id = session.get("user_id")

    # Load the symbols of the user-owned companies.
    portfolio = db.execute("SELECT symbol FROM user_?", user_id)

    if request.method == "POST":

        # Store the symbol the user searched.
        symbol = request.form.get("symbol")

        # User did not select a stock.
        if not symbol:
            return apology("No stock selected")

        # Store user's inputted number of shares.
        shares_to_sell = request.form.get("shares")

        # User had incomplete inputs.
        if not shares_to_sell:
            return apology("Input number of share/s")

        # The user did not input a positive integer.
        if shares_to_sell.isnumeric == False or shares_to_sell.isdigit() == False or int(shares_to_sell) <= 0:
            return apology("Input a positive integer")

        # Get information about the stock to sell by the user.
        stock_to_sell = db.execute("SELECT * FROM user_? WHERE symbol = ?", user_id, symbol)[0]

        # User don't have enough shares.
        if int(shares_to_sell) > stock_to_sell["shares"]:
            return apology("You don't have enough shares")

        # Get total shares after purchase.
        shares = stock_to_sell["shares"] - int(shares_to_sell)

        # Get the total price of sale.
        total_sale_price = int(shares_to_sell) * stock_to_sell["price"]

        # Get user's post-sale-balance.
        session["cash"] = session.get("cash") + total_sale_price

        # Set activity to "SELL".
        activity = "SELL"

        # Update user's cash.
        db.execute(
            "UPDATE users SET cash = ? WHERE id = ?", session.get("cash"), user_id)

        # Get the time of transaction.
        time = str(db.execute(
            "SELECT datetime('now')")[0]["datetime('now')"]) + " (UTC)"

        # Save all transaction data to a list.
        transaction = [user_id, stock_to_sell["company"], stock_to_sell["symbol"],
                       stock_to_sell["price"], stock_to_sell["price"], total_sale_price, activity, time]

        # Update user's portfolio.
        db.execute("UPDATE user_? SET shares = ? WHERE symbol = ?", user_id, shares, symbol)

        # Set "shares" to shares of current shares only (not the user's total shares after the purchase).
        transaction[3] = shares_to_sell

        # Update transaction database.
        db.execute("INSERT INTO transactions (user_id, company, symbol, shares, price, total, activity, time) VALUES ({}, '{}', '{}', {}, {}, {}, '{}', '{}')".format(
            *transaction))

        # Delete rows having shares = zero.
        db.execute("DELETE FROM user_? WHERE shares = 0", user_id)

        return render_template("sale_summary.html", stock=stock_to_sell, shares=shares_to_sell, total=total_sale_price, cash=session.get("cash"))

    # Render search form to user.
    else:
        return render_template("sell.html", portfolios=portfolio, cash=session.get("cash"))


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