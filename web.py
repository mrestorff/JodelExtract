#!/usr/bin/env python2
import os.path
from flask import Flask, session, request, url_for, redirect, render_template, g, abort
import sqlite3
import random
import threading
import webbrowser
import main
import TOOLS.Config as cfg

app = Flask(__name__)
app.config['DEBUG'] = cfg.DEBUG
instance = None

# ----------------------------------------------
# SQL database setup and connection
# TODO: Set up SQL database
# ----------------------------------------------
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

@app.errorhandler(404)
def page_not_found(e):
    message = "Nomnom.. Our racoon ate the page you were looking for."
    return render_template('error.html', error=message), 404

@app.errorhandler(500)
def internal_server_error(e):
    message = "Oops! An internal error occured."
    return render_template('error.html', error=message), 500

@app.context_processor
def remote_functions():
    def random_col():
        colorspec = ['blue', 'turquoise', 'green', 'red', 'orange', 'yellow']
        return random.choice(colorspec)
    def vote(post_id, value): # 1=up; 0=down
        instance._vote(post_id, value)
    def pin(post_id, value): # 1=pin; 0=unpin
        instance._pin(post_id, value)
    return dict(random_color=random_col(), random_col=random_col, vote=vote(), pin=pin())

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
            session['loc'] = instance.connection.get_location_string()
            return redirect(url_for('posts', mode='recent'))
        else:
            return redirect(url_for('index'))

@app.route('/posts/<mode>', methods=['GET'])
def posts(mode):
    if not instance == None:
        after_post_id = request.args.get('after')
        last_first_post = request.args.get('before')
        post_list, first_post, last_post = instance.posts(mode=mode, after_post_id=after_post_id)
        base_url = "/posts/"
        return render_template('show_posts.html', posts=post_list, first_post=first_post, last_post=last_post,
        last_first_post=last_first_post, base_url=base_url, active_page=mode)
    else:
        return redirect(url_for('index'))

@app.route('/post/<post_id>', methods=['GET'])
def particular_post(post_id):
    if not instance == None:
        channel = request.args.get('channel')
        comment_list, post_data = instance._open_post(post_id)
        if comment_list != False:
            return render_template('particular_post.html', post=post_data, comments=comment_list, channel=channel)
        else:
            abort(404)
    else:
        return redirect(url_for('index'))

@app.route('/channel/', defaults={'channel': 'None', 'mode': 'recent'})
@app.route('/channel/<channel>/<mode>', methods=['GET'])
def channel(channel, mode):
    if not instance == None:
        if channel in instance.channel_name_list:
            after_post_id = request.args.get('after')
            last_first_post = request.args.get('before')
            post_list, first_post, last_post = instance._open_channel(channel=channel, mode=mode, after_post_id=after_post_id)
            base_url = "/channel/" + channel + "/"
            return render_template('show_posts.html', posts=post_list, first_post=first_post, last_post=last_post,
            last_first_post=last_first_post, base_url=base_url, active_page=mode, channel=channel)
        else:
            return render_template('channel_list.html', channels=instance.channel_list)
    else:
        return redirect(url_for('index'))

# TODO: check if function still feasable (API v3)
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
        return redirect(url_for('posts', mode='recent'))

app.secret_key = '192837465'

if __name__ == "__main__":
    port = 5000# + random.randint(0, 999)
    url = "http://127.0.0.1:{0}".format(port)
    threading.Timer(1.25, lambda: webbrowser.open(url, new=0)).start()
    print cfg.SPLASH_TEXT
    app.run(port=port, debug=False)
