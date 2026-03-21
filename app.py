import flask
from flask_sqlalchemy import SQLAlchemy
from flask import render_template, request, redirect, url_for, make_response, session, send_from_directory, url_for, jsonify
from flask_uploads import UploadSet, IMAGES, configure_uploads
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy import func,select,JSON, desc
from sqlalchemy.ext.mutable import MutableList
from wtforms import SubmitField
from datetime import datetime, timedelta
import re
import bcrypt
from User_Accounts import profile
from agentTrain import CategorizePost
from itsdangerous import Signer
import resend
import uuid
import secrets
import os
from dotenv import load_dotenv
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

load_dotenv()

resend.api_key = os.environ.get("RESEND_API_KEY")

app = flask.Flask(__name__)

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=[]
)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

app.secret_key = os.environ.get("SECRET_KEY")
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(minutes=15)
app.config["SESSION_COOKIE_SECURE"] = True    # nur HTTPS
app.config["SESSION_COOKIE_HTTPONLY"] = True  # kein JS-Zugriff
app.config["SESSION_COOKIE_SAMESITE"] = "Lax" # CSRF-Schutz

app.config['UPLOADED_PHOTOS_DEST'] = 'uploads'

photos = UploadSet('photos', IMAGES)
configure_uploads(app, photos)

developMode = False
minPasswordLength = 6
howManyTriesInXTime = 3
XTime = 60
defaultPB = '/uploads/istockphoto-1393750072-612x612.jpg'
maxPostsPerSide = 30

class UploadForm(FlaskForm):
    photo = FileField(
        validators=[
            FileAllowed(photos, 'Nur Bilder sind erlaubt')
        ]
    )
    submit = SubmitField('Bestätigen')
    

likes_table = db.Table(
    'likes',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('post_id', db.Integer, db.ForeignKey('post.id'), primary_key=True)  # Kleinbuchstaben!
)

class Comments(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'))
    content = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

follows_table = db.Table(
    'follows',
    db.Column('following_user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('followed_user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True)  # Kleinbuchstaben!
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
    prefferedCategorie = db.Column(db.JSON, default=list)
    following = db.relationship(
        'User',
        secondary=follows_table,
        primaryjoin=id == follows_table.c.followed_user_id,
        secondaryjoin=id == follows_table.c.following_user_id,
        backref='follower'
    )
    reset_token = db.Column(db.String())
    expire_token = db.Column(db.DateTime)
    seenIds = db.Column(MutableList.as_mutable(db.JSON), default=list)

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.String(5000), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    likers = db.relationship('User', secondary=likes_table, back_populates='liked_posts')
    categorie = db.Column(db.JSON)

with app.app_context():
    db.create_all()

@app.after_request
def add_header(response):
    response.headers["Cache-Control"] = "no-store"
    return response

@app.route('/', methods=['GET', 'POST'])
def main():
    #check if session is on
    try:
        user_id = session.get("user_id")
    except:
        print("No active Session")

    session_user = User.query.get(user_id)

    if session_user != None:
        return redirect(url_for("feed", username = session_user.username, site=1))


    if request.method == 'POST':
        if request.form.get("GoToLogin") == "clicked":
            return redirect(url_for("login"))
        
        if request.form.get("GoTosignup") == "clicked":
            return redirect(url_for("signup"))
        

    return render_template("index.html")

@app.route('/signup', methods=['GET', 'POST'])
@limiter.limit("10 per hour")
def signup():
    #check if session is on
    try:
        user_id = session.get("user_id")
    except:
        print("No active Session")

    session_user = User.query.get(user_id)

    if session_user != None:
        return redirect(url_for("feed", username = session_user.username, site=1))

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
    #check if session is on
    try:
        user_id = session.get("user_id")
    except:
        print("No active Session")

    session_user = User.query.get(user_id)

    if session_user != None:
        return redirect(url_for("feed", username = session_user.username, site=1))

    tooManyTries = False
    emailOrUsername = ""
    timeUnit = "s"
    blockedTimeLeft =""
    if request.method == 'POST':

        if request.form.get("GoTosignup") == "clicked":
            return redirect(url_for("signup"))

        if request.form.get("ResetPasswordNotLoggedIn") == "clicked":
            return redirect(url_for("startReset"))

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

            if request.form.get("remember") == "clicked":
                pass

            return redirect(url_for("feed", username=user.username, site=1))
        else:
            user.triesInXTime += 1
            db.session.commit()
            print("Incorrect Password")
    return render_template('Login_Page.html', tooManyTries=tooManyTries, email=emailOrUsername, blockedTimeLeft=blockedTimeLeft, timeUnit=timeUnit)

@app.route('/reset-password', methods=['GET', 'POST'])
@limiter.limit("5 per hour")
def startReset():
    if request.method == "POST":
        action = request.form.get("action")
        if action == "submit":
            ResetPassword(request.form['email_address'])
            return redirect(url_for('login'))

    return render_template('reset-password-window.html')

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

    if session.get("show_profile_pic_form"):
        changeProfilePic = "shown"
        session.pop("show_profile_pic_form", None)

    form, file_url = ChangeProfilePic(username)

    if request.method == "POST":
        action = request.form.get("action")
        if action == "change_password":
            ChangePassword(user.id)

        if action == "change_email":
            newEmail = request.form['change_email']
            isEmail = CheckIfEmailisAnEmail(newEmail)
            if(isEmail):
                existing_user = User.query.filter_by(email_address=newEmail).first()

                if existing_user:
                    print("E-Mail existiert bereits")
                else:
                    session_user.email_address = newEmail
                    db.session.commit()

        if action == "change_username":
            newUsername = request.form['change_username']
            if(isEmail):
                existing_user = User.query.filter_by(username=newUsername).first()

                if existing_user:
                    print("Username existiert bereits")
                else:
                    session_user.username = newUsername
                    db.session.commit()

        elif action == "open_settings":
           return redirect(url_for("AccountSettings", username=user.username))
        elif action == "change_profilePic":
            session["show_profile_pic_form"] = True
        elif action == "delete_profilepic":
            session_user.profilePicture = defaultPB
            db.session.commit()
        elif action == "reset_password":
            token = uuid.uuid4().hex
            Send_email(session_user.email_address)
            return redirect(url_for("AccountSettings", token=token))
        elif action == "sign-out":
            session.clear()
            return redirect(url_for("main"))

        DeleteAccount(request.form.get("delete"))

        db.session.commit()
        return redirect(url_for("dashboard", username=username))

    print("User:", user,
          "\nUsername: ", user.username,
          "\nID: ", user.id)
    
    profilePicture = user.profilePicture
    
    users = User.query.all()
    
    if(username == "admin"):
        return render_template(
            'dashboard.html', 
            username = user.username, 
            created_at = user.created_at, users=users, 
            profilePicture=profilePicture,
            changeProfilePic=changeProfilePic,
            form=form,
            session_user= session_user)
    else:
        return render_template(
            'dashboard.html', 
            username = user.username, 
            created_at = user.created_at,
            users=users,
            profilePicture=profilePicture,
            changeProfilePic=changeProfilePic,
            file_url=file_url,
            form=form,
            session_user= session_user)

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

def ResetPassword(usernameOrEmail):
    try:
        user = User.query.filter_by(email_address=usernameOrEmail).first()
    except:
        user = User.query.filter_by(username=usernameOrEmail).first()
    
    token = secrets.token_urlsafe(32)
    token_rest = datetime.utcnow() + timedelta(minutes=15)

    user.reset_token = token
    user.expire_token = token_rest
    db.session.commit()

    Send_email(user.email_address, token)
    


def Send_email(mail_to, token):
    params = {
        "from": "quotelyapp@resend.dev",
        "to": ["clckzz07@gmail.com"],
        "subject": "Passwort zurücksetzen",
        "html": f"Dein Resetlink ist localhost:5000/reset-password/{token}"
    }

    resend.Emails.send(params)

@app.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    user = User.query.filter_by(
                reset_token=token
            ).first()
    
    if datetime.utcnow() <= user.expire_token:
        if request.method == "POST":
            action = request.form.get("action")
            if action == "change_password":
                user.reset_token = None
                user.expire_token = datetime.utcnow()
                db.session.commit()
                ChangePassword(user.id)
    else:
        redirect(url_for('main'))

    return render_template('reset-password.html')

@app.route("/uploads/<filename>")
def getFile(filename):
    return send_from_directory(app.config['UPLOADED_PHOTOS_DEST'], filename)

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

    if form.submit.data and form.validate_on_submit():
        if(form.photo.data == None):
            print("ERROR: NO PHOTO SELECTED")
        else:
            file_url = saveImage(form.photo.data)
            user.profilePicture = file_url
            db.session.commit()

    return form, file_url

def saveImage(photo):
    filename = photos.save(photo)
    return url_for('getFile', filename=filename)

@app.route('/user/<username>/feed/<site>', methods=['GET', 'POST'])
def feed(username, site):
    #check if session is on
    user_id = session.get("user_id")

    if not user_id:
        return redirect("/login")

    session_user = User.query.get(user_id)

    if session_user is None:
        return redirect("/login")
    
    if session_user.username != username:
        return redirect(url_for("feed", username=session_user.username, site=1))

    #Get the last X posts
    seen_ids = session_user.seenIds

    posts = (
        Post.query
        .filter(~Post.likers.any(id=session_user.id))  # noch nicht geliked
        .filter(~Post.id.in_(seen_ids))               # noch nicht gesehen
        .filter(Post.user_id != session_user.id)
        .order_by(Post.id.desc())
        .limit(maxPostsPerSide * 10)
        .all()
    )
    print(len(posts))

    #Calculate if post is relavent or not
    relevanceList = []
    for post in posts:
        
        creator_Of_Post = User.query.get(post.user_id)
        relevance = 0
        for i, value in enumerate(session_user.prefferedCategorie):
            new_val = value * post.categorie[i]
            relevance += new_val

        if session_user in creator_Of_Post.follower:
            relevance = 0.6 * relevance + .3 * .2 + .1 * len(post.likers)
        else:
            relevance = 0.6 * relevance + .3 * 0 + .1 * len(post.likers)

        relevanceList.append(relevance)
        

    #sort after relevance
    pairedList = list(zip(relevanceList, posts))
    pairedList.sort(key=lambda x: x[0], reverse=True)

    relevance_sorted, posts_sorted = zip(*pairedList)

    relevance_sorted = list(relevance_sorted)
    posts_sorted = list(posts_sorted)

    #check if it's already liked
    alreadyLiked = []

    for post in posts_sorted:
        if session_user in post.likers:
            alreadyLiked.append(1)
        else:
            alreadyLiked.append(0)

    print(alreadyLiked)

    final_sorted_posts = []
    for i,liked in enumerate(alreadyLiked):
        if len(final_sorted_posts) >= maxPostsPerSide:
            break
        if liked == 0:
            final_sorted_posts.append(posts_sorted[i])


    users = []
    for i in range(len(posts_sorted)):
        users.append(User.query.get(posts_sorted[i].user_id))

    post_id = request.form.get("post_id")

    user = User.query.get(user_id)
    post = Post.query.get(post_id)

    if request.method == "POST":
        action = request.form.get("action")
        print(action)
        post_index = request.form.get("post_id")
        if action != None:
            if action == "open_settings":
                return redirect(url_for("profileManager", username=session_user.username))
            elif action == ("give_like") and post_index:
                print("Gave a like!")
                if user not in post.likers:
                    post.likers.append(user)
                    prefferedCategorie = session_user.prefferedCategorie
                    new_preffered = []

                    for i, value in enumerate(prefferedCategorie):
                        new_value = value * .9 + post.categorie[i] * .1
                        new_preffered.append(new_value)

                    session_user.prefferedCategorie = new_preffered
                    db.session.commit()
                    return jsonify({"likes": len(post.likers)})
            elif action.startswith("post.id = "):
                post_id = action.split("=")[1]
                post_user_id = Post.query.get(post_id).user_id
                post_username = User.query.get(post_user_id).username 
                return redirect(url_for('profileManager', username=post_username, post_id=post_id))
            elif action.startswith("OpenPost.id = "):
                post_id = action.split("=")[1]
                return redirect(url_for('ViewPost', post_id=post_id))
            elif action == "new_post":
                return redirect(url_for('post', username=session_user.username))
            elif action == "search_user":
                print(request.form["search-input"])
                try:
                    return redirect(url_for("SearchUserMenu", search_input=request.form['search-input']))
                except Exception as e:
                    print("ERROR:", e)

    print("POST IDS:", [p.id for p in final_sorted_posts])

    final_post_ids = [post.id for post in final_sorted_posts]

    # sicherstellen, dass seenIds eine Liste ist
    session_user.seenIds = session_user.seenIds or []

    # IDs hinzufügen
    session_user.seenIds.extend(final_post_ids)

    #db.session.commit()

    return render_template('feed.html', posts=final_sorted_posts, users=users, session_user=session_user, preference=session_user.prefferedCategorie, alreadyLiked=alreadyLiked)

@app.route('/search/<search_input>', methods=['GET', 'POST'])
def SearchUserMenu(search_input):
    users = User.query.filter(User.username.ilike(f"%{search_input}%")).all()
    followerCountList = []
    for user in users:
        followerCountList.append(len(user.follower))

    #sort after relevance
    pairedList = list(zip(followerCountList, users))
    pairedList.sort(key=lambda x: x[0], reverse=True)

    followerCount_sorted, users_sorted = zip(*pairedList)

    followerCount_sorted = list(followerCount_sorted)
    users_sorted = list(users_sorted)

    if request.method == "POST":
        action = request.form.get("action")
        if action.startswith("user.id = "):
                user_id = action.split("=")[1]
                username = User.query.get(user_id).username 
                return redirect(url_for('profileManager', username=username))
        elif action == "search_user":
                print(request.form["search-input"])
                try:
                    return redirect(url_for("SearchUserMenu", search_input=request.form['search-input']))
                except Exception as e:
                    print("ERROR:", e)

    return render_template('search_user.html', users=users_sorted, lastSearch=search_input)

@app.route('/user/<username>/feed/like', methods=['POST'])
def give_like(username):
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "not logged in"}), 401

    session_user = User.query.get(user_id)
    if session_user.username != username:
        return jsonify({"error": "wrong user"}), 403

    data = request.get_json()
    post_id = data.get("post_id")
    post = Post.query.get(post_id)

    if not post:
        return jsonify({"error": "post not found"}), 404

    if session_user in post.likers:
        post.likers.remove(session_user)
        db.session.commit()
        liked = False
    else:
        post.likers.append(session_user)
        liked = True
        prefferedCategorie = session_user.prefferedCategorie
        new_preffered = []

        for i, value in enumerate(prefferedCategorie):
            new_value = value * .9 + post.categorie[i] * .1
            new_preffered.append(new_value)

        session_user.prefferedCategorie = new_preffered
        db.session.commit()

    return jsonify({"likes": len(post.likers), "liked": liked})

@app.route('/user/<username>/feed/comment', methods=['POST'])
def show_comments(username):
    data = request.get_json()
    post_id = data.get("post_id")
    
    # post_id kommt als "post-32" an → Zahl rausschneiden
    if isinstance(post_id, str) and post_id.startswith("post-"):
        post_id = post_id.replace("post-", "")
    
    comments = Comments.query.filter_by(post_id=post_id)\
    .order_by(Comments.created_at.desc())\
    .all()

    # ✅ Manuell serialisieren
    comments_list = [
        {
            "id": c.id,
            "content": c.content,
            "user_id": c.user_id,
            "username": User.query.get(c.user_id).username,
            "profilePicture": User.query.get(c.user_id).profilePicture,
            "created_at": c.created_at.strftime('%d.%m.%Y %H:%M')
        }
        for c in comments
    ]

    return jsonify({"data": comments_list})

@app.route('/user/<username>/feed/write_comment', methods=['POST'])
def write_comment(username):
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "not logged in"}), 401

    session_user = User.query.get(user_id)
    if session_user.username != username:
        return jsonify({"error": "wrong user"}), 403
    
    data = request.get_json()
    post_id = data.get("post_id")

    if isinstance(post_id, str) and post_id.startswith("post-"):
        post_id = post_id.replace("post-", "")

    content = data.get("content")
    
    new_comment = Comments(
            user_id=session_user.id,
            post_id=post_id,
            content=content
        )

    db.session.add(new_comment)
    db.session.commit()

    return jsonify({"comment" : content})

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
            user_id=session.get("user_id"),
            categorie = CategorizePost(contentOfPost)
        )
        
        db.session.add(new_post)
        user.totalPosts += 1
        db.session.commit()
        return redirect(url_for("feed", username=username, site=1))

    return render_template('post.html')

@app.route('/user/<username>', methods=['GET', 'POST'])
def profileManager(username):
     #check if session is on
    user_id = session.get("user_id")

    if not user_id:
        return redirect("/login")

    session_user = User.query.get(user_id)

    if session_user is None:
        return redirect("/login")

    user = User.query.filter_by(username=username).first()
    user_posts = Post.query.filter_by(user_id=user.id).with_entities(Post.id).all()

    posts_of_user = Post.query.filter_by(user_id=user.id)\
    .order_by(desc(Post.id))\
    .all()
    alreadyLiked = []

    for post in posts_of_user:
        if session_user in post.likers:
            alreadyLiked.append(1)
        else:
            alreadyLiked.append(0)

    post_ids = [p.id for p in user_posts]

    totalPosts = user.totalPosts
    
    if post_ids:  # falls der user überhaupt posts hat
        stmt = select(func.count()).select_from(likes_table).where(likes_table.c.post_id.in_(post_ids))
        totalLikes = db.session.execute(stmt).scalar()
    else:
        totalLikes = 0

    if request.method == "POST":
        action = request.form.get("action")
        if action == "open_settings_real":
            return redirect(url_for("dashboard", username=session_user.username))

    return render_template('profileView.html', totalPosts=totalPosts, username=username, totalLikes = totalLikes, user=user, session_user=session_user, user_posts=posts_of_user, alreadyLiked=alreadyLiked)

@app.route('/post/<post_id>')
def ViewPost(post_id):
    post = Post.query.get(post_id)
    user = User.query.filter_by(id=post.user_id).first()

    return render_template('ViewPostSingle.html', post_id=post_id, user=user, post=post)

@app.route('/user/<username>/follow', methods=['POST'])
def give_follow(username):
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "not logged in"}), 401

    session_user = User.query.get(user_id)

    data = request.get_json()
    id_to_follow = data.get("id_to_follow")
    user_to_follow = User.query.get(id_to_follow)

    if session_user in user_to_follow.follower:
        user_to_follow.follower.remove(session_user)
        db.session.commit()
        followed = False
    else:
        followed = True
        user_to_follow.follower.append(session_user)
        db.session.commit()

    return jsonify({"follower": len(user_to_follow.follower), "followed": followed})


if __name__ == "__main__":
    if developMode == True:
        app.run(debug=True)
    else:
        app.run(host="0.0.0.0", port=5000, debug=True)