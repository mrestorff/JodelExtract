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
#from PIL import Image
import TOOLS.Connection
import TOOLS.PostHandler
import requests

# enable utf8
reload(sys)
sys.setdefaultencoding('utf8')

APP_NAME = "JodelExtract"
APP_AUTHOR = "MR"

def timesort(post):
    """Returns post's post ID as an int for sorting"""
    return int(post['post_id'], 16)

#class post_category_type(enum.Enum):
#    """Enumerate the types of page container widgets """
#    MY_POSTS     = 1
#    VOTED_POSTS  = 3
#    MY_REPLIES   = 5
#    POSTS        = 7
#    CHANNEL      = 9
#    PINNED_POSTS = 11

#post_category_titles = {post_category_type.MY_POSTS:     'My Posts',
#                        post_category_type.VOTED_POSTS:  'My Voted Posts',
#                        post_category_type.PINNED_POSTS: 'My Pinned Posts',
#                        post_category_type.MY_REPLIES:   'My Replies',
#                        post_category_type.POSTS:        'Posts'}

menu_entry_titles={TOOLS.Connection.PostType.POPULAR: 'Popular',
                   TOOLS.Connection.PostType.DISCUSSED: 'Discussed',
                   TOOLS.Connection.PostType.COMBO:'Combo'}

class JodelExtract():
    """ The main window class """

    def __init__(self, recent_posts=None):
        try:
            self.tempdir = appdirs.user_cache_dir(APP_NAME,APP_AUTHOR)
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

    def initialize(self, citycc=None, location=None, initial_channels=None):
        """Set up the connection to Jodel, load the content of the
           default tabs
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

        self.posts(mode=self.posts_mode) # => calls posts further down the code
        #self.my_posts()
        #self.my_replies()
        #self.my_voted_posts()
        #self.my_pinned_posts()
        #for initial_channel in initial_channels:
        #   self._open_channel(self,initial_channel)
        return False

    def reload(self, widget, data):
        """Reloads the data in the currently raised notebook page, which is
           referred to by its numerical index given to it by the Notebook widget.

           widget and data are parameters required for callbacks but are
           ignored"""
        reload_function = self.reload_function_dict[self.notebook.get_current_page()]

        if reload_function is not None:
            reload_function[0](*reload_function[1])
        self.clean_tempdir()

    def view_karma(self, widget, data):
        """ This method opens a dialog which shows the user's current karma.
            The karma value is fetched from the API

           widget and data are parameters required for callbacks but are
           ignored"""
        reply = self.connection.karma()

        if self.debugDialog is not None:
            self.debugDialog.update('=== Karma ===\n' + pprint.pformat(reply) + '\n')
        if reply is not None:
            dialog = Gtk.MessageDialog(self,Gtk.DialogFlags.DESTROY_WITH_PARENT,Gtk.MessageType.INFO,Gtk.ButtonsType.CLOSE,'Karma: ' + str(reply['karma']))
            dialog.run()
            dialog.destroy()


# ----------------------------------------------------------------------
# Methods for updating notebook tabs with posts
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
            if mode == TOOLS.Connection.PostType.POPULAR:
                post_data_dict = self.connection.popular_posts()
            elif mode == TOOLS.Connection.PostType.DISCUSSED:
                post_data_dict = self.connection.discussed_posts()
            elif mode == TOOLS.Connection.PostType.COMBO:
                raw_post_data_dict = self.connection.combo_posts()
                post_data_dict = {'posts': sorted(raw_post_data_dict['replied'] +
                        raw_post_data_dict['voted'] +
                        raw_post_data_dict['recent'],key=timesort,reverse=True)}
            else:
                post_data_dict = self.connection.get_combo()

        if post_data_dict is False:
            print "Error! Could not fetch post data."

        self.post_data_dict = post_data_dict

        #if self.debugDialog is not None:
        #    self.debugDialog.update('=== Posts ===\n' + pprint.pformat(post_data_dict) + '\n')

        # get page widget
        #page_container_widget, tab_number = self._new_tab_container((self.posts,[None]),
                                                                    #post_category=post_category_type.POSTS,
                                                                    #menu_entries=[TOOLS.Connection.PostType.COMBO,
                                                                    #              TOOLS.Connection.PostType.POPULAR,
                                                                    #              TOOLS.Connection.PostType.DISCUSSED])


        #notebook_page = self._get_clear_notebook_page_grid(page_container_widget)
        #print "Post count: " + len(post_data_dict['posts'])
        if post_data_dict:
            debug = False
            if debug == False:
                self.post_list = []
                #try:
                for post in post_data_dict['posts']:
                    p = TOOLS.PostHandler.Post(post,self.tempdir,self,self.connection)
                    self.post_list.append(p)
                #except:
                #    print post_data_dict
                #post = self.post_list[5]
                #print post
                #print post.post
                #print post.post['distance']

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


if __name__ == '__main__':
    # The main routine

    print TOOLS.Config.SPLASH_TEXT

    loc = raw_input("Please specify the location (format: City, CC): ")

    if loc is not '':
        print "Location specified as " + loc
    else:
        loc = "Hamburg, DE"
        print "Using default location " + loc

    win = JodelExtract()
    win.initialize(citycc=loc)
