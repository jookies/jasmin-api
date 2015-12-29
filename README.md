# jasmin-api
Jasmin restful management API

##Installation

Requires local_settings.py in jasmin_api/jasmin_api
(same directory as settings.py) which should contain:

    DEBUG = False
    SECRET_KEY = '[some random string]'

To run on production

    cd jasmin_api;run_cherrypy.py

which uses the production quality CherryPy WSGI server. Django's manage.py runserver will work but should be used only for development.

## Dependencies
See requirements.txt
option libyaml would improve performance of Django REST Swagger
