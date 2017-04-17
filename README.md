# Readme #

1. Start via command line "python web.py"
2. Enter location in the format "City, CC" (e.g. Hamburg, DE). If that city can't be found, your current IP-based position will be used
3. Latest posts will be loaded, click on posts to see the comments
4. Use links in navigation bar to list the most liked, or most discussed posts from your location

### Command line options

To directly go to a specific location, you can use the command line commands.
```
$ python web.py [-h] [-l CITY, CC]
  -h, --help          Show this help message and exit
  -l CITY, CC, --location CITY, CC    
                      A location, e.g. Hamburg, DE
  -m, --mode          Choose write or read mode
```

## Prerequisites ##

* Python
* `python-requests`
* `python-appdirs`
* `python-shutil`
* `python-enum34`
* `python-keyring`
* `python-dateutil`
* `python-flask`
