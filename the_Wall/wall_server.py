from flask import Flask, render_template, redirect, request, session, flash
import re
from flask.ext.bcrypt import Bcrypt
from mysqlconnection import MySQLConnector

app = Flask(__name__)
bcrypt = Bcrypt(app)
app.secret_key = 'KeepThisSecret'
mysql = MySQLConnector(app,'walldb')

EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9\.\+_-]+@[a-zA-Z0-9\._-]+\.[a-zA-Z]*$')
PASS_REGEX = re.compile(r'(.*([A-Z]+).*([0-9]+).*)|(.*([0-9]+).*([A-Z]+).*)')

@app.route('/')
def index():
    #render the page
    return render_template('index.html')

# validate your registration here
@app.route('/registration', methods=['POST'])
def registration_validation():
	print 'entered registration'
	allOK = True
	#extract all the data and save into session dictionary
	temp_email = request.form['email']
    #check for duplicate emails
	email_existence_query = "SELECT * FROM users WHERE email = :email"
	print '1'
	email_entry = {'email': temp_email}
	user_in_db = mysql.query_db(email_existence_query, email_entry)
	print '2'
	temp_fname = request.form['first_name']
	temp_lname = request.form['last_name']
	temp_pass = request.form['password']
	temp_pass2 = request.form['confirm_password']
	#check email and flash accordingly
	if len(temp_email) < 1:
		flash("Email cannot be blank!")
		allOK = False
	if not EMAIL_REGEX.match(temp_email):
		flash("Invalid Email Address!")
		allOK = False
	if not user_in_db == []:
		flash("User email already in system! No duplicates!")
		allOK = False

	#check first name and flash accordingly
	if len(temp_fname) < 1:
		flash("First Name cannot be blank!")
		allOK = False
	if not temp_fname.isalpha():
		flash("Invalid First Name! Cannot contain numbers")
		allOK = False

	#check last name and flash accordingly
	if len(temp_lname) < 1:
		flash("Last Name cannot be blank!")
		allOK = False
	if not temp_lname.isalpha():
		flash("Invalid Last Name! Cannot contain numbers")
		allOK = False

	#check passwords and flash accordingly
	if len(temp_pass) < 1:
		flash("Password cannot be blank!")
		allOK = False
	if len(temp_pass) < 8:
		flash("Password should be more than 8 characters!")
		allOK = False
	if not PASS_REGEX.match(temp_pass):
		flash("Invalid Password! Must have 1 uppercase letter and 1 numeric value")
		allOK = False
	if temp_pass != temp_pass2:
		flash("Password and confirmation must match")
		allOK = False

	#if all pass, hash password, then insert data into database
	if allOK:
		hash_pw = bcrypt.generate_password_hash(temp_pass)
		query = "INSERT INTO users (first_name, last_name, email, password, created_at, updated_at) VALUES (:fname, :lname, :email, :hpass, NOW(), NOW())"
		data = {'fname': temp_fname,
		'lname': temp_lname,
		'hpass': hash_pw,
		'email': temp_email
		}
		mysql.query_db(query, data)
		flash('User registered successfully')
	return redirect('/')

@app.route('/validate', methods=['POST'])
def validate():
    print 'entered validation route'
    email = request.form['email']
    password = request.form['password']
    print email
    print password
    if (email > 0) and (password > 0):
        query = "SELECT * FROM users WHERE email = :email LIMIT 1"
        data = {'email': email}
        user = mysql.query_db(query, data)
        print user
        if not user:
            flash('no such user')
            return redirect('/')
        if bcrypt.check_password_hash(user[0]['password'], password):
            session['id'] = user[0]['id']
            return redirect('/wall')
        else:
            return redirect('/')
    else:
        flash('not valid email password combo')
        return redirect('/')

# Render wall.html
# Need to pass in name of user matching session['id']
# Needs to pull message data, as well as comment data before rendering.
@app.route('/wall')
def wallRender():
    #this is the user data
    login_query = "SELECT * FROM users WHERE id = :user_id"
    login_data = {
            'user_id': session['id']
    }
    one_user = mysql.query_db(login_query, login_data)
    if one_user == []:
    	flash('No user found with email entry')
    	return redirect('/')

    #pull all the messages to display, and save in messages
    # message = [ {messageID:, userID:, first_name:, last_name:, messages.created_at:, message:} ]
    messages_query = "SELECT messages.id as messageID, users.id as userID, first_name, last_name, messages.created_at, message FROM users JOIN messages ON users_id = users.id"
    messages = mysql.query_db(messages_query)
    #pull all comments that are associated with a message.
    # comments => [{messages_id:, first_name:, last_name:, comment:, created_at}, {messages_id:, first_name:, last_name:, comment:, created_at}....]
    comments_query = "SELECT comments.messages_id, commentOwner.first_name, commentOwner.last_name, comments.comment, comments.created_at FROM comments LEFT JOIN users AS commentOwner ON (comments.users_id = commentOwner.id) ORDER BY messages_id ASC"
    comments = mysql.query_db(comments_query)
    # all3Tables_query = "SELECT * FROM messages LEFT JOIN (users AS messageOwner) ON (messages.users_id = messageOwner.id) LEFT JOIN (SELECT * FROM comments LEFT JOIN (users AS commentOwner) ON (comments.users_id = commentOwner.id)) AS t ON (messages.id = t.messages_id)"
    # all3Tables = mysql.query_db(all3Tables_query)

    return render_template('wall.html', user=one_user[0], all_usermessages=messages, all_usercomments=comments)

# Write message into the database, with the correct user_id. Correct user_id is in session.
# Should return to wall rendering. Redirect /wall
@app.route('/wall/post_message', methods = ['POST'])
def postMessage():
	print 'posting message now'
	query = "INSERT INTO messages (message, created_at, updated_at, users_id) VALUES (:message, NOW(), NOW(), :user_id)"
	data = {'message': request.form['message'], 'user_id': session['id']}
	mysql.query_db(query, data)
	return redirect ('/wall')

# Write message into the database, with the correct user_id. Correct user_id is in session.
# Should return to wall rendering. Redirect /wall
@app.route('/wall/<message_id>/post_comment', methods =['POST'])
def postComment(message_id):
	print 'posting comment now'
	print message_id
	query = "INSERT INTO comments (comment, created_at, updated_at, users_id, messages_id) VALUES (:comment, NOW(), NOW(), :user_id, :messages_id)"
	data = {'comment': request.form['comment'], 'user_id': session['id'], 'messages_id': message_id}
	mysql.query_db(query, data)
	return redirect ('/wall')

app.run(debug=True)
