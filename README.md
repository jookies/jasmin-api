# jasmin-api
Jasmin restful management API

##Settings

Requires local_settings.py in jasmin_api/jasmin_api
(same directory as settings.py) which should contain:

    DEBUG = False
    SECRET_KEY = '[some random string]'

By default a SQLite database will be used. You can use a different database by adding a [DATABASES setting](https://docs.djangoproject.com/en/1.8/ref/settings/#databases) to local_settings.py

You can also override the default settings for the telnet connection in local_settings.py. These settings with their defaults are:

TELNET_HOST = '127.0.0.1'
TELNET_PORT = 8990
TELNET_USERNAME = 'jcliadmin'
TELNET_PW = 'jclipwd'

##Installing

We recommend installing in a virtualenv

1. Install dependencies, checkout code.
2. cd to jasmin_api and run

    ./manage.py migrate
    ./manage.py createsuperuser

##Running

To run on production

    cd jasmin_api;run_cherrypy.py

which uses the production quality CherryPy WSGI server. Django's "manage.py runserver" will work but should be used only for testing, troubleshooting and development.

## Dependencies and requirements
* Python 2.7 required, use of virtualenv recommended
* A command line telnet client should be installed - this is a usual with Unix type OSes
* See requirements.txt for packages installable from pypi
* Optional: libyaml would improve performance of Django REST Swagger
