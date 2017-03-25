import TOOLS.prettytime as prettytime
import requests
import os.path
import cPickle as pickle

VERBOSE = False # print to command line

def print_verbose(message):
    if VERBOSE:
        print message

class Post(object):
    def __init__(self,post,tempdir,main_window,connection,userno=None,reply=False):
        """ post        Post data
            tempdir     Directory for downloaded images
            main_window Reference to main window
            connection  server connection from connection.py
            userno      Number of user in post
            reply       Flag if this is an original post (False) or a reply (True)"""

        self.post = post
        self.tempdir = tempdir
        self.main_window = main_window
        self.connection = connection
        self.reply = reply
        print_verbose(" # # # # ")
        print_verbose("Handling post " + post['post_id'])

        # create color hex code
        self.color = '#' + post['color']
        if not self.color:
            self.color = None

        #self.save_post()
        self.print_post()

    def save_post(self):
        filename = self.tempdir + '\posts_' + self.connection.get_location_string() + '.txt'

        if os.path.isfile(filename) is not False:
            # write to file
            with open(filename, 'ab') as f:
                pickle.dump(self.post, f)
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
        print ""
        print " ######## VOTES: "+str(self.post['vote_count'])+" #### DISTANCE: "+named_distance(self.post['distance'])+" #### CREATED AT: "+self.post['created_at']+" ########"
        print self.post['message'].encode('ascii', 'ignore')


def named_distance(distance):
    if (distance < 2):
        return "very near"
    elif (distance < 15):
        return "near"
    else:
        return "remote"
