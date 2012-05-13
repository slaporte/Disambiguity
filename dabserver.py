import bottle
from bottle import route, run
import dabnabbit

bottle.debug(True)

@route('/prepare/')
def preapre_dab():
    dabs = dabnabbit.get_random_dabblets()
    return {'dabs': dabs}

run(host='localhost', port=8080, reloader=True)