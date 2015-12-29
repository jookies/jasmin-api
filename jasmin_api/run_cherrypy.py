#!/usr/bin/env python

from jasmin_api.wsgi import application

from django.conf import settings

import cherrypy

cherrypy.tree.graft(application, "/")

server = cherrypy._cpserver.Server()

server.socket_host = "0.0.0.0"
server.socket_port = 8001
server.thread_pool = 10

server.subscribe()

cherrypy.engine.start()
cherrypy.engine.block()
