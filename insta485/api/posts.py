"""REST API for posts."""
import flask
import insta485
import insta485.model
import hashlib

@insta485.app.errorhandler(404)
def resource_not_found(e):
    return flask.jsonify(error=str(e)), 404

@insta485.app.errorhandler(403)
def invalid_auth(e):
    
  error = {
    "message": "Forbidden",
    "status_code": 403
  }

  return flask.jsonify(**error), 403

@insta485.app.errorhandler(400)
def bad_request(e):
  
  error = {
    "message": "Bad Request",
    "status_code": 400
  }

  return flask.jsonify(**error), 400

## Returns API Services
@insta485.app.route('/api/v1/', methods=['GET'])
def get_services():
        
    context = {
        "comments": "/api/v1/comments/",
        "likes": "/api/v1/likes/",
        "posts": "/api/v1/posts/",
        "url": "/api/v1/"
    }

    return flask.jsonify(**context)

## Returns Post IDs
@insta485.app.route('/api/v1/posts/', methods=['GET'])
def get_posts():
  
  if not userLoggedIn():
        flask.abort(403)
  
  db = insta485.model.get_db()

  size = flask.request.args.get("size", default=10, type=int)
  page = flask.request.args.get("page", default=0, type=int)
  postid_lte = flask.request.args.get("postid_lte", type=int)

  ## Error Handling
  if size < 1 or page < 0:
     flask.abort(400)

  if postid_lte:
    posts = db.execute(
      """
      SELECT posts.postid 
      FROM posts WHERE posts.postid <= ?  
      AND posts.owner IN (
          SELECT username2 FROM following WHERE username1 = ? 
          UNION 
          SELECT ?
      ) 
      ORDER BY posts.postid DESC LIMIT ? OFFSET ?
      """,
      (postid_lte, flask.session["username"], flask.session["username"], size, page*size,)
    ).fetchall()
  else:
    posts = db.execute(
      """
      SELECT posts.postid 
      FROM posts 
      WHERE posts.owner IN (
          SELECT username2 FROM following WHERE username1 = ? 
          UNION 
          SELECT ?
      ) 
      ORDER BY posts.postid DESC LIMIT ? OFFSET ?
      """,
      (flask.session["username"], flask.session["username"], size, page*size,)
    ).fetchall()
  
  for post in posts:
    post["url"] = f"/api/v1/posts/{post['postid']}/"

  if not postid_lte:
     postid_lte = posts[0]["postid"]

  if (len(posts) < size):
     next = ""
  else:
     next = flask.request.path + "?size=" + str(size) + "&page=" + str(page+1) + "&postid_lte=" + str(postid_lte)

  url = flask.request.full_path.rstrip('?')

  context = {"results": posts, "next": next, "url": url}
  return flask.jsonify(**context)

## Returns Post Data
@insta485.app.route('/api/v1/posts/<int:postid_url_slug>/', methods=['GET'])
def get_post(postid_url_slug):
  if not userLoggedIn():
    flask.abort(403)
  db = insta485.model.get_db()
  post = db.execute("SELECT * FROM posts WHERE postid = ?", (postid_url_slug,)).fetchone()
  if not post:
    flask.abort(404)
  
  comments = getComments(postid_url_slug, db)
  comments_url = f"/api/v1/comments/?postid={postid_url_slug}"
  created = post["created"]
  imgUrl = f"/uploads/{post["filename"]}"
  owner = post["owner"]
  ownerImgUrl = getOwnerImg(owner, db)
  ownerShowUrl  = f"/users/{owner}/"
  postid = post["postid"]
  postShowUrl = f"/posts/{postid}/"
  url = f"/api/v1/posts/{postid}/"
  likeCount = getNumberOfLikes(postid_url_slug, db)
  lognameLikesThis = getLognameLike(postid_url_slug, db)["status"]
  likeUrl = getLognameLike(postid_url_slug, db)["url"]

  likeObj = {
    "lognameLikesThis": lognameLikesThis,
    "numLikes": likeCount,
    "url": likeUrl
  }

  print(likeCount)

  context = { 
    "comments": comments, 
    "comments_url": comments_url,
    "created": created,
    "imgUrl": imgUrl,
    "owner": owner,
    "ownerImgUrl": ownerImgUrl,
    "ownerShowUrl": ownerShowUrl,
    "postid": postid,
    "postShowUrl": postShowUrl,
    "url": url,
    "likes": likeObj
  }

  return flask.jsonify(**context)

## Creates Like
@insta485.app.route('/api/v1/likes/', methods=['POST'])
def create_like():

  if not userLoggedIn():
     flask.abort(403)

  postid = flask.request.args.get('postid')
  if not postid:
     flask.abort(404)
  
  db = insta485.model.get_db()

  if not getLognameLike(postid, db)["status"]:
    db.execute(
       "INSERT INTO likes (owner, postid) "
       "VALUES (?, ?)",
       (flask.session["username"], postid)
    )

    likeid = getLognameLike(postid, db)["likeid"]
    url = getLognameLike(postid, db)["url"]

    response = {
       "likeid": likeid,
       "url": url
    }

    return flask.jsonify(**response), 201

  else:
     
    likeid = getLognameLike(postid, db)["likeid"]
    url = getLognameLike(postid, db)["url"]

    response = {
       "likeid": likeid,
       "url": url
    }

    return flask.jsonify(**response), 200

## Deletes Like
@insta485.app.route('/api/v1/likes/<int:likeid>/', methods=['DELETE'])
def delete_like(likeid):
  if not userLoggedIn():
    flask.abort(403)
  
  db = insta485.model.get_db()
  likeObj = db.execute(
     "SELECT * FROM likes WHERE likeid = ?",
     (likeid,)
  ).fetchone()

  if not likeObj:
     flask.abort(404)
  elif likeObj["owner"] != flask.session['username']:
     flask.abort(403)
  else:
    db.execute(
      "DELETE FROM likes "
      "WHERE owner = ? AND likeid = ?",
      (flask.session["username"], likeid,)
    )
    return flask.jsonify(), 204

## Creates Comment
@insta485.app.route('/api/v1/comments/', methods=['POST'])
def create_comment():
  if not userLoggedIn():
    flask.abort(403)
  
  postid = flask.request.args.get("postid")
  text = flask.request.get_json().get("text")

  db = insta485.model.get_db()
  
  ## Check if post exists
  post = db.execute(
     "SELECT * FROM posts WHERE postid = ?",
     (postid,)
  ).fetchone()

  if not post:
    flask.abort(404)

  db.execute(
     "INSERT INTO comments (owner, postid, text) "
     "VALUES (?, ?, ?)",
     (flask.session['username'], postid, text)
  )

  comment = db.execute("SELECT last_insert_rowid() as commentid").fetchone()

  response = {
    "commentid": comment["commentid"],
    "lognameOwnsThis": True,
    "owner": flask.session['username'],
    "ownerShowUrl": f"/users/{flask.session['username']}/",
    "text": text,
    "url": f"/api/v1/comments/{comment["commentid"]}/"
  }

  return flask.jsonify(**response), 201

## Deletes Comment
@insta485.app.route('/api/v1/comments/<commentid>/', methods=['DELETE'])
def delete_comment(commentid):
  if not userLoggedIn():
     flask.abort(403)
     
  db = insta485.model.get_db()
  commentObj = db.execute(
     "SELECT * FROM comments WHERE commentid = ?",
     (commentid,)
  ).fetchone()

  if not commentObj:
    flask.abort(404)
  elif flask.session['username'] != commentObj["owner"]:
    flask.abort(403)
  else:
    db.execute(
      "DELETE FROM comments "
      "WHERE owner = ? AND commentid = ?",
      (flask.session["username"], commentid,)
    )
    return flask.jsonify(), 204
 
  

## Post Helper Functions

def getComments(postid, db):
  comments = db.execute(
    "SELECT comments.commentid, "
    "comments.owner, comments.text "
    "FROM comments WHERE postid = ?", (postid,)
  ).fetchall()

  for comment in comments:
    if comment["owner"] == flask.session['username']:
      comment["lognameOwnsThis"] = True
    else:
      comment["lognameOwnsThis"] = False
    comment["ownerShowUrl"] = f"/users/{str(comment["owner"])}/"
    comment["url"] = f"/api/v1/comments/{str(comment["commentid"])}/"

  return comments

def getOwnerImg(owner, db):
  image = db.execute(
    "SELECT filename FROM users WHERE username = ?", (owner,)
  ).fetchone()
  return f"/uploads/{image['filename']}"

def getNumberOfLikes(postid, db):
  likes = db.execute(
    "SELECT COUNT(*) AS count FROM likes WHERE postid = ?", (postid,)
  ).fetchall()

  return likes[0]['count']

def getLognameLike(postid, db):
  obj = db.execute(
    "SELECT likeid FROM likes WHERE owner = ? AND postid = ?",
    (flask.session['username'], postid)
  ).fetchone()

  if obj: 
    return {"url": f"/api/v1/likes/{obj["likeid"]}/", "status": True, "likeid": obj["likeid"]}
  else:
    return {"url": None, "status": False, "likeid": None}

## Auth Helper Functions

## Returns True if User Logged In
def userLoggedIn():
    ## Check HTTP Auth
    auth = flask.request.authorization
    httpUsername = auth.username if auth else None
    httpPassword = auth.password if auth else None
    
    if 'username' in flask.session or checkAuth(httpUsername, httpPassword):
        return True
    else:
        return False

## Returns True if username and password exist and are correct
def checkAuth(username, password):
  if not username or not password:
      return False
  db = insta485.model.get_db()
  user = db.execute(
      "SELECT * FROM users WHERE username = ?", (username,)
  ).fetchone()
  if not user or not verifyPassword(password, user["password"]):
      return False
  else:
      ## Add user to session
      flask.session['username'] = username
      return True

## Returns True if input password hashes to stored password      
def verifyPassword(provided_password, stored_password):
  algorithm, salt, _ = stored_password.split('$')
  hash_obj = hashlib.new(algorithm)
  hash_obj.update((salt + provided_password).encode('utf-8'))
  return stored_password == "$".join([algorithm, salt, hash_obj.hexdigest()])
