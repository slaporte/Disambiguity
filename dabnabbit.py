import gevent
import socket
from gevent import monkey
monkey.patch_all()

import requests
import json
import time
import random
from pyquery import PyQuery as pq

# stupid ipy notebook

from collections import namedtuple

API_URL = "http://en.wikipedia.org/w/api.php"

class WikiException(Exception): pass

Page = namedtuple("ParsedPage", "pageid, title, revisionid, revisiontext, is_parsed, fetch_date")

DabOption = namedtuple("DabOption", "title, text, dab_title")

class Dabblet(object):
    def __init__(self, title, context, source_page, page_attr, source_order):
        self.title        = title
        self.context      = context
        self.source_page  = source_page
        self.page_title   = page_attr['title']
        self.images       = page_attr['images']
        self.source_order = source_order
        self.options = get_dab_options(title)
    def _asdict(self):
        return {'title': self.title,
                'context': self.context,
                'page_title': self.page_title,
                'options': [ o._asdict() for o in self.options ],
                'images': self.images,
                }

def api_req(action, params=None, raise_exc=False, **kwargs):
    all_params = {'format': 'json',
                  'servedby': 'true'}
    all_params.update(kwargs)
    all_params.update(params)
    all_params['action'] = action
    
    resp = requests.Response()
    resp.results = None
    try:
        if action == 'edit':
            resp = requests.post(API_URL, params=all_params)
        else:
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


def get_category(cat_name, count=500):
    params = {'list': 'categorymembers', 
              'cmtitle': 'Category:'+cat_name, 
              'prop': 'info', 
              'cmlimit': count}
    return api_req('query', params)
    
def get_dab_page_ids(date=None, count=500):
    cat_res = get_category("Articles_with_links_needing_disambiguation_from_June_2011", count)
    # TODO: Continue query?
    # TODO: Get subcategory of Category:Articles_with_links_needing_disambiguation
    return [ a['pageid'] for a in 
             cat_res.results['query']['categorymembers'] ]


def get_articles(page_id=None, title=None, parsed=True, follow_redirects=False):
    ret = []
    params = {'prop':    'revisions',  
              'rvprop':  'content|ids' }

    if page_id:
        if not isinstance(page_id, (str,unicode)):
            try:
                page_id = "|".join([str(p) for p in page_id])
            except:
                pass
        params['pageids'] = str(page_id)
    elif title:
        params['titles'] = title
    else:
        raise Exception('You need to pass in a page id or a title.')
    if parsed:
        params['rvparse'] = 'true'
    if follow_redirects:
        params['redirects'] = 'true'

    parse_resp = api_req('query', params)
    if parse_resp.results:
        ret = [Page( pageid = page['pageid'],
                     title  = page['title'],
                     revisionid = page['revisions'][0]['revid'],
                     revisiontext = page['revisions'][0]['*'],
                     is_parsed = parsed,
                     fetch_date = time.time())
               for page in parse_resp.results['query']['pages'].values()]
    return ret


def is_fixable_dab_link(parsed_page):
    # Check for redirect
    # Check for hat notes
    pass


def get_dab_options(dab_page_title):
    ret = []
    dab_page = get_articles(title=dab_page_title, follow_redirects=True)[0]
    dab_text = dab_page.revisiontext
    
    d = pq(dab_text)
    d('table#toc').remove()
    liasons = set([ d(a).parents('li')[-1] for a in d('li a') ])
    for lia in liasons:
        # TODO: better heuristic than ":first" link?
        title = d(lia).find('a:first').attr('title') 
        text = lia.text_content().strip()
        ret.append(DabOption(title, text, dab_page.title))
    
    return ret


def get_context(dab_a):
    d = dab_a(dab_a.parents()[0])
    link_parents = dab_a.parents()
    cand_contexts = [ p for p in link_parents 
                      if p.text_content() and len(p.text_content().split()) > 30 ]
    chosen_context = cand_contexts[-1]
    d(chosen_context).addClass('dab-context')
    # add upperbound/wrapping div
    return d(chosen_context)
    
def get_dabblets(parsed_page):
    "Call with a Page object, the type you'd get from get_articles()"
    ret = []
    d = pq(parsed_page.revisiontext)
    page_title = parsed_page.title

    images_found = [img.attrib['src'] for img in d('.thumbimage')][:3]
    page_attr = {'title': page_title,
                'images': images_found
                }

    dab_link_markers = d('span:contains("disambiguation needed")')
    for i, dlm in enumerate(dab_link_markers):
        try:
            dab_link = d(dlm).parents("sup")[0].getprevious() # TODO: remove extra d?
            dab_link = d(dab_link)
        except Exception as e:
            print 'nope', e
            continue
        if dab_link.is_('a'):
            dab_title = dab_link.attr('title')
            d(dab_link).addClass('dab-link')
            context = get_context(dab_link)
            ret.append( Dabblet(dab_title, context.outerHtml(), d.html(), page_attr, i) )
            
    return ret

def get_random_dabblets(count=2):
    dabblets = []
    page_ids = random.sample(get_dab_page_ids(count=count), count)
    articles = get_articles(page_ids)
    dabblets.extend(sum([get_dabblets(a) for a in articles], []))
    return dabblets