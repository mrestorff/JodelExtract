#!/usr/bin/env python2
# -*- coding: iso-8859-1 -*-

import json
import tempfile
from StringIO import StringIO
import array
import os
import shutil
import pprint
import argparse
import sys
import appdirs
import datetime
import requests
from time import gmtime, strftime
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

        self.posts_mode_dict = {}
        self.post_list = {}
        self.error_message = None

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

        # get local channels ordered by popularity
        if initial_channels is None:
            channels = self.connection.recommended_channels()
            if channels is not False:
                self.channel_list = sorted(channels['local'], key=lambda channel: channel['followers'], reverse=True)
            else:
                initial_channels = []

        self.channel_name_list = []
        for channel in self.channel_list:
            self.channel_name_list.append(channel['channel'])

        if mode is not None:
            self.posts_mode = mode

        #self.posts(mode=self.posts_mode) # => calls posts further down the code
        #self.my_posts()
        #self.my_replies()
        #self.my_voted_posts()
        #self.my_pinned_posts()

        return False


# ----------------------------------------------------------------------
# Post fetching methods
# ----------------------------------------------------------------------
    def posts(self, mode=None, after_post_id=None, post_data_dict=None):
        """ Fetch post data from API if post_data_dict not given. """

        if mode is None:
            #mode = self.posts_mode_dict[post_category_type.POSTS]
            mode = TOOLS.Connection.PostType.ALL

        # Fetch posts from the API if no data is supplied
        if post_data_dict is None:
            if mode == TOOLS.Connection.PostType.POPULAR or mode == "popular":
                post_data_dict = self.connection.popular_posts(after_post_id)
            elif mode == TOOLS.Connection.PostType.DISCUSSED or mode == "discussed":
                post_data_dict = self.connection.discussed_posts(after_post_id)
            elif mode == TOOLS.Connection.PostType.COMBO or mode == "combo":
                raw_post_data_dict = self.connection.combo_posts()
                post_data_dict = {'posts': sorted(raw_post_data_dict['replied'] +
                        raw_post_data_dict['voted'] +
                        raw_post_data_dict['recent'],key=timesort,reverse=True)}
            elif mode == TOOLS.Connection.PostType.ALL or mode == "recent":
                post_data_dict = self.connection.recent_posts(after_post_id)
            elif mode == "country": # TODO implement or delete function
                post_data_dict = self.connection.country_feed()
                print post_data_dict
            else:
                post_data_dict = self.connection.recent_posts(after_post_id)

        if post_data_dict is False:
            print "Error! Could not fetch post data."

        self.post_data_dict = post_data_dict

        if post_data_dict:
            temp_post_list = []
            for post in post_data_dict['posts']:
                if post['post_id'] in self.post_list:
                    p = self.post_list[post['post_id']]
                    p.update(post)
                else:
                    p = TOOLS.PostHandler.Post(post,self.tempdir,self,self.connection)
                    self.post_list[post['post_id']] = p
                # delete system messages
                if not p.system_message:
                    temp_post_list.append(p)
            first_post = temp_post_list[0]
            last_post = temp_post_list[len(temp_post_list)-1]
            return temp_post_list, first_post.id, last_post.id
        else:
            return [], post_data_dict, False


    def _open_channel(self, channel, mode=None, after_post_id=None, main=None, channel_data_dict=None):
        """ Load posts for channel or hashtag from API """

        if not channel in self.channel_name_list:
            return False

        if mode is None:
            mode = TOOLS.Connection.PostType.ALL

        # Fetch posts from the API if no data is supplied
        if mode == TOOLS.Connection.PostType.POPULAR or mode == "popular":
            channel_data_dict = self.connection.get_channel_popular(channel, after_post_id)
        elif mode == TOOLS.Connection.PostType.DISCUSSED or mode == "discussed":
            channel_data_dict = self.connection.get_channel_discussed(channel, after_post_id)
        elif mode == TOOLS.Connection.PostType.COMBO or mode == "combo":
            channel_data_dict = self.connection.get_channel(channel)
            raw_channel_data_dict = self.connection.get_channel(channel)
            channel_data_dict = {'posts': sorted(#raw_channel_data_dict['replied'] +
                    #raw_channel_data_dict['voted'] +
                    raw_channel_data_dict['recent'],key=timesort,reverse=True)}
        elif mode == TOOLS.Connection.PostType.ALL or mode == "recent":
            channel_data_dict = self.connection.get_channel_recent(channel, after_post_id)
        else:
            channel_data_dict = self.connection.get_channel_recent(channel, after_post_id)

        if channel_data_dict is False:
            return

        try:
            head = unicode(channel,errors='replace')
        except TypeError:
            head = channel
        s_unicode = head.decode("iso-8859-1")
        channel_utf8 = s_unicode.encode("utf-8")

        # Check if this channel has posts, and list them if yes
        channel_posts_list = channel_data_dict['posts']
        if channel_posts_list is not None and len(channel_posts_list) > 0:
            temp_post_list = []
            # critical channel handling
            critical_channels_utf8 = []
            critical_channels = ['körperselfie', 'sex', 'druffkultur', 'bettgeflüster']
            for item in critical_channels:
                s_unicode = item.decode("iso-8859-1")
                s_utf8 = s_unicode.encode("utf-8")
                critical_channels_utf8.append(s_utf8)
            if channel_utf8.lower() in critical_channels_utf8:
                print "Loading *critical* channel @" + channel + "\nBeware of explicit content!"
                time = datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S.%fZ')
                message = {"message":"Caution! This channel may contain explicit images and/or language, or indications of drug use.",
                "created_at":time,"updated_at":time,"pin_count":0,"color":"999999","got_thanks":"false",
                "thanks_count":0,"child_count":0,"replier":0,"post_id":"ChannelWarningMessage999",
                "discovered_by":0,"vote_count":0,"share_count":0,"user_handle":"oj","post_own":"team","distance":99,
                "location":{
                    "name":"Hamburg",
                    "loc_coordinates":{"lat":0,"lng":0},
                    "loc_accuracy":0,
                    "country":"DE",
                    "city":"Hamburg"
                }}
                p = TOOLS.PostHandler.Post(message,self.tempdir,self,self.connection,channel=channel)
                temp_post_list.append(p)
            else:
                print "Loading channel @" + channel

            for post in channel_posts_list:
                p = TOOLS.PostHandler.Post(post,self.tempdir,self,self.connection,channel=channel)
                temp_post_list.append(p)
                # inserting into permanent list as well
                self.post_list[post['post_id']] = p

            first_post = temp_post_list[0]
            last_post = temp_post_list[len(temp_post_list)-1]
            return temp_post_list, first_post.id, last_post.id


    def _open_post(self, post_id, main=None):
        """ Update original post and load comments from API """

        # Fetch posts from the API
        this_post = post = self.connection.particular_post(post_id)

        if this_post is None:
            print "Could not fetch " + post_id
            for post in self.post_data_dict['posts']:
                if post['post_id'] == post_id:
                    this_post = post
                    break
        elif this_post is False:
            return False, post_id
        else:
            pass

        this_post = this_post['details']
        # generate & update post object for original post
        temp_post_list = []
        if this_post['post_id'] in self.post_list:
            p = self.post_list[this_post['post_id']]
            p.update(this_post)
            #temp_post_list.append(p)
        else:
            p = TOOLS.PostHandler.Post(this_post,self.tempdir,self,self.connection)
            #temp_post_list.append(p)
            self.post_list[this_post['post_id']] = p

        children_posts_list = post.get('replies')
        response_index = 0
        comments_list = []
        if children_posts_list is not None and len(children_posts_list) > 0:
            for reply in children_posts_list:
                comments_list.append(TOOLS.PostHandler.Post(reply,self.tempdir,self,self.connection,reply=True))
        return comments_list, self.post_list[this_post['post_id']]

    def get_user_posts(self, user_id):
        post_list = []
        if user_id:
            for post in dict.values(self.post_list):
                if post.post['user_handle'] == user_id:
                    post_list.append(post)
            return post_list
        else:
            return None

    #------------------------------------------------------------
    # User information
    #------------------------------------------------------------
    def view_karma(self):
        return self.connection.karma()

    #------------------------------------------------------------
    # User interactions
    #------------------------------------------------------------
    def _share(self, post_id):
        share = self.connection.share(post_id)
        if share is not None and share is not False and share.get('url'):
            return share.get('url')
        else:
            return False

    def _vote(self, post_id, value):
        if value == 1:
            re = self.connection.upvote(post_id)
        else:
            re = self.connection.downvote(post_id)
        if re is not None:
            print "Voted " + post_id

    def _pin(self, post_id, value):
        if value == 1:
            re = self.connection.pin(post_id)
        else:
            re = self.connection.unpin(post_id)
        if re is not None:
            print "Pinned " + post_id


def start(loc, mode=None, channels=None):
    if loc is not '':
        print "Location specified as " + loc
    else:
        loc = "Hamburg, DE"
        print "Using default location " + loc
    win = JodelExtract()
    win.initialize(citycc=loc, mode=mode, initial_channels=channels)
    return win

# TODO: Get rid of text-based console interface
if __name__ == '__main__':
    print cfg.SPLASH_TEXT

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
            channels = []
            channels.append(i[1])
            mode = None
    else:
        mode = None
        channels = None

    win = JodelExtract()
    win.initialize(citycc=loc, mode=mode, initial_channels=channels)
    win.posts(mode=mode)
