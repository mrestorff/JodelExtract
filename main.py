import json
import tempfile
from StringIO import StringIO
import array
import os
import shutil
import pprint
import argparse
import sys
import enum
import appdirs
import time
import requests
import TOOLS.Connection
import TOOLS.PostHandler
import TOOLS.Config as cfg

# enable utf8
reload(sys)
sys.setdefaultencoding('utf8')

def timesort(post):
    """Returns post's post ID as an int for sorting"""
    return int(post['post_id'], 16)

class JodelExtract():
    """ The main class """

    def __init__(self, recent_posts=None):
        try:
            self.tempdir = appdirs.user_cache_dir(cfg.APP_NAME,cfg.APP_AUTHOR)
            if not os.path.exists(self.tempdir):
                os.makedirs(self.tempdir)
            print "Tempdir set to: " + self.tempdir
        except Exception as e:
            print "Cannot create tempdir: "+str(e)
            return False

        # dictionary of dynamically generated notebook pages
        #self.notebook_pages_dict = {}
        # map post_category <=> page container widget
        #self.page_container_widget_dict = {}
        # dictionary for tuples of function and parameter list to refresh each tab
        #self.reload_function_dict = {}
        # map post_category_type <=> tab number
        #self.tab_num_dict = {}
        self.posts_mode_dict = {}
        self.post_list = {}
        #self.my_posts_notebook_page = None

        #for post_category in post_category_type:
        #    self.posts_mode_dict[post_category] = TOOLS.Connection.PostType.COMBO

        # POST MODE SETTINGS
        self.my_posts_mode = TOOLS.Connection.PostType.COMBO
        self.posts_mode = TOOLS.Connection.PostType.COMBO

        #self.reload
        #self.new_post
        #self.new_channel
        #self.change_location
        #self.view_karma

    def clean_tempdir(self,max_age=7*86400):
        try:
            files_in_temp = os.listdir(self.tempdir)
            for f in files_in_temp:
                real_path = os.path.join(self.tempdir,f)
                try:
                    if os.path.isfile(real_path) and (time.time() - os.stat(real_path).st_atime > max_age):
                        os.remove(real_path)
                except Exception as e:
                    print "Could not delete file: "+str(e)
        except Exception as e:
            print "Could not clean temp dir: "+str(e)

    def initialize(self, citycc=None, location=None, initial_channels=None, mode=None):
        """Set up the connection to Jodel
           citycc  A location in City, CC format as in "Vienna, AT"
           """

        # make a new connection object
        self.connection = TOOLS.Connection.Connection(location=location,citycc=citycc)
        if self.connection is None:
            print "Could not connect to server"
            self.destroy()
            return None

        #if initial_channels is None:
        #    recommended_channels = self.connection.recommended_channels()
        #    if recommended_channels is not False:
        #        initial_channels = [channel['channel'] for channel in recommended_channels['recommended']]
        #    else:
        #        initial_channels = []

        if mode is not None:
            self.posts_mode = mode

        #self.posts(mode=self.posts_mode) # => calls posts further down the code
        #self.my_posts()
        #self.my_replies()
        #self.my_voted_posts()
        #self.my_pinned_posts()
        if initial_channels is not None:
            for initial_channel in initial_channels:
                self._open_channel(self,initial_channel)
        return False

    def view_karma(self, widget, data):
        """ This method opens a dialog which shows the user's current karma.
            The karma value is fetched from the API

           widget and data are parameters required for callbacks but are
           ignored"""
        reply = self.connection.karma()


# ----------------------------------------------------------------------
# Methods for updating posts
# ----------------------------------------------------------------------

    def posts(self, post_data_dict=None, mode=None):
        """ post_data_dict  Initial data for the tab (do not fetch from API)
            mode  Data fetching mode (e.g. popular mode) from TOOLS.Connection.PostType
        """

        if mode is None:
            #mode = self.posts_mode_dict[post_category_type.POSTS]
            mode = TOOLS.Connection.PostType.COMBO

        # Fetch posts from the API if no data is supplied
        if post_data_dict is None:
            if mode == TOOLS.Connection.PostType.POPULAR or mode == "popular":
                post_data_dict = self.connection.popular_posts()
            elif mode == TOOLS.Connection.PostType.DISCUSSED or mode == "discussed":
                post_data_dict = self.connection.discussed_posts()
            elif mode == TOOLS.Connection.PostType.COMBO or mode == "combo":
                raw_post_data_dict = self.connection.combo_posts()
                post_data_dict = {'posts': sorted(raw_post_data_dict['replied'] +
                        raw_post_data_dict['voted'] +
                        raw_post_data_dict['recent'],key=timesort,reverse=True)}
            elif mode == TOOLS.Connection.PostType.ALL or mode == "recent":
                post_data_dict = self.connection.recent_posts()
            else:
                post_data_dict = self.connection.recent_posts()

        if post_data_dict is False:
            print "Error! Could not fetch post data."

        self.post_data_dict = post_data_dict

        #print "Post count: " + len(post_data_dict['posts'])
        if post_data_dict:
            debug = False
            temp_post_list = []
            if debug == False:
                #try:
                for post in post_data_dict['posts']:
                    if post['post_id'] in self.post_list:
                        p = self.post_list[post['post_id']]
                        # update post object
                        p.update(post)
                        temp_post_list.append(p)
                    else:
                        p = TOOLS.PostHandler.Post(post,self.tempdir,self,self.connection)
                        temp_post_list.append(p)
                        self.post_list[post['post_id']] = p
                #except:
                #    print post_data_dict

            if debug == True:
                post = post_data_dict['posts'][0]
                print "#########"
                print post
                print "#########"
                input = "0"
                while input is not "exit":
                    input = raw_input(">> ")
                    print "#########"
                    print post[input]
                    print "#########"
        print len(self.post_list)
        return temp_post_list


    def _open_channel(self, channel, main=None):
        """ Load posts for channel or hashtag from API """

        # Fetch posts from the API
        channel_data_dict = self.connection.get_channel(channel)

        if channel_data_dict is False:
            return

        try:
            head = unicode(channel,errors='replace')
        except TypeError:
            head = channel

        print """
        #########################################
        Channel loading: @"""+channel+"\n"

        # Check if this channel has posts, and list them if yes
        channel_posts_list = channel_data_dict.get('recent')
        temp_post_list = []
        if channel_posts_list is not None and len(channel_posts_list) > 0:
            for post in channel_posts_list:
                    p = TOOLS.PostHandler.Post(post,self.tempdir,self,self.connection)
                    temp_post_list.append(p)
                    # inserting into permanent list as well
                    self.post_list[post['post_id']] = p
        return temp_post_list

    def _open_post(self, post_id, main=None):
        """ Update original post and load comments from API """

        # Fetch posts from the API
        this_post = post = self.connection.particular_post(post_id)

        # get post & answers
        if this_post is None:
            print "Could not fetch " + post_id
            for post in self.post_data_dict['posts']:
                if post['post_id'] == post_id:
                    this_post = post
                    break
        if this_post is None:
            return False

        # generate & update post object for original post
        temp_post_list = []
        if this_post['post_id'] in self.post_list:
            p = self.post_list[this_post['post_id']]
            # update post object
            p.update(this_post)
            temp_post_list.append(p)
        else:
            p = TOOLS.PostHandler.Post(this_post,self.tempdir,self,self.connection)
            temp_post_list.append(p)
            self.post_list[this_post['post_id']] = p

        # extract data we need for user numbering
        user_handle = post.get('user_handle')
        userlist = None
        if user_handle is not None:
            # OP gets id 0
            userlist = {post['user_handle']: 0}

        # Check if this post has replies, and list them if yes
        children_posts_list = this_post.get('children')
        # Counts the number of responses, counts even when one poster posts multiple times
        response_index = 0
        comments_list = []
        if children_posts_list is not None and len(children_posts_list) > 0:
            for reply in children_posts_list:
                # Sometimes, the API supplies us with user numbers to
                # view who posted which answer
                response_index += 1
                user_handle = reply.get('user_handle')
                user_index = None
                if (user_handle is not None) and (userlist is not None):
                    if user_handle not in userlist:
                        userlist[user_handle] = response_index
                    user_index = userlist[user_handle]
                comments_list.append(TOOLS.PostHandler.Post(reply,self.tempdir,self,self.connection,userno=user_index,reply=True))
        return comments_list

    def get_user_posts(self, user_id):
        post_list = []
        if user_id:
            for post in dict.values(self.post_list):
                if post.post['user_handle'] == user_id:
                    post_list.append(post)
            return post_list
        else:
            return None


def start(loc, mode=None, channels=None):
    if loc is not '':
        print "Location specified as " + loc
    else:
        loc = "Hamburg, DE"
        print "Using default location " + loc
    win = JodelExtract()
    win.initialize(citycc=loc, mode=mode, initial_channels=channels)
    return win


if __name__ == '__main__':
    # The main routine

    print TOOLS.Config.SPLASH_TEXT

    loc = raw_input("Please specify the location (format: City, CC) >> ")

    if loc is not '':
        print "Location specified as " + loc
    else:
        loc = "Hamburg, DE"
        print "Using default location " + loc

    print """
    MODE SELECTION:
        1. Recent posts
        2. Most popular
        3. Most discussed
        4. Combination of 1-3
        5. Load Channel ["5 + channel name"]
        """
    modes = [TOOLS.Connection.PostType.ALL,
             TOOLS.Connection.PostType.POPULAR,
             TOOLS.Connection.PostType.DISCUSSED,
             TOOLS.Connection.PostType.COMBO]
    i = raw_input("What mode do you want to use? >> ")
    if i:
        i = i.split()
        x = int(i[0])-1
        print "\n#############################################################\n"
        if x <= 3:
            mode = modes[x]
            channels = None
        elif x == 4:
            # create session here?
            #channels = raw_input("What channels do you want to load? (separate by space) >> ").split()
            channels = []
            channels.append(i[1])
            mode = None
    else:
        mode = None
        channels = None

    win = JodelExtract()
    win.initialize(citycc=loc, mode=mode, initial_channels=channels)
    win.posts(mode=mode)
