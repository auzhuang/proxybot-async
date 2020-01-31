#! /usr/bin/python
#-*- coding: utf-8 -*-

from sanic import Sanic
from main import *
import config


app = Sanic('webproxy')


app.add_route(HTML_Index.as_view(), '/')
app.add_route(HTML_Sites.as_view(), '/sites.htm')
app.add_route(Block.as_view(), '/block')
app.add_route(SaveGAEOlderLink.as_view(), '/cc/<path:path>')
app.add_route(globals()[config.EnabledWebProxy].as_view(), '/<path:path>')

app.run(host="127.0.0.1", debug=True, access_log=False, port=9000, workers=2)
