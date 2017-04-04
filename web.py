import os.path
from flask import Flask, session, request, url_for, redirect, render_template, g
import sqlite3
import main
import TOOLS.Config as cfg

app = Flask(__name__)
app.config['DEBUG'] = cfg.DEBUG
instance = None

def get_db(loc):
    path = os.path.join(cfg.DATABASE_PATH, loc + ".db")
    db = getattr(g, '_database', None)
    if db is None:
        if not os.path.isfile(path):
            db = g._database = sqlite3.connect(path)
            with app.open_resource('schema.sql', mode='r') as f:
                db.cursor().executescript(f.read())
            db.commit()
            print("Initialized the database")
        else:
            db = g._database = sqlite3.connect(path)
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

# ----------------------------------------------
# Request and site methods
# ----------------------------------------------
@app.after_request
def add_header(response):
    """
    Add headers to both force latest IE rendering engine or Chrome Frame,
    and also to cache the rendered page for 10 minutes.
    """
    response.headers['X-UA-Compatible'] = 'IE=Edge,chrome=1'
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate" # HTTP 1.1.
    response.headers["Pragma"] = "no-cache" # HTTP 1.0.
    response.headers["Expires"] = "0" # Proxies.
    return response

@app.route('/setup', methods=['POST', 'GET'])
def setup():
    global instance
    if request.args.get('kill_session') == "True":
        del(instance)
        instance = None
        return redirect(url_for('index'))
    else:
        location = request.form.get('location')
        instance = main.start(loc=location)
        if not instance == None:
            get_db(instance.connection.get_location_city())
            session['title'] = "JodelExtract: " + instance.connection.get_location_string()
            return redirect(url_for('posts'))
        else:
            return redirect(url_for('index'))

@app.route('/posts/', defaults={'mode': 'recent'})
@app.route('/posts/<mode>', methods=['GET'])
def posts(mode):
    if not instance == None:
        post_list = instance.posts(mode=mode)
        return render_template('show_posts.html', posts=post_list)
    else:
        return redirect(url_for('index'))

@app.route('/post/<post_id>', methods=['GET'])
def particular_post(post_id):
    if not instance == None:
        comment_list = instance._open_post(post_id)
        post_data = instance.post_list[post_id]
        return render_template('particular_post.html', post=post_data, comments=comment_list)
    else:
        return redirect(url_for('index'))

@app.route('/channel/', defaults={'channel': 'Leuphana'})
@app.route('/channel/<channel>', methods=['GET'])
def channel_posts(channel):
    if not instance == None:
        post_list = instance._open_channel(channel=channel)
        return render_template('show_posts.html', posts=post_list)
    else:
        return redirect(url_for('index'))

@app.route('/user/<user_id>', methods=['GET'])
def user_posts(user_id):
    if not instance == None:
        post_list = instance.get_user_posts(user_id)
        if post_list:
            return render_template('show_posts.html', posts=post_list)
        else:
            return redirect(url_for('posts'))
    else:
        return redirect(url_for('index'))

@app.route('/')
def index():
    if not instance:
        session['title'] = "JodelExtract"
        return render_template('setup.html')
    else:
        return redirect(url_for('posts'))

app.secret_key = '192837465'

if __name__ == "__main__":
    app.run()
