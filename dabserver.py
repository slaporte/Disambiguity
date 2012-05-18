import bottle
from bottle import route, run, request, response
import bottle_jsonp

from peewee import R

from dabnabbit import api_req, replace_dabblet
import dabase
from dabase import Dabblet, DabChoice, DabImage, DabSolution

bottle.debug(True)

# TODO: sequencing/session/"next"

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

if __name__ == '__main__':
    dabase.init('abunch')
    print get_random_dabblet()
    run(host='0.0.0.0', port=8080, server='gevent')
