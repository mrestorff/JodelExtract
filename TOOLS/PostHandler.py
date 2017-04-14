#!/usr/bin/env python2
import re
import requests
import os.path
import datetime
import unicodedata
import TOOLS.prettytime as prettytime
import TOOLS.Config as cfg
import urlparse, urllib

def print_verbose(message):
    if cfg.VERBOSE:
        print message

class Post(object):
    def __init__(self,post,tempdir,main_window,connection,channel=False,userno=None,reply=False):
        """ post        Post data
            tempdir     Directory for downloaded images
            main_window Reference to main window
            connection  server connection from connection.py
            userno      Number of user in post
            reply       Flag if this is an original post (False) or a reply (True)"""

        self.post = post
        self.id = post.get('post_id')
        self.tempdir = tempdir
        self.main_window = main_window
        self.connection = connection
        self.reply = reply

        # Workaround for API not returning child_count
        if not self.reply and not 'child_count' in self.post.keys():
            print "NO child_count FOUND IN DICT! \n"
            print post
            self.post['child_count'] = 0

        # format post message (removing newlines)
        self.post['message'] = self.strip_empty_lines(post['message'])

        # mark post from Jodel Team
        if self.post['post_own'] == "team":
            self.system_message = True
        else:
            self.system_message = False

        if reply:
            print_verbose("Handling comment " + post['post_id'])
            if post['user_handle'].lower() == "oj":
                self.by_oj = True
                self.replier = 0
            else:
                self.replier = post['replier']
        else:
            print_verbose("Handling post " + post['post_id'])

        # create color hex code
        colorspec = {'#06A3CB':'blue', '#8ABDB0':'turquoise', '#9EC41C':'green', '#DD5F5F':'red', '#FF9908':'orange', '#FFBA00':'yellow'}
        if post['color']:
            self.color = colorspec.get('#' + post['color'], 'grey')

        image_url = post.get('image_url')
        if (image_url is None):
            pass
        elif not cfg.DBG_NO_IMAGES:
            # Download the image into the temp folder (if not yet downloaded)
            image_headers = post.get('image_headers')
            if not channel:
                path = os.path.join(self.tempdir, post['post_id'] + ".jpg")
            else:
                folder_path = os.path.join(self.tempdir, channel)
                if not os.path.exists(folder_path):
                    os.makedirs(folder_path)
                path = os.path.join(folder_path, post['post_id'] + ".jpg")
            if not (os.path.exists(path) and os.path.isfile(path)):
                print_verbose("Downloading image https:" + image_url + "... ")
                try:
                    with open(path, 'wb') as handle:
                        if (image_headers is not None):
                            r = connection.imgsession.request('GET', 'https:' + image_url, headers=image_headers)
                        else:
                            r = connection.imgsession.request('GET', 'https:' + image_url)

                        if not r.ok:
                            print_verbose("Could not get image.")

                        for block in r.iter_content(1024):
                            handle.write(block)

                except requests.exceptions.ConnectionError as e:
                    print "failed: " + str(e)
        self.image_url = image_url

        #self.save_post()
        if cfg.DEBUG:
            print post
        self.get_data()

    def get_data(self):
        self.named_distance = named_distance(self.post['distance'])
        date = datetime.datetime.strptime(self.post['created_at'], '%Y-%m-%dT%H:%M:%S.%fZ')
        self.date = date.strftime('%Y-%m-%d at %H:%M:%S')
        self.timedelta = prettytime.pretty(self.post['created_at'])

    def get_hashtags(self):
        hashtags = re.findall(r"#(\w+)", self.post['message'])
        print_verbose("Found hashtags " + str(hashtags))
        if hashtags:
            return hashtags
        else:
            return None

    def update(self, new_post):
        self.post = new_post
        self.get_data()
        if not self.reply and not 'child_count' in self.post.keys():
            self.post['child_count'] = 0
        return True

    def save_post(self):
        """ Saves post in CSV file """
        filename = self.tempdir + '\posts_' + self.connection.get_location_string() + '.csv'

        if os.path.isfile(filename) is not False:
            # write to file
            with open(filename, 'ab') as f:
                pickle.dump(self.post, f)
                # do this with csv files
        else:
            f = open(filename,'w+')
        try:
            for line in f:
                print line
        except:
            print "File empty!"
            print self.post

        print_verbose("Saving post " + self.post['post_id'] + " to " + filename)

    def print_post(self):
        date = datetime.datetime.strptime(self.post['created_at'], '%Y-%m-%dT%H:%M:%S.%fZ')
        date = date.strftime('%Y-%m-%d at %H:%M:%S')
        print ""
        print " ######## VOTES: "+str(self.post['vote_count'])+" #### DISTANCE: "+named_distance(self.post['distance'])+" #### CREATED AT: "+date+" ########"
        print unicodedata.normalize('NFKD', self.post['message']).encode('ascii', 'ignore') + "\n\n"

    def strip_empty_lines(self, s):
        lines = s.splitlines()
        while lines and not lines[0].strip():
            lines.pop(0)
        while lines and not lines[-1].strip():
            lines.pop()
        return '\n'.join(lines)


def named_distance(distance):
    if (distance < 2):
        return "very near"
    elif (distance < 15):
        return "near"
    else:
        return "remote"
