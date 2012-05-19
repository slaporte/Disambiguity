import os

import bottle
from bottle import route, run, request, response, static_file
#import bottle_jsonp

from dabnabbit import api_req, replace_dabblet
import dabase
from dabase import Dabblet, DabChoice, DabImage, DabSolution

bottle.debug(True)

# TODO: sequencing/session/"next"

STATIC_DIR = os.path.join(os.path.dirname(__file__), 'static')

@route('/')
@route('/<path:path>')
def home_path(path="index.html"):
    return static_file(path, root=STATIC_DIR)

@route('/get/')
def get_dabblet():
    dab_id = request.GET.get('id')
    if dab_id:
        ret = Dabblet.get(id=int(dab_id))
    else:
        ret = Dabblet.select().order_by('priority').limit('1').get()
    
    return ret.jsondict()

@route('/random/')
def get_random_dabblet():
    rdabs = Dabblet.select().order_by("RANDOM()").limit(2)
    
    return { 'dabs': [ d.jsondict() for d in rdabs ] }

class SlashMiddleware(object):
    def __init__(self, app):
        self.app = app
    def __call__(self, e, h):
        e['PATH_INFO'] = e['PATH_INFO'].rstrip('/')+'/'
        return self.app(e,h)

if __name__ == '__main__':
    dabase.init('abunch')
    app = SlashMiddleware(bottle.app())
    run(app=app, host='0.0.0.0', port=8080, server='gevent')
