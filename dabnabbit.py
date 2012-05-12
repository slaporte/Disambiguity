#import gevent

import requests
import json

import pyquery

API_URL = "http://en.wikipedia.org/w/api.php"

def get_dab_page_ids(date=None):
    params = {'action': 'query', 
              'list': 'categorymembers', 
              'cmtitle': 'Category:Articles_with_links_needing_disambiguation_from_June_2011', 
              'prop': 'info', 
              'cmlimit': '500', 
              'format': 'json'}
    try:
        a_list_json = requests.get(API_URL, params=params).text
    except Exception as e:
        # TODO: Connection error
        raise
    # TODO: Continue query?
    return [ a['pageid'] for a in 
             json.loads(ARTICLE_LIST_URL)['query']['categorymembers'] ]

def get_article_parsed(page_id):
    params = {'action':  'query',
              'prop':    'revisions', 
              'rvparse': 'true', 
              'pageids':  page_id,
              'rvprop':  'content|ids', 
              'format':  'json' }
    return
