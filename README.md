# Jaizzer<sup>2</sup>

The project is a web application where the user can track his/her finances. This app has tha ability to keep track of the money in the accounts that the user will create. There are also added functionality such as editing and synching elements and keeping track where the user lended or borrowed moneey.


## Technologies Used

1. Flask

This project was accomplished through the use of different technologies. The framework I used is Flask.

2. Python
	
This language was the one that handles almost all actions (except the client side scripts). It handled all the logic and rendering of templates and routings. Moreover, it also automated the database handling by integrating it with Sqlite3.

3. Sqlite3
	
This is crucial for executing functions throughout all the databases via different routes depending on the action the user wants to use.

4. HTML, CSS, JavaScript, Bootstrap Templates
	
All of these are responsible for bringing the front-end side to life. I’ve created some of my own styling and scripting, but also utilized some already existing implementations in Bootstrap.


## How it Works

### Registration

The idea is simple. The user just need to register to an account and choose a username that is not already taken, and a strong password. What I meant about a strong password is a password that is at least 10-character long where it contains at least one of the  following: uppercase-letter, lower-case letter, special character, and number. And of course, the password should match with the “confirm password” field. All of these are required input fields. Hence, the user can’t proceed if one input field lacks input. 

In the backend, all of these are handled through the **“/register”** route which calls a function “check_password_strength( )”. After succesful registration, underneath the hood, **“/register”** route saves user’s chose username to a global database alongside the hashed version of the password. This is hashing is accomplished through the function “hash( )”. Afterwards, the **“/register”** route will also grant the user a database that will serve as his/her storage for everything in his accounts such as transaction history, balance, lend/debt list, and many more.


### Logging In
	
After the user accomplished the registration, he/she can now login to the website. The sure, will now be prompted to enter theire registered username and password. In the event the user’s input does not match the ones in the database, an error page saying “Incorrect Inputs” will be displayed to the user. Otherwise, if the user has succesfully logged in, his/her last saved session will be retrieved back from the database to render all data inside his/her account. Log in function is handled through the **“/login”** route which prevents the website from showing any data to the user unless a session is retrieved, meaning loggin in was a success. 


### Navbar and Topbar

If the user has succesfully logged-in, he/she will now be redirected to the home page and can then proceeding checking out other pages. However, despite the web app has several different web pages showing different content, they all have a navbar, and a topbar functionality. The navbar and topbar where all implemented in a HTML layout file called named “layout.html”. The navbar contains all the pages where the user can visti. This includes the Dashboard itself, Lists (debt/lend), Edit, History, and Log Out. The topbar on the otherhand shows what is the username that is currently logged in, which in the case of the user, is his/her chosen username when he/she registered the account.


### Home Page

The home page or also known as dashboard page displays to user all his accounts and the balance inside. This is implemented to a horizontally scrollable group of boxes. When I was doing this, I also tried to implement the feature through a table because it appears more organized to visualize. However, I realized that things will get ugly if the user add a lot of accounts making the page overwhelming and distracting. Hence I opt to just using user friendly and clean looking scrollable boxes. In default, every user are already given premade accounts named: Account 1, Account 2, Account 3, Savings 1, and Savings 2.
	
Moreover, below those “account boxes”, we can also see an input form. All of these are required fields hence can not proceed to the next route if incomplete. The first field ask for the description or anything about the transaction. The second one asks for the amount of money involved and what account the user will used. Moreover, it will also ask for the category, whether the transaction “adds money” (Income or Debt), “gets money” (Expense, Lend) or “transfers money” (transfer). All of these will be cheked and handles by the **“/”** route. It will check if the selected account has enough money if the transaction “gets money”. Moreover it will check to what route or webpage the user will be redirected (to be explained more later). If the user does not have enough money, then, an error message stating “insufficient balance” will be showed to the user.

In addition, the description that the user will type will be saved in a database containing all of his/her inputted description, hence, can just be reused next time. And because this descriptions are being saved, these are also subject to editing through teh “Edit” page if the user whishes to (to be explaned more later). 
	
Before proceeding to the transaction, a confirmation will be asked to the user first. If the user confirms, the transaction now commences. If it is just a regular “Income/Expense” category, it will be handled by the **“/regular”** route. Meanwhile if the transaction is a transfer, it will be handled by the **“/transfer”** route.  Else, if the transaction is either Debt or Lend, it will handled by the **“/lend_or_borrow”** route. After the processing of transaction is completed, the user is then redirected to the History page which shows all existing transaction history, with the newest transaction appended on the top. This is handled by the **“/history”** route.


### Lend/Debt Form Page

If the user chose the Lend or Debt as category, he/she will be redirected to this another page. This contains another form which will ask the user to select an existing person or create a new one to lend or borrow money. After confirming, if the chosen or created name matches a name from the opposite list (e.g if the list is debt, then lend is the opposite list), it will ask the user whether he or she would like to synch them so that all future transaction can now be handled in that one person. Else, if no match is found, there will be no “synch confirmation” prompt. In both cases, after processing, the user will be redirected to the transaction history page.	


### Lend/Debt List Page

This is page is a lot different than the “Lend/Debt Form Page”. This page shows all the people where the user lended or borrowed money. It uses the route **“/lend”** or **“/debt”**. The list are presented in a form of “borderless” table which shows the name of the person, the amount borrowed/lended, and a button that could be “Pay” for Debt or “Collect” for Lend. Moreover, if a name from the current list matches a name from the opposite list (e.g if the list is debt, then lend is the opposite list), then a button saying “synch” will appear”, signifying a synching opportunity if the user wishes to synch the person (synching will be further explained below). Else if the person was already synched, then a Botton saying “unsynch will appear”. If the user pressed the button “Pay” or “Collect”, they will be redirected to a page containing a form. The first input field asks how much money to collect/pay, and the second input field will asks where to add/get the money. This form is implemented through the route **“/pay_or_collect”**. After submitting the form, the user will then be redirected to another page which just basically show the summary of transaction (**“/confirmation”**) before processing. Finally, just like other type of transaction, the user will be redirected to the Transaction History Page.


### Synching/Unsynching Functionality
	
Why make this feature? Well, this question can best be answered through an example. Let say Bob borrowed 50 dollars from Alice, this 50 dollars will be added to Bob’s account. Bob will then save Alice to his debt list and the transaction is done. However, one day Alice also borrowed 50 dollars from Bob, for us humans, it is already understood that in this moment, Bob is also just basically paying his 50 dollar debt from Alice. However, the app, sadly, is not that smart enough. Hence, Bob will have a name “Alice” with the 50 dollar he borrowed in the debt list, and an “Alice” with the 50 dollar he lended in the lend list. You might suggest that why not just collect the 50 dollar lended money from the “Alice” in the lend list and use it to pay the “Alice” in the debt list. Well, that could work, but what if you are transacting with different and lots of people everyday. It will be a hassle in the long run. 

This is a problem the that synch functionality is trying to solve. If Bob for instance, just synched the Alice from the Debt list and the Alice from the Lend list, the app will already do the calculations for him. Which in this case cancels both the 50 dollars. The app will subtract the 50 dollar lend from Alice 1 (Lend list) to the 50 dollar debt from Alice 2 (50 - 50 = 0). This feature will present itself to the user whenever it sees a matching name from debt and lend list. Hence, if user just happen to have transacted to two different persons but with different name, then he/she must come up of some ways to prevent this either by putting surnames or numbers to differentiate the two people. Moreover, if the user wish to unsynch the person, he/she can just press the button either in the Debt or Lend list page. Intuitively the synch function is handled via **“/synch”** route while the unsynch function is handled via **“/unsynch**” route.


### Transfer Page
	
Transfer page is somewhat a combination of Income and Expense category. It takes a money from  Account A (just like expense) but adds it to Account B (just like income). If the user chose “Transfer” category in the “Add Transaction” form in the homepage, he/she will further be redirected to a page with input fields. It will ask the user where to transfer the amount. Afterwards, the user will then be redirected to the Transaction history (**“/history”**). Moreover, transfer is implemented, you guessed it, via **“/transfer”** route.


### Edit Accounts

The edit page is the page where the user would want to go if he/she would want to make some modifications, either on his/her lists of Accounts, Descriptions, Debts, and Lends. If the user go to the “accounts” part of Edit page, he/she will be redirected to a page rendering all existing account names alongside the buttons: “Modify” (in green) or “Delete” (in red). If the user pressed the Modify he/she will be redirected to a page containing input fields. The first one asks for the account’s new name if the user wish to rename the account. The second one asks for the account’s new balance if the user wish to change the balance inside the account. This form is implemented via **“/modify_account”** route. Meanwhile, if the user pressed “Delete” the route **“/edit_account”** will be used. Moreover, the Edit Accounts page also containts an input field for creating new Accounts. It contains an input field for the account name and another one for the initial balance. If no balance was put, the app, in default, will initialize it to zero.


### Edit Description

The edit page is the page where the user would want to go if he/she would want to make some modifications, either on his/her lists of Accounts, Descriptions, Debts, and Lends. If the user go to the “descriptions” part of Edit page, he/she will be redirected to a page rendering all existing description names alongside the buttons: “Modify” (in green) or “Delete” (in red). If the user pressed the Modify he/she will be redirected to a page containing input fields. It asks for the description’s new name if the user wish to rename the description.This form page is implemented via **“/modify_description”** route. Meanwhile, if the user pressed “Delete” the route **“/edit_description”** will be used. Moreover, the Edit Description page also contains an input field for creating new descriptions. It contains an input field for the description name. However, creating page can also be done on the Home page in the “Add Transaction” form directly.


### Edit Debt

The edit page is the page where the user would want to go if he/she would want to make some modifications, either on his/her lists of Accounts, Descriptions, Debts, and Lends. If the user go to the “Debts” part of Edit page, he/she will be redirected to a page rendering all existing debt list containing names alongside the buttons: “Modify” (in green) or “Delete” (in red). If the user pressed the Modify he/she will be redirected to a page containing input fields. It asks for the description’s new name if the user wish to rename the description.This form page is implemented via **“/modify_debt”** route. Meanwhile, if the user pressed “Delete” the route **“/edit_debt”** will be used.


### Edit Lend

The edit page is the page where the user would want to go if he/she would want to make some modifications, either on his/her lists of Accounts, Descriptions, Debts, and Lends. If the user go to the “Lends” part of Edit page, he/she will be redirected to a page rendering all existing lend list containing names alongside the buttons: “Modify” (in green) or “Delete” (in red). If the user pressed the Modify he/she will be redirected to a page containing input fields. It asks for the description’s new name if the user wish to rename the description.This form page is implemented via **“/modify_lend”** route. Meanwhile, if the user pressed “Delete” the route **“/edit_lend”** will be used.


### Transaction History
	
This page is the one responsible for storing all the user’s transaction. It is implemented via the **“/history”** route. This route pulls all the transaction history from the database and renders it in HTML through a table. This table, allows for sorting the transaction. If the user clicked the column title: “Date”, the transactions will be sorted by Date ascendingly, and descendingly if the user clicked it again. The same goes with the “Amount” column, but it sorts all the transaction through the amount of money involved. The other columns on the other hand will just sort the transaction alphabetically base on that column. There is also a search bar so that user can easily find a certain transaction. This features are implemented via Javascript.


### Error Page

This page acts as the error handling page. It is called whenever the user does not meet some conditions the web application requires. This is implemented via a function “apology( )” which is in a file named “helpers.py”. This function creates a “404” page alongside a message which details what went wrong.


## Others

### Sessions

This project utilized a lot of sessions. This was used to transfer information via different routes especially for remembering informations that are frequently used such as the user’s username.


### Possible improvements

As all applications this one can also be improved. Possible improvements:

- Addition of visualization tools like charts and graphs. 
- Addition of budgeting database that auto gets/puts money at a certain schedule 
- Addition of real bank account handling 
- Addition of Forgot password Feature 


### How to launch application

1. Clone the code:  `git clone https://github.com/Jaizzer/PerFi.git`
2. Save it to desired location.
3. Unzip File.
4. Access directory via Terminal containing “app.py”. 
5. Run “flask run” 
6. Clink the link that will appear on the terminal that looks like these: “http://127.0.0.1:5000".
7. You are ready to go!
