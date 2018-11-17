#!/usr/bin/env python
# vim:fileencoding=UTF-8:ts=4:sw=4:sta:et:sts=4:ai
from __future__ import (unicode_literals, division, absolute_import,
                        print_function)

__license__   = 'GPL v3'
__copyright__ = '2012, Michal Rezny <miisha@seznam.cz>'
__docformat__ = 'restructuredtext en'

import time, re, HTMLParser
from urllib import quote, unquote
from Queue import Queue, Empty

from lxml.html import fromstring, tostring

from calibre import as_unicode
from calibre.ebooks.metadata.sources.base import Source
from calibre.utils.icu import lower
from calibre.utils.cleantext import clean_ascii_chars
from calibre.utils.localization import get_udc


class Legie(Source):

    name                    = 'Legie'
    description             = _('Downloads metadata and covers from Legie.info (only books in Czech, mainly sci-fi and fantasy)')
    author                  = 'Michal Rezny'
    version                 = (2, 0, 1)
    minimum_calibre_version = (0, 8, 0)

    capabilities = frozenset(['identify', 'cover'])
    touched_fields = frozenset(['title', 'authors', 'identifier:legie', 'comments', 'rating', 'series', 
                                'identifier:isbn', 'publisher', 'pubdate', 'series_index', 'tags', 'language'])
    has_html_comments = True
    supports_gzip_transfer_encoding = True

    BASE_URL = 'http://www.legie.info'

    def get_book_url(self, identifiers):
        ff_id = identifiers.get('legie', None)
        if ff_id:
            return ('Legie', ff_id,
                    '%s/kniha/%s'%(Legie.BASE_URL, ff_id))

    def get_cached_cover_url(self, identifiers):
        url = None
        ff_id = identifiers.get('legie', None)
        if ff_id is not None:
            url = self.cached_identifier_to_cover_url(ff_id)
        return url
    
    def create_title_query(self, log, title=None):
        q = ''
        if title:
            title = get_udc().decode(title)
            tokens = []
            title_tokens = list(self.get_title_tokens(title,
                                strip_joiners=False, strip_subtitle=True))
            tokens = [quote(t.encode('utf-8') if isinstance(t, unicode) else t) for t in title_tokens]
            q = '+'.join(tokens)
        if not q:
            return None
        return '%s/index.php?cast=knihy&search_text=%s'%(Legie.BASE_URL, q)

    def identify(self, log, result_queue, abort, title=None, authors=None,
            identifiers={}, timeout=30):
        '''
        Note this method will retry without identifiers automatically if no
        match is found with identifiers.
        '''
        matches = []

        # If we have a Legie id then we do not need to fire a "search".
        # Instead we will go straight to the URL for that book.
        legie_id = identifiers.get('legie', None)
        br = self.browser
        if legie_id:
            matches.append('%s/kniha/%s'%(Legie.BASE_URL, legie_id))
        else:
            query = self.create_title_query(log, title=title)
            if query is None:
                log.error('Insufficient metadata to construct query')
                return
            try:
                log.info('Querying: %s'%query)
                response = br.open_novisit(query, timeout=timeout)
                raw = response.read()
                redirected = response.geturl()
            except Exception as e:
                err = 'Failed to make identify query: %r'%query
                log.exception(err)
                return as_unicode(e)
            root = fromstring(clean_ascii_chars(raw))
            # Now grab the match from the search result, provided the
            # title appears to be for the same book
            if redirected == query:
                self._parse_search_results(log, title, root, matches, timeout, query)
            else:
                matches.append(redirected)

        if abort.is_set():
            return

        if not matches:
            log.error('No matches found with query: %r'%query)
            return

        from calibre_plugins.legie.worker import Worker
        author_tokens = list(self.get_author_tokens(authors))
        workers = [Worker(url, author_tokens, result_queue, br, log, i, self) for i, url in
                enumerate(matches)]

        for w in workers:
            w.start()
            # Don't send all requests at the same time
            time.sleep(0.1)

        while not abort.is_set():
            a_worker_is_alive = False
            for w in workers:
                w.join(0.2)
                if abort.is_set():
                    break
                if w.is_alive():
                    a_worker_is_alive = True
            if not a_worker_is_alive:
                break

        return None

    def _parse_search_results(self, log, orig_title, root, matches, timeout, query):

        def ismatch(title):
            title = lower(title)
            match = not title_tokens
            for t in title_tokens:
                if lower(t) in title:
                    match = True
                    break
            return match

        title_tokens = list(self.get_title_tokens(orig_title))
        max_results = 10
        
        res = root.xpath('//div[@id="kniha_info"]')
        if res:
            log.info('Found match directly: %s'%(query))
            matches.append(query)
            return
        
        res_path = root.xpath('//table[@class="tabulka-s-okraji"]/tr/td[1]')
        
        if res_path:
            for data in res_path:
                id = ''.join(data.xpath('./a/@href'))
                if not id:
                    continue
    
                title = ''.join(data.xpath('./a/text()'))
                if not ismatch(title):
                    log.error('Rejecting as not close enough match: %s'%(title))
                    continue
                url = '%s/%s'%(Legie.BASE_URL, id.strip())
                log.info('Found in search results: %s'%(url))
                matches.append(url)
                if len(matches) >= max_results:
                    break
        else:
            log.info('Result table was not found')


    def download_cover(self, log, result_queue, abort,
            title=None, authors=None, identifiers={}, timeout=30):
        cached_url = self.get_cached_cover_url(identifiers)
        if cached_url is None:
            log.info('No cached cover found, running identify')
            rq = Queue()
            self.identify(log, rq, abort, title=title, authors=authors,
                    identifiers=identifiers)
            if abort.is_set():
                return
            results = []
            while True:
                try:
                    results.append(rq.get_nowait())
                except Empty:
                    break
            results.sort(key=self.identify_results_keygen(
                title=title, authors=authors, identifiers=identifiers))
            for mi in results:
                cached_url = self.get_cached_cover_url(mi.identifiers)
                if cached_url is not None:
                    break
        if cached_url is None:
            log.info('No cover found')
            return

        if abort.is_set():
            return
        br = self.browser
        log('Downloading cover from:', cached_url)
        try:
            cdata = br.open_novisit(cached_url, timeout=timeout).read()
            result_queue.put((self, cdata))
        except:
            log.exception('Failed to download cover from:', cached_url)


if __name__ == '__main__': # tests
    # To run these test use:
    # calibre-debug -e __init__.py
    from calibre.ebooks.metadata.sources.test import (test_identify_plugin,
            title_test, authors_test, series_test)
    test_identify_plugin(Legie.name,
        [
         
            ( # A book with no id specified
                {'title':"Poslední obyvatel z planety Zwor", 'authors':['Jean-pierre Garen']},
                [title_test("Poslední obyvatel z planety Zwor",
                    exact=True), authors_test(['Jean-pierre Garen']),
                    series_test('Mark Stone - Kapitán Služby pro dohled nad primitivními planetami', 1.0)]

            ),

            ( # Multiple answers
                {'title':'Čaroprávnost'},
                [title_test('Čaroprávnost',
                    exact=True), authors_test(['Terry Pratchett']),
                    series_test('Úžasná Zeměplocha', 3.0)]

            ),

            ( # Book with given id and edition year
                {'identifiers':{'legie': '103#1996'},'title':'Čaroprávnost'},
                [title_test('Čaroprávnost',
                    exact=True), authors_test(['Terry Pratchett']),
                    series_test('Úžasná Zeměplocha', 3.0)] #80-85609-54-1

            ),

            ( # A book with a Legie id
                {'identifiers':{'legie': '973'},
                    'title':'Drak na Wilku', 'authors':['Jean-Pierre Garen']},
                [title_test('Drak na Wilku',
                    exact=True), authors_test(['Jean-Pierre Garen']),
                    series_test('Mark Stone - Kapitán Služby pro dohled nad primitivními planetami', 7)]

            ),

        ])


