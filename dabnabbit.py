# -*- coding: utf-8 -*-
# <nbformat>2</nbformat>

# <codecell>

#import gevent

import requests
import json
from pyquery import PyQuery as pq

from collections import namedtuple

API_URL = "http://en.wikipedia.org/w/api.php"

# <codecell>

class WikiException(Exception): pass

def api_get(action, params=None, raise_exc=False, **kwargs):
    all_params = {'format': 'json',
                  'servedby': 'true'}
    all_params.update(kwargs)
    all_params.update(params)
    all_params['action'] = action
    
    resp = requests.Response()
    resp.results = None
    try:
        resp = requests.get(API_URL, params=all_params)
    except Exception as e:
        if raise_exc:
            raise
        else:
            resp.error = e
            return resp
    
    mw_error = resp.headers.get('MediaWiki-API-Error')
    if mw_error:
        if raise_exc:
            raise WikiException(mw_error)
        else:
            resp.error = mw_error
            return resp    
    
    try:
        resp.results = json.loads(resp.text)
    except Exception as e:
        if raise_exc:
            raise
        else:
            resp.error = e
            return resp
    
    return resp

# <codecell>

def get_category(cat_name, count=500):
    params = {'list': 'categorymembers', 
              'cmtitle': 'Category:'+cat_name, 
              'prop': 'info', 
              'cmlimit': count}
    return api_get('query', params)
    
def get_dab_page_ids(date=None):
    cat_res = get_category("Articles_with_links_needing_disambiguation_from_June_2011")
    # TODO: Continue query?
    # TODO: Get subcategory of Category:Articles_with_links_needing_disambiguation
    return [ a['pageid'] for a in 
             cat_res.results['query']['categorymembers'] ]

get_dab_page_ids()

# <codecell>

def get_article_parsed(page_id=None, title=None): #TODO: support lists
    params = {'action':  'query',
              'prop':    'revisions', 
              'rvparse': 'true', 
              'rvprop':  'content|ids', 
              'format':  'json' }

    if page_id:
        if type(page_id)==type(list()):
            page_id = "|".join(map(str, page_id))

        params['pageids'] = page_id
    elif title:
        params['titles'] = title
    else:
        raise Exception('You need to pass in a page id or a title.')
        
    try:
        a_json = requests.get(API_URL, params=params).text
        pages = json.loads(a_json)['query']['pages'].values()
    except Exception as e:
        raise
    return [{'pageid': page['pageid'], 'title': page['title'], 'revisionid': page['revisions'][0]['revid'], 'revisiontext': page['revisions'][0]['*']} for page in pages]

#article_parsed = get_article_parsed(tmp_ids[0])

# <codecell>

def is_fixable_dab_link(parsed_page):
    # Check for redirect
    # Check for hat notes
    pass

# TODO: find context
def find_dab_links(parsed_page):
    ret = []
    d = pq(parsed_page)
    
    dab_link_markers = d('span:contains("disambiguation needed")')
    for dlm in dab_link_markers:
        try:
            dab_link = d(dlm).parents("sup")[0].getprevious() # TODO: remove extra d?
        except Exception as e:
            print 'nope', e
            continue

        if dab_link.tag == 'a':
            ret.append(dab_link.text)
            
    return ret

# <codecell>

DabOption = namedtuple("DabOption", "title, text, dab_title")

def get_dab_options(dab_page_title):
    ret = []
    parsed_dab_page = get_article_parsed(title=dab_page_title)[0]['revisiontext']
    
    d = pq(parsed_dab_page)
    liasons = d('li:contains(a)')

    for lia in liasons:
        # TODO: better heuristic than ":first" link?
        # URL decode necessary? special character handlin'
        title = d(lia).find('a:first').attr('href').split('/')[-1] 
        text = lia.text_content().strip()
        ret.append(DabOption(title, text, dab_page_title))
    
    return ret

# <codecell>

import random

class Dabblet(object):
    def __init__(self, sample=10):
        self.range = random.sample(z.get_dab_page_ids(), 3)
        

# <codecell>

get_dab_options('Born to Lose')
