import gevent
from gevent import monkey
monkey.patch_all()

import requests
import json
import time
import random
from pyquery import PyQuery as pq
from collections import namedtuple

import dabase
from dabase import Dabblet, DabChoice

API_URL = "http://en.wikipedia.org/w/api.php"
EDIT_SUMMARY = 'DAB link solved with disambiguity!'

class WikiException(Exception): pass

Page = namedtuple("Page", "title, req_title, pageid, revisionid, revisiontext, is_parsed, fetch_date")

DabOption = namedtuple("DabOption", "title, text, dab_title")

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
    
    try:
        resp.results = json.loads(resp.text)
        resp.servedby = resp.results.get('servedby')
        # TODO: warnings?
    except Exception as e:
        if raise_exc:
            raise
        else:
            resp.error = e
            return resp

    mw_error = resp.headers.get('MediaWiki-API-Error')
    if mw_error:
        error_str = mw_error
        error_obj = resp.results.get('error')
        if error_obj and error_obj.get('info'):
            error_str += ' ' + error_obj.get('info')
        if raise_exc:
            raise WikiException(error_str)
        else:
            resp.error = error_str
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


def get_articles(page_ids=None, titles=None, parsed=True, follow_redirects=False, **kwargs):
    ret = []
    params = {'prop':    'revisions',  
              'rvprop':  'content|ids' }

    if page_ids:
        if not isinstance(page_ids, (str,unicode)):
            try:
                page_ids = "|".join([str(p) for p in page_ids])
            except:
                pass
        params['pageids'] = str(page_ids)
    elif titles:
        if not isinstance(titles, (str,unicode)):
            try:
                titles = "|".join([unicode(t) for t in titles])
            except:
                print "Couldn't join: ",repr(titles)
        params['titles'] = titles
    else:
        raise Exception('You need to pass in a page id or a title.')

    if parsed:
        params['rvparse'] = 'true'
    if follow_redirects:
        params['redirects'] = 'true'

    parse_resp = api_req('query', params, **kwargs)
    if parse_resp.results:
        try:
            pages = parse_resp.results['query']['pages'].values()
            redirect_list = parse_resp.results['query'].get('redirects', [])
        except:
            print "Couldn't get_articles() with params: ", params
            return ret

        redirects = dict([ (r['to'],r['from']) for r in redirect_list ])
        # this isn't perfect since multiple pages might redirect to the same page
        for page in pages:
            title = page['title']
            pa = Page( title  = title,
                       req_title  = redirects.get(title, title),
                       pageid = page['pageid'],
                       revisionid = page['revisions'][0]['revid'],
                       revisiontext = page['revisions'][0]['*'],
                       is_parsed = parsed,
                       fetch_date = time.time())
            ret.append(pa)
    return ret


def is_fixable_dab_link(parsed_page):
    # Check for redirect
    # Check for hat notes
    pass


def get_dab_choices(dabblets): # side effect-y..
    ret = []
    if not dabblets:
        return ret
    dab_map = dict([(d.title, d) for d in dabblets])
    dab_pages = get_articles(titles=dab_map.keys(), follow_redirects=True)

    for dp in dab_pages:
        dabblet  = dab_map.get(dp.req_title) # :/ (worried about special characters)
        dab_text = dp.revisiontext
        
        d = pq(dab_text)
        if not d('table#disambigbox'):
            print dp.req_title, 'has no table#disambigbox, skipping.'
            #print '(pulled in from', dabblet.source_title,')'
            continue

        d('table#toc').remove()
        liasons = set([ d(a).parents('li')[-1] for a in d('li a') ])
        for lia in liasons:
            # TODO: better heuristic than ":first" link?
            title = d(lia).find('a:first').attr('title') 
            text = lia.text_content().strip()
            ret.append(DabChoice(dabblet=dabblet,
                                 title=title, 
                                 text=text))
    
    return ret


def get_context(dab_a):
    d = dab_a(dab_a.parents()[0])
    d(dab_a).addClass('dab-link')
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
            context = get_context(dab_link)

            ret.append( Dabblet.from_page(dab_title, 
                                          context.outerHtml(), 
                                          parsed_page, 
                                          i,
                                          '||'.join(images_found)))
            
    return ret

def get_random_dabblets(count=2):
    dabblets = []
    page_ids = random.sample(get_dab_page_ids(count=count*2), count)
    articles = get_articles(page_ids)
    dabblets.extend(sum([get_dabblets(a) for a in articles], []))
    return dabblets
'''
import re
def replace_nth(n, repl):
    def replace(match, c=[0]):
        c[0] += 1
        return repl if  c[0] == n else match.group(0)
    return replace

def replace_dablet(dabblet, guess):
    article_text = get_articles(page_id=dabblet.source_page['pageid'], parsed=False)
    dab_title = dabblet.title
    dab_postition = dabblet.source_order
    if article_text.revisionid === dabblet.source_page['revisionid']:
        return re.sub('\[\[' + title + '(.*){{Disambiguation needed.*}}, replace_nth(dab_postition, '[[' + guess + '\g<1>'), article_text.revisiontext)
    else:
        return 'error: the revids don't match'

def submit_solution(title, solution):
    params = {'action': 'edit',
            'format': 'json',
            'title': title,
            'text': solution,
            'summary': EDIT_SUMMARY,
            'token': '+\\'}
    resp = api_req('query', params)
    return resp
'''

P_PER_CALL = 4
DEFAULT_TIMEOUT = 30
def green_call_list(func, arglist, per_call=P_PER_CALL, timeout=DEFAULT_TIMEOUT):
    import time
    fname = func.__name__
    print 'calling', fname, 'on', len(arglist), 'items...'
    start = time.time()
    jobs = [gevent.spawn(func, arglist[i:i+per_call])
            for i in
            range(0, len(arglist), per_call)]
    print 'using', len(jobs), 'green threads.'
    gevent.joinall(jobs, timeout)
    done_jobs = [j for j in jobs if j.value]
    try:
        ret = sum([j.value for j in done_jobs], [])
    except TypeError as te:
        print '(', fname, "'s results appear to not be iterable)"
        ret = [ j.value for j in done_jobs ]

    print '(', len(done_jobs), 'out of', len(jobs), 'jobs returned, with', 
    print len(ret), 'results.)'
    dur = time.time() - start
    print 'done', fname, 'on', len(arglist), 'items in',
    print dur, 'seconds.'

    return ret

def save_a_bunch(count=1000):
    import time

    db_name = 'abunch'
    dabase.init(db_name)

    start = time.time()

    page_ids = get_dab_page_ids(count=count)
    pages    = green_call_list(get_articles, page_ids)
    dabblets = sum([ get_dabblets(p) for p in pages ], [])

    # TODO start transaction
    for d in dabblets:
        d.save()

    all_choices = green_call_list(get_dab_choices, dabblets)

    for c in all_choices:
        c.save()
    # TODO end transaction 
    end = time.time()

    print len(dabblets), 'Dabblets saved to', db_name, 'in', end-start, 'seconds'
    print len(set([d.title for d in dabblets])), 'unique titles'
    print len(set([d.source_title for d in dabblets])), 'unique source pages'
    print len(all_choices), 'dabblet choices fetched and saved.'

    print Dabblet.select().count(), 'total records in database'
    print len(set([d.title for d in Dabblet.select()])), 'unique titles in database'

    return dabblets

def test():
    print 'getting one article by ID'
    pid_article = get_articles(4269567, raise_exc=True)
    assert len(pid_article) > 0
    print 'getting one article by list of IDs (list of one)'
    pid_articles = get_articles([4269567], raise_exc=True)
    assert len(pid_articles) > 0

    title_article = get_articles(titles="Dog", raise_exc=True)
    title_articles = get_articles(titles=["Dog"], raise_exc=True)

if __name__ == '__main__':
    dabblets = save_a_bunch(50)
    import pdb;pdb.set_trace()
