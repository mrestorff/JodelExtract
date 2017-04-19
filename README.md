# Readme #

JodelExtract is a Flask-based web app for the Jodel API. Curently, it can display  
posts from the timeline and all channels in a read-only mode. Soon though,  
it will enable the user to interact with the server as well, meaning the user can  
vote, write, and pin posts.
This is **not** an official Jodel app.

### Prerequisites

* Python
* `python-requests`
* `python-appdirs`
* `python-shutil`
* `python-enum34`
* `python-keyring`
* `python-dateutil`
* `python-flask`

## Using JodelExtract

1. Start via command line / terminal `python web.py`, the webbrowser is opened automatically
2. Enter location in the format "City, CC" (e.g. Hamburg, DE). If that city can't be found, your current IP-based position will be used
3. The latest posts will be loaded, click on posts to see the comments
  1. Use links in navigation bar to list the most liked, or most discussed posts from your location
4. All the available channels at your current location can be used as well.  
  [Note: the channel feature is only active in some locations, mostly those with a large user base.]

### Command line options

Despite `web.py` being a web app, the following command line options are supported:
```
usage: web.py [-h] [-i] [-p] [-l CITY,CC] [-m {read,write}] [-d] [-v]

optional arguments:
  -h, --help            show this help message and exit

AppSettings:
  application settings and options
  -i, --store_images    store images in temp folder
  -p, --store_posts     store posts in database [UNAVAILABLE]
  -l CITY,CC, --location CITY,CC    
                        a location, e.g. Hamburg,DE (without spaces!)
  -m {read,write}, --mode {read,write}
                        choose read-only or write mode (default: read)

Debugging:
    -d, --debug         activate Flask debugging mode
    -v, --verbose       print connection handling to command line
```

#### Credits

The HMAC secret decryption and authorisation with the server are courtesy of Christian Fibich's project OJOC.
