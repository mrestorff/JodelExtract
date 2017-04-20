#!/usr/bin/env python
import os.path
from flask import Flask, session, request, url_for, redirect, render_template, g, abort
#import sqlite3
import random
import threading
import webbrowser
import argparse
import sys
import main
import TOOLS.Config as cfg

app = Flask(__name__)
instance = None
cmd_loc = None
cmd_mode = None

# ----------------------------------------------
# SQL database setup and connection
# TODO: Set up SQL database
# ----------------------------------------------
#def get_db(loc):
#    path = os.path.join(cfg.DATABASE_PATH, loc + ".db")
#    db = getattr(g, '_database', None)
#    if db is None:
#        if not os.path.isfile(path):
#            db = g._database = sqlite3.connect(path)
#            with app.open_resource('schema.sql', mode='r') as f:
#                db.cursor().executescript(f.read())
#            db.commit()
#            print("Initialized the database")
#        else:
#            db = g._database = sqlite3.connect(path)
#    return db
#
#@app.teardown_appcontext
#def close_connection(exception):
#    db = getattr(g, '_database', None)
#    if db is not None:
#        db.close()

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
    return dict(random_color=random_col(), random_col=random_col, vote=vote, pin=pin)

@app.route('/setup/', methods=['POST', 'GET'])
def setup():
    global cmd_loc
    global instance
    if request.args.get('kill_session') == "True":
        del(instance)
        instance = None
        return redirect(url_for('index'))
    else:
        if cmd_loc is not None:
            location = cmd_loc
            usage_mode = cmd_mode
            cmd_loc = None
        else:
            location = request.form.get('location')
            usage_mode = request.form.get('usage_mode')
            if usage_mode == "write":
                session['write_mode'] = True
            else:
                session['write_mode'] = False
        instance = main.start(loc=location)
        if instance is not None:
            #get_db(instance.connection.get_location_city())
            session['loc'] = instance.connection.get_location_string()
            return redirect(url_for('posts', mode='recent'))
        else:
            return redirect(url_for('index'))

@app.route('/posts/<mode>', methods=['GET'])
def posts(mode):
    if instance is not None:
        images = request.args.get('images')
        after_post_id = request.args.get('after')
        last_first_post = request.args.get('before')
        post_list, first_post, last_post = instance.posts(mode=mode, after_post_id=after_post_id, images=images)
        base_url = "/posts/"
        return render_template('show_posts.html', posts=post_list, first_post=first_post, last_post=last_post,
        last_first_post=last_first_post, base_url=base_url, current_mode=mode)
    else:
        return redirect(url_for('index'))

@app.route('/post/<post_id>', methods=['GET'])
def post(post_id):
    if instance is not None:
        channel = request.args.get('channel')
        comment_list, post_data = instance._open_post(post_id)
        if post_data:
            return render_template('post.html', post=post_data, comments=comment_list, channel=channel)
        else:
            abort(404)
    else:
        return redirect(url_for('index'))

@app.route('/channel/', defaults={'channel': 'None', 'mode': 'recent'})
@app.route('/channel/<channel>/<mode>', methods=['GET'])
def channel(channel, mode):
    if instance is not None:
        if channel in instance.channel_name_list:
            after_post_id = request.args.get('after')
            last_first_post = request.args.get('before')
            post_list, first_post, last_post = instance._open_channel(channel=channel, mode=mode, after_post_id=after_post_id)
            base_url = "/channel/" + channel + "/"
            return render_template('show_posts.html', posts=post_list, first_post=first_post, last_post=last_post,
            last_first_post=last_first_post, base_url=base_url, current_mode=mode, channel=channel)
        else:
            return render_template('channel_list.html', channels=instance.channel_list)
    else:
        return redirect(url_for('index'))

@app.route('/hashtag/<hashtag>/<mode>', methods=['GET'])
def hashtag(hashtag, mode):
    if instance is not None:
        after_post_id = request.args.get('after')
        last_first_post = request.args.get('before')
        post_list, first_post, last_post = instance._open_hashtag(hashtag=hashtag, mode=mode, after_post_id=after_post_id)
        base_url = "/hashtag/" + hashtag + "/"
        if post_list:
            return render_template('show_posts.html', posts=post_list, first_post=first_post, last_post=last_post,
            last_first_post=last_first_post, base_url=base_url, current_mode=mode, hashtag=hashtag)
        else:
            return redirect(url_for('posts', mode='recent'))
    else:
        return redirect(url_for('index'))

@app.route('/')
def index():
    if cmd_loc is not None:
        return redirect(url_for('setup'))
    elif not instance:
        session['title'] = "JodelExtract"
        return render_template('setup.html', usage_mode=cmd_mode)
    else:
        return redirect(url_for('posts', mode='recent'))

app.secret_key = '192837465'

def arguments():
    global cmd_loc
    global cmd_mode

    parser = argparse.ArgumentParser()
    opt = parser.add_argument_group("App Settings", "application settings and options")
    opt.add_argument("-i", "--store-images", action="store_true", help="store images in temp folder")
    opt.add_argument("-p", "--store-posts", action="store_true", help="store posts in database [UNAVAILABLE]")
    opt.add_argument("-l", "--location", nargs=1, help="a location, e.g. Hamburg,DE (without spaces!)", metavar="CITY,CC")
    opt.add_argument("-m", "--mode", choices=["read", "write"], default="read", help="read-only or write mode (default: %(default)s)")
    debug = parser.add_argument_group("Debugging Options")
    debug.add_argument("-d", "--debug", action="store_true", help="activate Flask debugging")
    debug.add_argument("-v", "--verbose", action="store_true", help="print connection handling")
    debug.add_argument("-a", "--api-replies", action="store_true", help="print API post replies")
    args = parser.parse_args()

    cfg.set_config(args.debug, args.verbose, args.store_images, args.store_posts, args.api_replies)
    app.debug = args.debug
    cmd_mode = args.mode
    if args.location and len(args.location) is 1:
        cmd_loc = args.location[0]
        print "Chosen location: " + cmd_loc
    elif args.location and len(args.location) is not 1:
        print "Invalid location input!"
        parser.print_help()
        sys.exit(1)

if __name__ == "__main__":
    arguments()
    port = 5000# + random.randint(0, 999)
    url = "http://127.0.0.1:{0}".format(port)
    threading.Timer(1.25, lambda: webbrowser.open(url, new=0)).start()
    print cfg.SPLASH_TEXT
    app.run(port=port)
