import gevent
from gevent.pool import Pool
from gevent import monkey
monkey.patch_all()

import itertools
import requests
import json
import time
import random
from optparse import OptionParser
from pyquery import PyQuery as pq
from collections import namedtuple

import dabase
from dabase import Dabblet, DabChoice, DabImage

from progress import ProgressMeter

API_URL = "http://en.wikipedia.org/w/api.php"
DEFAULT_CAT = "Articles_with_links_needing_disambiguation"
DEFAULT_LIMIT = 100
DEFAULT_CONC  = 100
DEFAULT_PER_CALL = 4
DEFAULT_TIMEOUT = 30
DEFAULT_DB = 'dab_store'
CAT_CONC = 10
ALL = 20000


EDIT_SUMMARY = 'DAB link solved with disambiguity!'



class WikiException(Exception): pass

Page = namedtuple("Page", "title, req_title, pageid, revisionid, revisiontext, is_parsed, fetch_date")

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
            resp.results = None
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
            resp.results = None
            resp.servedby = None
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

CategoryMember = namedtuple("CategoryMember", "pageid, ns, title")
def get_category(cat_name, count=500, cont_str=""):
    ret = []
    if not cat_name.startswith('Category:'):
        cat_name = 'Category:'+cat_name
    while len(ret) < count and cont_str is not None:
        cur_count = min(count - len(ret), 500)
        params = {'list':       'categorymembers', 
                  'cmtitle':    cat_name, 
                  'prop':       'info', 
                  'cmlimit':    cur_count,
                  'cmcontinue': cont_str}
        resp = api_req('query', params)
        try:
            qres = resp.results['query']
        except:
            # print resp.error # log
            break
        ret.extend([ CategoryMember(pageid=cm['pageid'],
                                    ns    =cm['ns'],
                                    title =cm['title'])
                     for cm in qres['categorymembers']
                     if cm.get('pageid') ])
        try:
            cont_str = resp.results['query-continue']['categorymembers']['cmcontinue']
        except:
            cont_str = None

    return ret

def get_category_recursive(cat_name, count=None):
    ret = set()
    seen_cats = set()

    if count is None:
        count = ALL
        print 'Recursively getting all members of', cat_name
    else:
        print 'Recursively getting',count,'members of', cat_name

    jobs = []
    api_pool = Pool(CAT_CONC)
    jobs.append(api_pool.spawn(get_category, cat_name, count))
    dpm = ProgressMeter(total=count, unit="categories", ticks=30)
    while len(ret) < count and jobs:
        cur_count = count - len(ret)
        api_pool.join(timeout=0.3, raise_error=True)
        for j in jobs:
            if not j.ready():
                continue
            jobs.remove(j)
            if not j.successful():
                print 'failed a cat fetch'
                continue
            cur_mems = j.value
            for m in cur_mems:
                if m.ns == 14:
                    if m.title not in seen_cats:
                        jobs.append(api_pool.spawn(get_category, m.title, cur_count))
                        seen_cats.add(m.title)
                else:
                    ret.add(m)
                    dpm.update(1)

    dpm.update(count - len(ret))
    
    ret = list(ret)[:count]
    print 'Done, returning', len(ret),'category members.'
    return list(ret)

def get_dab_page_ids(category=DEFAULT_CAT, count=500):
    cat_res = get_category_recursive(category, count)
    return [ a.pageid for a in cat_res ]


def get_articles(page_ids=None, titles=None, parsed=True, follow_redirects=False, **kwargs):
    ret = []
    params = {'prop':   'revisions',  
              'rvprop': 'content|ids' }

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
            if not page.get('pageid') or not page.get('title'):
                continue
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
            #print 'Article "'+dp.req_title+'" has no table#disambigbox, skipping.'
            #print '(pulled in from', dabblet.source_title,')'
            continue

        d('table#toc').remove()
        liasons = set([ d(a).parents('li')[-1] for a in d('li a') ])
        for lia in liasons:
            # TODO: better heuristic than ":first" link?
            title = d(lia).find('a:first').attr('title') 
            text = lia.text_content().strip()
            if title and text:
                ret.append(DabChoice(dabblet=dabblet,
                                     title=title, 
                                     text=text))
            #else:
            #    print 'skippin a bogus link'
    
    return ret


def get_context(dab_a):
    d = dab_a(dab_a.parents()[0])
    d(dab_a).addClass('dab-link')
    link_parents = dab_a.parents()
    cand_contexts = [ p for p in link_parents 
                      if getattr(p, "text_content", lambda: False)()
                      and len(p.text_content().split()) > 30 ]
    chosen_context = cand_contexts[-1]
    d(chosen_context).addClass('dab-context')
    # add upperbound/wrapping div
    return d(chosen_context)

def get_dabblets(parsed_page):
    "Call with a Page object, the type you'd get from get_articles()"
    ret = []
    d = pq(parsed_page.revisiontext)
    page_title = parsed_page.title

    images_found = [img.attrib['src'] 
                    for img in d('img.thumbimage')
                    if img.attrib.get('src')][:3]

    dab_link_markers = d('span:contains("disambiguation needed")')
    for i, dlm in enumerate(dab_link_markers):
        try:
            dab_link = d(dlm).parents("sup")[0].getprevious() # TODO: remove extra d?
            dab_link = d(dab_link)
            if dab_link.is_('a'):
                dab_title = dab_link.attr('title')
                context = get_context(dab_link)
                ctx_html = context.outerHtml()
                ret.append( Dabblet.from_page(title        = dab_title, 
                                              context      = ctx_html, 
                                              source_page  = parsed_page, 
                                              source_order = i,
                                              source_imgs  = images_found))
        except Exception as e:
            print 'nope', e
            pass
            
    return ret

def get_random_dabblets(count=2):
    dabblets = []
    page_ids = random.sample(get_dab_page_ids(count=count*2), count)
    articles = get_articles(page_ids)
    dabblets.extend(sum([get_dabblets(a) for a in articles], []))
    return dabblets

import re
def replace_nth(n, guess):
    def alternate(n):
        i=0
        while True:
            i += 1
            yield i%n == 0
    gen = alternate(n)
    def match(m):
        replace = gen.next()
        if replace:
            return '[[' + guess + m.group(1)
        else:
            return m.group(0)
    return match

def replace_dabblet(dabblet, guess):
    article_text = get_articles(page_ids=dabblet.source_page.pageid, parsed=False)[0]
    dab_title = dabblet.title
    dab_postition = dabblet.source_order + 1
    if article_text.revisionid == dabblet.source_page.revisionid:
        return re.sub('\[\[' + dab_title + '(.*){{Disambiguation needed.*}}', replace_nth(dab_postition, guess), article_text.revisiontext)
    else:
        return 'error: the revids don\'t match'

def submit_solution(title, solution):
    params = {'action': 'edit',
              'format': 'json',
              'title': title,
              'text': solution,
              'summary': EDIT_SUMMARY,
              'token': '+\\'}
    resp = api_req('query', params)
    return resp

def chunked_pimap(func, els, concurrency=DEFAULT_CONC, chunk_size=DEFAULT_PER_CALL):
    chunked = (els[i:i + chunk_size]
               for i in xrange(0, len(els), chunk_size))
    pool = Pool(concurrency)
    return pool.imap_unordered(func, chunked)

@dabase.dab_db.commit_on_success
def save_a_bunch(count=DEFAULT_LIMIT, category=DEFAULT_CAT, concurrency=DEFAULT_CONC, 
                 per_call=DEFAULT_PER_CALL, db_name=DEFAULT_DB):
    import time

    page_ids = get_dab_page_ids(category, count)

    dabblets = []
    dpm = ProgressMeter(total=len(page_ids), unit="articles", ticks=30)
    for pages in chunked_pimap(get_articles, page_ids,
                               concurrency=concurrency,
                               chunk_size=per_call):
        for p in pages:
            dpm.update(1)
            cur_dabs = get_dabblets(p)
            dabblets.extend(cur_dabs)
    
    print
    print 'Saving', len(dabblets), 'dabblets.'
    dspm = ProgressMeter(total=len(dabblets), unit="dabblets", ticks=30)
    dsave_start = time.time()
    for d in dabblets:
        d.save()
        for img in d.source_imgs:
            dab_img = DabImage(dabblet=d, src=img)
            dab_img.save()
        dspm.update(1)
    print
    print 'Done saving', len(dabblets), 'Dabblets. (', time.time()-dsave_start,'seconds)'

    print 'Processing choices for', len(dabblets), 'Dabblets.'
    cpm = ProgressMeter(total=len(page_ids), unit="Dabblets", ticks=30)
    all_choices = []
    for choices in chunked_pimap(get_dab_choices, dabblets,
                                 concurrency=concurrency,
                                 chunk_size=per_call):
        cpm.update(per_call)
        all_choices.extend(choices)
    
    print
    print 'Saving', len(all_choices), 'DabChoices.'
    cspm = ProgressMeter(total=len(all_choices), unit="DabChoices", ticks=30)
    csave_start = time.time()
    for c in all_choices:
        c.save()
        cspm.update(1)
    print 'Done saving', len(dabblets), 'DabChoices. (', time.time()-csave_start,'seconds)'

    drank_start = time.time()
    print 'Ranking', len(dabblets), 'Dabblets.'
    for d in dabblets:
        d.priority = d.get_priority()
        d.save()
    print 'Done ranking', len(dabblets), 'DabChoices. (', time.time()-drank_start,'seconds)'

    print len(set([d.title for d in dabblets])), 'unique titles'
    print len(set([d.source_title for d in dabblets])), 'unique source pages'
    print len(all_choices), 'dabblet choices fetched and saved.'

    print Dabblet.select().count(), 'total records in database'
    print len(set([d.title for d in Dabblet.select()])), 'unique titles in database'

    print 'Committing...'
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

def parse_args():
    parser = OptionParser()
    parser.add_option("-d", "--database", dest="database", 
                      type="string", default=DEFAULT_DB,
                      help="name of sqlite database used for saving Dabblets")

    parser.add_option("-a", "--all", dest="get_all", 
                      action="store_true", default=False,
                      help="save as many Dabblets as we can find")

    parser.add_option("-l", "--limit", dest="limit", 
                      type="int", default=DEFAULT_LIMIT,
                      help="max number of articles to search for Dabblets (see -a)")

    parser.add_option("-C", "--category", dest="category", 
                      type="string", default=DEFAULT_CAT,
                      help="category to search for Dabblets (recursive)")

    parser.add_option("-c", "--concurrency", dest="concurrency", 
                      type="int", default=DEFAULT_CONC,
                      help="concurrency factor to use when querying the" 
                      "Wikipedia API (simultaneous requests)")

    parser.add_option("-g", "--grouping", dest="grouping", 
                      type="int", default=DEFAULT_PER_CALL,
                      help="how many sub-responses to request per API call")

    parser.add_option('-D', "--debug", dest="debug",
                      action="store_true", default=False,
                      help="enable debugging (and pop up pdb at the end of successful run")

    parser.add_option("-q", "--quiet", dest="verbose", action="store_false",
                      help="suppress output (TODO)")
    return parser.parse_args()


if __name__ == '__main__':
    import time
    opts, args = parse_args()
    start = time.time()
    if opts.get_all:
        print 'Getting all Dabblets.',
        opts.limit = None
    else:
        print 'Searching up to',opts.limit,'articles for Dabblets.'
    print 'Using', opts.concurrency, 'green threads. Saving to', opts.database

    dabase.init(opts.database)

    try:
        dabblets = save_a_bunch(count=opts.limit,
                                category=opts.category,
                                concurrency=opts.concurrency,
                                per_call=opts.grouping,
                                db_name=opts.database)
    except Exception as e:
        #if opts.debug: #TODO
        #    import pdb;pdb.pm()
        raise

    end = time.time()
    print len(dabblets), 'Dabblets saved in', end-start, 'seconds'

    if opts.debug:
        import pdb;pdb.set_trace()
