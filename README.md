# jasmin-api
Jasmin restful management API

##Settings

Requires local_settings.py in jasmin_api/jasmin_api
(same directory as settings.py) which should contain:

    DEBUG = False
    SECRET_KEY = '[some random string]'

By default a SQLite database will be used. You can use a different database by adding a [DATABASES setting](https://docs.djangoproject.com/en/1.8/ref/settings/#databases) to local_settings.py

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

## Dependencies
See requirements.txt
optional libyaml would improve performance of Django REST Swagger
