"""
Insta485 index (main) view.

URLs include:
/
"""

import pathlib
import os
import hashlib
import uuid
from flask import (
    render_template,
    session,
    redirect,
    url_for,
    request,
    abort,
    send_from_directory
)
import arrow
import insta485

insta485.app.secret_key = insta485.app.config['SECRET_KEY']

# GET Requests


@insta485.app.route('/')
def show_index():
    """Display / route."""
    if 'username' not in session:
        return redirect(url_for("show_login"))

    # Connect to database
    db = insta485.model.get_db()

    # Get all posts
    post_dump = db.execute(
        "SELECT posts.postid, posts.filename AS img_url, posts.owner AS "
        "post_owner, posts.created, users.filename AS profile_img "
        "FROM posts "
        "JOIN users ON posts.owner = users.username "
        "ORDER BY posts.postid DESC"
    )

    # Get Following users
    following_dump = db.execute(
        "SELECT username2 FROM following "
        "WHERE username1 = ?",
        (session['username'],)
    )

    post_dump = post_dump.fetchall()
    following_dump = following_dump.fetchall()

    following_dump.append({"username2": session['username']})
    followers = {item["username2"] for item in following_dump}
    post_dump = [item for item in post_dump if item["post_owner"] in followers]

    for post in post_dump:
        post["created"] = arrow.get(post["created"]).humanize()
        comments = db.execute(
            "SELECT * "
            "FROM comments "
            "WHERE comments.postid = ?", (post["postid"],)
        )

        likes = db.execute(
            "SELECT COUNT(*) FROM likes "
            "WHERE likes.postid = ?",
            (post["postid"],)
        )

        current_user_likes = db.execute(
            "SELECT * FROM likes "
            "WHERE likes.owner = ? AND likes.postid = ?",
            (session['username'], post["postid"])
        )

        current_user_likes = current_user_likes.fetchone()
        if not current_user_likes:
            like_action = "like"
        else:
            like_action = "unlike"

        like_count = likes.fetchall()
        comment_data = comments.fetchall()

        post["like_count"] = like_count[0]['COUNT(*)']
        post["comments"] = comment_data
        post["like_action"] = like_action

    context = {"db": post_dump, "current_user": session['username']}
    return render_template("index.html", **context)


@insta485.app.route('/posts/<postid_url_slug>/')
def show_post(postid_url_slug):
    """Display a single post given its unique post ID."""
    if 'username' not in session:
        return redirect(url_for("show_login"))

    # Connect to database
    db = insta485.model.get_db()

    # Retrieve Post
    posts = db.execute(
        "SELECT * FROM posts WHERE postid = ?", (postid_url_slug,)
    )

    post_raw = posts.fetchone()

    if not post_raw:
        abort(404)

    post = post_raw

    # Get comments
    comments = db.execute(
        "SELECT * FROM comments WHERE comments.postid = ?", (post["postid"],)
    )

    # Get likes count
    likes = db.execute(
        "SELECT COUNT(*) FROM likes WHERE likes.postid = ?", (post["postid"],)
    )

    # Get user profile image
    user = db.execute(
        "SELECT users.filename FROM users WHERE users.username = ?",
        (post["owner"],)
    )

    # Check if the current user has liked the post
    current_user_likes = db.execute(
        "SELECT * FROM likes WHERE likes.owner = ? AND likes.postid = ?",
        (session['username'], post["postid"])
    ).fetchone()

    like_action = "unlike" if current_user_likes else "like"

    user_data = user.fetchone()
    like_count = likes.fetchone()

    post["comments"] = comments.fetchall()
    post["created"] = arrow.get(post["created"]).humanize()
    post["like_count"] = like_count['COUNT(*)'] if like_count else 0
    post["profile_img"] = user_data['filename'] if user_data else None

    context = {
        "post": post,
        "like_action": like_action,
        "current_user": session['username']
    }

    return render_template("post.html", **context)


@insta485.app.route('/accounts/login/', methods=['GET'])
def show_login():
    """login."""
    if 'username' in session:
        return redirect(f"/users/{session['username']}/")
    return render_template("login.html")


@insta485.app.route('/users/<user_slug>/', methods=['GET'])
def show_user(user_slug):
    """Display user profile page."""
    if 'username' not in session:
        return redirect(url_for("show_login"))

    db = insta485.model.get_db()

    # Fetch user details
    user = db.execute(
        "SELECT * FROM users WHERE users.username = ?", (user_slug,)
    ).fetchone()

    if not user:
        abort(404)

    # Fetch following relationship
    following_dump = db.execute(
        "SELECT * FROM following "
        "WHERE following.username1 = ? "
        "AND following.username2 = ?",
        (session['username'], user_slug)
    )

    # Fetch user posts
    user_posts = db.execute(
        "SELECT * FROM posts WHERE posts.owner = ?", (user_slug,)
    ).fetchall()

    total_post_count = len(user_posts) if user_posts else 0

    # Determine relationship status
    if user_slug == session['username']:
        relationship = ""
    elif not following_dump.fetchone():
        relationship = "not following"
    else:
        relationship = "following"

    # Fetch followers count
    followers = db.execute(
        "SELECT * FROM following WHERE username2 = ?", (user_slug,)
    ).fetchall()
    follower_count = len(followers) if followers else 0

    # Fetch following count
    following = db.execute(
        "SELECT * FROM following WHERE username1 = ?", (user_slug,)
    ).fetchall()
    following_count = len(following) if following else 0

    # Fetch posts count
    posts = db.execute(
        "SELECT * FROM posts WHERE posts.owner = ?", (user_slug,)
    ).fetchall()
    post_count = len(posts) if posts else 0

    context = {
        "current_user": session['username'],
        "relationship": relationship,
        "user": user,
        "total_post_count": total_post_count,
        "follower_count": follower_count,
        "following_count": following_count,  # ✅ No longer unassigned
        "posts": posts,
        "post_count": post_count
    }

    return render_template("user.html", **context)


@insta485.app.route('/accounts/auth/')
def aws_route():
    """Authenticate."""
    if 'username' not in session:
        abort(403)
    else:
        return "", 200


@insta485.app.route('/users/<username>/followers/', methods=['GET'])
def show_followers(username):
    """Display /users/<username>/followers/ route."""
    if "username" not in session:
        return redirect(url_for('show_login'))

    logname = session["username"]
    db = insta485.model.get_db()

    # Validate username
    user_exists = db.execute(
        "SELECT 1 FROM users WHERE username = ?",
        (username,)
    ).fetchone()

    if not user_exists:
        abort(404)

    # Retrieve followers
    followers = db.execute(
        "SELECT users.filename AS user_img_url, users.username "
        "FROM users "
        "JOIN following ON users.username = following.username1 "
        "WHERE following.username2 = ?", (username,)
    ).fetchall()

    # Check if logname follows each follower
    for follower in followers:
        follower["logname_follows_username"] = db.execute(
            "SELECT 1 FROM following WHERE username1 = ? AND username2 = ?",
            (logname, follower["username"])
        ).fetchone() is not None

    return render_template(
        "followers.html",
        logname=logname,
        username=username,
        followers=followers,
        curr_path=request.path
    )


@insta485.app.route('/users/<username>/following/', methods=['GET'])
def show_following(username):
    """Display /users/<username>/following/ route."""
    if "username" not in session:
        return redirect(url_for('show_login'))

    logname = session["username"]
    db = insta485.model.get_db()

    # Validate username
    user_exists = db.execute(
        "SELECT 1 FROM users WHERE username = ?",
        (username,)
    ).fetchone()

    if not user_exists:
        abort(404)

    # Retrieve users followed by username
    following = db.execute(
        "SELECT users.filename AS user_img_url, users.username "
        "FROM users "
        "JOIN following ON users.username = following.username2 "
        "WHERE following.username1 = ?", (username,)
    ).fetchall()

    # Check if logname follows each user
    for follow in following:
        follow["logname_follows_username"] = db.execute(
            "SELECT 1 FROM following WHERE username1 = ? AND username2 = ?",
            (logname, follow["username"])
        ).fetchone() is not None

    return render_template(
        "following.html",
        logname=logname,
        username=username,
        following=following,
        curr_path=request.path
    )


@insta485.app.route('/explore/', methods=['GET'])
def show_explore():
    """Display /explore/ route."""
    # Redirect to login if user is not authenticated
    if "username" not in session:
        return redirect(url_for('show_login'))

    logname = session["username"]
    db = insta485.model.get_db()

    # Retrieve users not followed by the logged-in user
    query = (
        "SELECT username, filename AS user_img_url "
        "FROM users WHERE username != ? "
        "AND username NOT IN ("
        "    SELECT username2 FROM following WHERE username1 = ?"
        ")"
    )
    not_following = db.execute(query, (logname, logname)).fetchall()

    return render_template(
        "explore.html",
        logname=logname,
        not_following=not_following,
        curr_path=request.path
    )


@insta485.app.route('/accounts/create/', methods=['GET'])
def show_create_account():
    """Display /accounts/create/ route."""
    # If logged in, redirect to /accounts/edit/
    if 'username' in session:
        return redirect(url_for("show_account_edit"), code=302)

    return render_template("create.html")


@insta485.app.route('/accounts/edit/', methods=['GET'])
def show_account_edit():
    """Display the account edit page."""
    db = insta485.model.get_db()

    if 'username' not in session:
        return redirect(url_for("show_login"))

    user_data = db.execute(
        "SELECT * FROM users WHERE users.username = ?",
        (session['username'],)
    ).fetchone()

    context = {
        "current_user": session['username'],
        "fullname": user_data["fullname"],
        "email": user_data["email"]
    }

    return render_template("edit.html", **context)


@insta485.app.route('/accounts/delete/', methods=['GET'])
def show_account_delete():
    """delete_account."""
    return render_template("delete.html")


@insta485.app.route('/accounts/password/', methods=['GET'])
def show_password_page():
    """show_password."""
    return render_template("password.html")


# POST Requests


@insta485.app.route('/accounts/logout/', methods=['POST'])
def logout():
    """logout."""
    session.pop('username', None)
    return redirect(url_for("show_login"))


@insta485.app.route('/accounts/', methods=['POST'])
def account_options():
    """Handle various account operations."""
    db = insta485.model.get_db()
    operation = request.form.get('operation')

    if operation == 'login':
        return handle_login(db)
    if operation == 'logout':
        return handle_logout()
    if operation == 'create':
        return handle_account_creation(db)
    if operation == 'edit_account':
        return handle_account_edit(db)
    if operation == 'delete':
        return handle_account_deletion(db)
    if operation == 'update_password':
        return handle_password_update(db)
    abort(400)


def handle_login(db):
    """options_like."""
    form_username = request.form.get('username')
    form_password = request.form.get('password')
    target_url = request.args.get('target', '/')
    if not form_username or not form_password:
        abort(400)
    user = db.execute(
        "SELECT * FROM users WHERE users.username = ?", (form_username,)
    ).fetchone()
    if not user or not verify_password(user['password'], form_password):
        abort(403)
    session['username'] = form_username
    return redirect(target_url)


def verify_password(stored_password, provided_password):
    """options_like."""
    algorithm, salt, _ = stored_password.split('$')
    hash_obj = hashlib.new(algorithm)
    hash_obj.update((salt + provided_password).encode('utf-8'))
    return stored_password == "$".join([algorithm, salt, hash_obj.hexdigest()])


def handle_logout():
    """options_like."""
    session.pop('username', None)
    return redirect(url_for("show_login"))


def handle_account_creation(db):
    """options_like."""
    target_url = request.args.get('target', '/')
    fullname, email, username, password = (
        request.form.get("fullname"),
        request.form.get("email"),
        request.form.get("username"),
        request.form.get("password"),
    )
    password_db_string = hash_password(password)
    uuid_basename = save_uploaded_file(request.files["file"])

    db.execute(
        "INSERT INTO users (username, fullname, email, filename, password) "
        "VALUES (?, ?, ?, ?, ?)",
        (username, fullname, email, uuid_basename, password_db_string)
    )
    session['username'] = username
    return redirect(target_url)


def hash_password(password):
    """options_like."""
    algorithm = 'sha512'
    salt = uuid.uuid4().hex
    hash_obj = hashlib.new(algorithm)
    hash_obj.update((salt + password).encode('utf-8'))
    return "$".join([algorithm, salt, hash_obj.hexdigest()])


def save_uploaded_file(fileobj):
    """options_like."""
    filename = fileobj.filename
    uuid_hex = uuid.uuid4().hex
    ext = pathlib.Path(filename).suffix.lower()
    uuid_basename = f"{uuid_hex}{ext}"
    path = insta485.app.config["UPLOAD_FOLDER"] / uuid_basename
    fileobj.save(path)
    return uuid_basename


def handle_account_edit(db):
    """options_like."""
    if 'username' not in session:
        abort(403)
    fullname, email = request.form.get('fullname'), request.form.get('email')
    if not fullname or not email:
        abort(400)

    if request.files.get('file'):
        update_profile_image(db)
    db.execute("UPDATE users SET fullname = ?, email = ? WHERE username = ?",
               (fullname, email, session['username']))
    return redirect(request.args.get('target', '/'))


def update_profile_image(db):
    """options_like."""
    user = db.execute("SELECT filename FROM users WHERE username = ?",
                      (session['username'],)).fetchone()
    if user:
        upload_folder = insta485.app.config['UPLOAD_FOLDER']
        file_path = os.path.join(upload_folder, user['filename'])
        os.remove(file_path)
    new_filename = save_uploaded_file(request.files["file"])
    db.execute("UPDATE users SET filename = ? WHERE username = ?",
               (new_filename, session['username']))


def handle_account_deletion(db):
    """options_like."""
    if 'username' not in session:
        abort(403)

    delete_user_files(db)
    db.execute("DELETE FROM users WHERE username = ?", (session['username'],))
    session.clear()
    return redirect(request.args.get('target', '/'))


def delete_user_files(db):
    """options_like."""
    posts = db.execute("SELECT filename FROM posts WHERE owner = ?",
                       (session['username'],)).fetchall()
    upload_folder = insta485.app.config['UPLOAD_FOLDER']

    for post in posts:
        file_path = os.path.join(upload_folder, post['filename'])
        os.remove(file_path)

    user = db.execute(
        "SELECT filename FROM users WHERE username = ?", (session['username'],)
    ).fetchone()

    if user:
        file_path = os.path.join(upload_folder, user['filename'])
        os.remove(file_path)


def handle_password_update(db):
    """options_like."""
    if 'username' not in session:
        abort(403)
    password, new_password1, new_password2 = (
        request.form.get('password'),
        request.form.get('new_password1'),
        request.form.get('new_password2'),
    )
    if not password or not new_password1 or not new_password2:
        abort(400)

    current_password = db.execute(
        "SELECT password FROM users WHERE username = ?", (session['username'],)
    ).fetchone()

    if (not current_password or
            not verify_password(current_password['password'], password)):
        abort(403)

    if new_password1 != new_password2:
        abort(401)

    hashed_password = hash_password(new_password1)
    db.execute("UPDATE users SET password = ?", (hashed_password,))
    return redirect(request.args.get('target', '/'))


@insta485.app.route('/likes/', methods=['POST'])
def like_options():
    """options_like."""
    db = insta485.model.get_db()
    target_url = request.args.get('target', '/')

    if request.form.get('operation') == 'like':

        postid = request.form.get('postid')

        valid_like = db.execute(
            "SELECT * FROM likes "
            "WHERE likes.postid = ? AND likes.owner = ?",
            (postid, session['username'])
        )

        if not valid_like.fetchall():
            db.execute(
                "INSERT INTO likes (owner, postid) "
                "VALUES (?, ?)",
                (session["username"], postid)
            )
        else:
            abort(409)
    if request.form.get('operation') == 'unlike':
        postid = request.form.get('postid')
        valid_unlike = db.execute(
            "SELECT * FROM likes "
            "WHERE likes.postid = ? AND likes.owner = ?",
            (postid, session['username'])
        )

        if not valid_unlike.fetchall():
            abort(409)
        else:
            db.execute(
                "DELETE FROM likes "
                "WHERE owner = ? AND postid = ?",
                (session["username"], postid)
            )

    return redirect(target_url)


@insta485.app.route('/comments/', methods=['POST'])
def comment_options():
    """comment_options."""
    db = insta485.model.get_db()
    target_url = request.args.get('target', '/')
    postid = request.form.get('postid')
    text = request.form.get('text')
    comment = request.form.get('commentid')

    if request.form.get('operation') == 'create':
        if request.form.get('text') == "":
            abort(400)
        else:
            db.execute(
                "INSERT INTO comments (owner, postid, text) "
                "VALUES (?, ?, ?)",
                (session['username'], postid, text)
            )

            return redirect(target_url)
    elif request.form.get('operation') == 'delete':
        db.execute(
            "DELETE FROM comments WHERE commentid = ?", (comment,)
        )

    return redirect(target_url)


@insta485.app.route('/posts/', methods=['POST'])
def post_options():
    """Handle post creation and deletion."""
    db = insta485.model.get_db()
    target_url = request.args.get('target', '/users/awdeorio/')
    operation = request.form.get('operation')

    if operation == 'delete':
        postid = request.form.get('postid')

        image = db.execute(
            "SELECT * FROM posts WHERE postid = ?", (postid,)
        ).fetchone()

        if image:
            file_path = os.path.join(
                insta485.app.config['UPLOAD_FOLDER'],
                image["filename"]
            )

            # Delete the file from the filesystem
            if os.path.exists(file_path):
                os.remove(file_path)

            # Remove post from database
            db.execute(
                "DELETE FROM posts WHERE postid = ?", (postid,)
            )

    elif operation == 'create':
        fileobj = request.files.get('file')
        if fileobj is None or fileobj.filename == '':
            abort(400)

        filename = fileobj.filename
        stem = uuid.uuid4().hex
        suffix = pathlib.Path(filename).suffix.lower()
        uuid_basename = f"{stem}{suffix}"
        path = insta485.app.config["UPLOAD_FOLDER"] / uuid_basename
        fileobj.save(path)

        # Insert the new post into the database
        db.execute(
            "INSERT INTO posts (filename, owner) VALUES (?, ?)",
            (uuid_basename, session["username"])
        )
    return redirect(target_url)


@insta485.app.route('/following/', methods=['POST'])
def follow_actions():
    """follow_action."""
    db = insta485.model.get_db()
    target_url = request.args.get('target', '/')
    operation = request.form.get('operation')
    username = request.form.get('username')

    if operation == 'follow':

        current_user_following = db.execute(
            "SELECT username2 FROM following "
            "WHERE following.username1 = ? "
            "AND following.username2 = ?",
            (session['username'], username)
        )

        if not current_user_following.fetchone():
            db.execute(
                "INSERT INTO following (username1, username2) "
                "VALUES (?, ?)",
                (session['username'], username)
            )

        else:
            abort(409)

    elif operation == 'unfollow':
        current_user_following = db.execute(
            "SELECT username2 FROM following "
            "WHERE following.username1 = ? "
            "AND following.username2 = ?",
            (session['username'], username)
        )

        if current_user_following.fetchone():
            db.execute(
                "DELETE FROM following "
                "WHERE username1 = ? AND username2 = ?",
                (session['username'], username)
            )
        else:
            abort(409)

    return redirect(target_url)


UPLOAD_FOLDER = insta485.app.config['UPLOAD_FOLDER']


@insta485.app.route('/uploads/<filename>')
def show_image(filename):
    """show_image."""
    if 'username' not in session:
        abort(403)

    filepath = os.path.join(UPLOAD_FOLDER, filename)
    if not os.path.exists(filepath):
        abort(404)

    return send_from_directory(UPLOAD_FOLDER, filename)
