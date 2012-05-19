import os
from datetime import datetime

import bottle
from bottle import route, run, request, response, static_file
#import bottle_jsonp

from dabnabbit import api_req, replace_dabblet
import dabase
from dabase import Dabblet, DabChoice, DabImage, DabSolution

bottle.debug(True)

STATIC_DIR = os.path.join(os.path.dirname(__file__), 'static')

ALL_DABBLETS = None # set on 
SESSIONS = {}

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

@route('/next/')
def next_dabblet():
    session_id = request.get_cookie('session_id')
    session = get_session(session_id)
    response.set_cookie('session_id', session['id'])

    cur_index = session.get('cur_index', 0)
    cur_id = session['seq'][cur_index]
    session['cur_index'] = cur_index + 1

    return { 'cur_index': cur_index,
             'total': len(session['seq']),
             'dabblet': Dabblet.get(id=cur_id).jsondict()
             }

def get_session(session_id=None):
    import random
    global SESSIONS
    if not session_id:
        session_id = str(random.randint(10**8, 10**13))
    session = SESSIONS.get(session_id, {'id': session_id})
    if not session.get('seq'):
        sequence = ALL_DABBLETS[:]
        random.shuffle(sequence)
        sequence.sort(key=lambda d: round(d[1], 1)) # difficulty
        session['seq'] = [ d[0] for d in sequence ]
    SESSIONS[session_id] = session
    return session

@route('/solve/', method='POST')
def solve_dabblet():
    session_id = request.get_cookie('session_id') #TODO: decorator-ify session
    session = get_session(session_id)
    response.set_cookie('session_id', session['id'])

    dabblet_id = int(request.POST['dabblet_id'])
    choice_id  = int(request.POST['choice_id'])

    dabblet = Dabblet.get(id=dabblet_id)
    if choice_id < 0:
        choice = None
    else:
        choice  = DabChoice.get(id=choice_id)

    sol = DabSolution(dabblet=dabblet,
                      choice=choice,
                      solver_ip=request.get('REMOTE_ADDR'),
                      solver_index=session.get('cur_index', 0),
                      date_solved=datetime.now())
    sol.save()
    # replace?
    return { 'hello stephen': "it's 2:37AM and your request succeeded" }
    
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
    ALL_DABBLETS = [ (d.id, d.priority) for d in Dabblet.select(['id','priority']) ]
    app = SlashMiddleware(bottle.app())
    run(app=app, host='0.0.0.0', port=8080, server='gevent')
