from flask import Flask, session, request
from flask import url_for, redirect, render_template
import main

app = Flask(__name__)
instance = None

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

@app.route('/setup', methods=['POST'])
def setup():
    location = request.form.get('location')
    global instance
    instance = main.start(loc=location)
    if not instance == None:
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
        return render_template('setup.html')
    else:
        return redirect(url_for('posts'))

app.secret_key = '192837465'

if __name__ == "__main__":
    app.run()
