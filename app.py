import flask
from flask_sqlalchemy import SQLAlchemy
from flask import render_template, request, redirect, url_for, make_response, session, send_from_directory, url_for
from flask_uploads import UploadSet, IMAGES, configure_uploads
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy import func,select
from wtforms import SubmitField
from datetime import datetime, timedelta
import re
import bcrypt
from User_Accounts import profile
import os

app = flask.Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///local.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

app.secret_key = "SessionTestKey123"
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(minutes=15)

app.config['UPLOADED_PHOTOS_DEST'] = 'uploads'

photos = UploadSet('photos', IMAGES)
configure_uploads(app, photos)

developMode = False
minPasswordLength = 6
howManyTriesInXTime = 3
XTime = 60

class UploadForm(FlaskForm):
    photo = FileField(
        validators=[
            FileAllowed(photos, 'Nur Bilder sind erlaubt')
        ]
    )
    submit = SubmitField('Hochladen')
    

likes_table = db.Table(
    'likes',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('post_id', db.Integer, db.ForeignKey('post.id'), primary_key=True)  # Kleinbuchstaben!
)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email_address = db.Column(db.String(255), unique=True, nullable=False)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow())
    lastFirstTry = db.Column(db.DateTime, default=datetime.utcnow())
    triesInXTime = db.Column(db.Integer, default=0)
    lastLoginTry = db.Column(db.Integer, default=0)
    profilePicture = db.Column(db.String(1000))
    liked_posts = db.relationship('Post', secondary=likes_table, back_populates='likers')
    totalPosts = db.Column(db.Integer, default=0)

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.String(5000), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    likers = db.relationship('User', secondary=likes_table, back_populates='liked_posts')

with app.app_context():
    db.create_all()

@app.after_request
def add_header(response):
    response.headers["Cache-Control"] = "no-store"
    return response

@app.route('/', methods=['GET', 'POST'])
def main():
    if request.method == 'POST':
        if request.form.get("GoToLogin") == "clicked":
            return redirect(url_for("login"))
        
        if request.form.get("GoTosignup") == "clicked":
            return redirect(url_for("signup"))
        

    return render_template("index.html")

@app.route('/signup', methods=['GET', 'POST'])
def signup():

    errors = session.pop("errors", {})

    if request.method == "POST":

        error = False

        if request.form.get("GoToLogin") == "clicked":
            return redirect(url_for("login"))

        tried_email_address = request.form['email_address']
        tried_username = request.form['username']
        tried_password = request.form['password']

        notAnEmail = ""
        notAnUsername = ""
        notAPassword = ""

        if len(tried_password) < minPasswordLength:
            error = True
            notAPassword = "notAPassword"

        isAnEmailAddress = CheckIfEmailisAnEmail(tried_email_address)

        if not isAnEmailAddress:
            error = True
            notAnEmail = "notAnEmail"

        existing_email = db.session.query(User).filter_by(
            email_address=tried_email_address
        ).first()

        existing_username = db.session.query(User).filter_by(
            username=tried_username
        ).first()

        if existing_username or tried_username == "" or tried_username == None:
            error = True
            notAnUsername = "notAnUsername"

        if existing_email:
            error = True
            notAnEmail = "notAnEmail"

        # Wenn Fehler → speichern + redirect
        if error:
            session["errors"] = {
                "email": notAnEmail,
                "username": notAnUsername,
                "password": notAPassword
            }
            return redirect(url_for("signup"))

        # Wenn alles gut → User erstellen
        new_user = User(
            email_address=tried_email_address,
            username=tried_username,
            password=bcrypt.hashpw(
                tried_password.encode("utf-8"),
                bcrypt.gensalt()
            )
        )

        db.session.add(new_user)
        db.session.commit()

        return redirect(url_for("login"))

    return render_template(
        "Signup_Page.html",
        notAnEmail=errors.get("email", ""),
        notAnUsername=errors.get("username", ""),
        notAPassword=errors.get("password", "")
    )

def CheckIfEmailisAnEmail(tried_email_adress):
    print("Tried to check email")
    listOfTriedEmailElements = []
    if "@" and "." in tried_email_adress:
        #listOfTriedEmailElements = re.split(r'[@.]', tried_email_adress)
        listOfTriedEmailElements.append(tried_email_adress.split("@")[0])
        #secondPart = tried_email_adress.split("@")[1].split(".")[:-1]
        #secondPartString = "".join(secondPart)
        listOfTriedEmailElements.append(tried_email_adress.split("@")[1].rsplit(".", 1))
        listOfTriedEmailElements.append(tried_email_adress.split("@")[1].split(".")[-1])
        
        print(listOfTriedEmailElements)
        if len(listOfTriedEmailElements) == 3:
            return True
        else:
            return False

@app.route('/login', methods=['GET', 'POST'])
def login():
    tooManyTries = False
    emailOrUsername = ""
    timeUnit = "s"
    blockedTimeLeft =""
    if request.method == 'POST':

        if request.form.get("GoTosignup") == "clicked":
            return redirect(url_for("signup"))

        # Request password and email input
        emailOrUsername = request.form['email_address']
        password = request.form['password'].encode("utf-8")
        user = None

        user = User.query.filter_by(email_address=emailOrUsername).first()

        if user is None:
            user = User.query.filter_by(username=emailOrUsername).first()

        user.lastLoginTry = datetime.utcnow()

        blockedTimeLeft = XTime - (datetime.utcnow() - user.lastFirstTry).total_seconds()
        blockedTimeLeft = round(blockedTimeLeft)

        if blockedTimeLeft / 60 >= 1:
            blockedTimeLeft = round(blockedTimeLeft / 60)
            timeUnit = "m"

        #check if it's the first try in a given time
        if (datetime.utcnow() - user.lastFirstTry).total_seconds() >= XTime: #check if time difference is greater or equal to max time
            user.lastFirstTry = datetime.utcnow()
            user.triesInXTime = 0

        #Check if max tries in XTIme is reached and if so give no access
        if (datetime.utcnow() - user.lastFirstTry).total_seconds() < XTime and user.triesInXTime >= howManyTriesInXTime:
            tooManyTries = True
            return render_template("Login_Page.html", tooManyTries=True, email=emailOrUsername, blockedTimeLeft=blockedTimeLeft, timeUnit=timeUnit), 429
        
        db.session.commit()


        if user and bcrypt.checkpw(password, user.password):
            print("Correct Password")
            user.triesInXTime = 0
            session["user_id"] = user.id
            session.permanent = True
            session["user_id"] = user.id

            return redirect(url_for("feed", username=user.username))
        else:
            user.triesInXTime += 1
            db.session.commit()
            print("Incorrect Password")
    return render_template('Login_Page.html', tooManyTries=tooManyTries, email=emailOrUsername, blockedTimeLeft=blockedTimeLeft, timeUnit=timeUnit)

@app.route('/user/<username>/settings', methods=['GET', 'POST'])
def dashboard(username):
    changeProfilePic = "hidden"

    #check if session is on
    user_id = session.get("user_id")

    if not user_id:
        return redirect("/login")

    session_user = User.query.get(user_id)

    if session_user is None:
        return redirect("/login")
    
    if session_user.username != username:
        return redirect(url_for("dashboard", username=session_user.username))

    user = session_user

    form, file_url = ChangeProfilePic(username)

    if session.get("show_profile_pic_form"):
        changeProfilePic = "shown"
        session.pop("show_profile_pic_form", None)
    
    profilePicture = user.profilePicture

    if request.method == "POST":
        action = request.form.get("action")
        if action == "change_password":
            ChangePassword(user.id)
        elif action == "open_settings":
           return redirect(url_for("AccountSettings", username=user.username))
        elif action == "change_profilePic":
            session["show_profile_pic_form"] = True

        DeleteAccount(request.form.get("delete"))

        db.session.commit()
        return redirect(url_for("dashboard", username=username))

    print("User:", user,
          "\nUsername: ", user.username,
          "\nID: ", user.id)
    
    users = User.query.all()
    
    if(username == "admin"):
        return render_template(
            'dashboard.html', 
            username = user.username, 
            created_at = user.created_at, users=users, 
            profilePicture=profilePicture,
            changeProfilePic=changeProfilePic,
            form=form)
    else:
        return render_template(
            'dashboard.html', 
            username = user.username, 
            created_at = user.created_at,
            users=users,
            profilePicture=profilePicture,
            changeProfilePic=changeProfilePic,
            file_url=file_url,
            form=form)

def ChangePassword(user_id):
    print("tried to change password")
    user = User.query.get(user_id)
    newPassword = request.form['change_password']

    if newPassword != "":
        print("ACTUALLY SET NEW PASSWORD: ", newPassword)
        user.password = bcrypt.hashpw(newPassword.encode("utf-8"), bcrypt.gensalt())

        db.session.commit()

def DeleteAccount(idToDelete):
    accountToDeleteId = idToDelete
    userToDelete = User.query.get(accountToDeleteId)

    if userToDelete != None:
        db.session.delete(userToDelete)
        db.session.commit()

@app.route("/uploads/<filename>")
def getFile(filename):
    return send_from_directory(app.config['UPLOADED_PHOTOS_DEST'], filename)

"""@app.route("/user/<username>/settings", methods=['GET', 'POST'])"""
def ChangeProfilePic(username):
    #Get the logged in username
    user = User.query.filter_by(username=username).first()

    #check if session is on
    user_id = session.get("user_id")
    print("User_id: ", session.get("user_id"))

    if not user_id:
        return redirect("/login")
    
    form = UploadForm()
    file_url = user.profilePicture

    if form.validate_on_submit():
        file_url = saveImage(form.photo.data)
        user.profilePicture = file_url
        db.session.commit()
        #return redirect(url_for("AccountSettings", username=username))

    return form, file_url

def saveImage(photo):
    filename = photos.save(photo)
    return url_for('getFile', filename=filename)

@app.route('/user/<username>/feed', methods=['GET', 'POST'])
def feed(username):
    #check if session is on
    user_id = session.get("user_id")

    if not user_id:
        return redirect("/login")

    session_user = User.query.get(user_id)

    if session_user is None:
        return redirect("/login")
    
    if session_user.username != username:
        return redirect(url_for("feed", username=session_user.username))

    posts = Post.query.all()
    posts.reverse()

    users = []
    for i in range(len(posts)):
        users.append(User.query.get(posts[i].user_id))

    post_id = request.form.get("post_id")

    user = User.query.get(user_id)
    post = Post.query.get(post_id)

    if request.method == "POST":
        action = request.form.get("action")
        print(action)
        post_index = request.form.get("post_id")
        if action == "open_settings":
           return redirect(url_for("dashboard", username=session_user.username))
        elif action == ("give_like") and post_index:
            print("Gave a like!")
            if user not in post.likers:
                post.likers.append(user)
                db.session.commit()
                return redirect(url_for("feed", username=session_user.username) + f"#post-{post.id}")
        elif action.startswith("post.id = "):
            post_id = action.split("=")[1]
            post_user_id = Post.query.get(post_id).user_id
            post_username = User.query.get(post_user_id).username 
            return redirect(url_for('profileManager', username=post_username, post_id=post_id))
        elif action.startswith("OpenPost.id = "):
            post_id = action.split("=")[1]
            return redirect(url_for('ViewPost', post_id=post_id))


    return render_template('feed.html', posts=posts, users=users, session_user=session_user)

@app.route('/user/<username>/post', methods=['GET', 'POST'])
def post(username):
    #check if session is on
    user_id = session.get("user_id")

    if not user_id:
        return redirect("/login")

    session_user = User.query.get(user_id)

    if session_user is None:
        return redirect("/login")
    
    if session_user.username != username:
        return redirect(url_for("post", username=session_user.username))

    user = session_user

    if request.method == 'POST':
        titleOfPost = request.form['title']
        contentOfPost = request.form['content']

        new_post = Post(
            title=titleOfPost,
            content=contentOfPost,
            user_id=session.get("user_id")
        )
        
        db.session.add(new_post)
        user.totalPosts += 1
        db.session.commit()
        return redirect(url_for("feed", username=username))

    return render_template('post.html')

@app.route('/user/<username>/<post_id>', methods=['GET', 'POST'])
def profileManager(username, post_id):

    user = User.query.filter_by(username=username).first()
    user_posts = Post.query.filter_by(user_id=user.id).with_entities(Post.id).all()
    post_ids = [p.id for p in user_posts]

    totalPosts = user.totalPosts
    
    if post_ids:  # falls der user überhaupt posts hat
        stmt = select(func.count()).select_from(likes_table).where(likes_table.c.post_id.in_(post_ids))
        totalLikes = db.session.execute(stmt).scalar()
    else:
        totalLikes = 0

    return render_template('profileView.html', totalPosts=totalPosts, username=username, post_id=post_id, totalLikes = totalLikes, user=user)

@app.route('/<post_id>')
def ViewPost(post_id):
    post = Post.query.get(post_id)
    user = User.query.filter_by(id=post.user_id).first()

    return render_template('ViewPostSingle.html', post_id=post_id, user=user, post=post)


if __name__ == "__main__":
    if developMode == True:
        app.run(debug=True)
    else:
        app.run(host="0.0.0.0", port=5000, debug=True)