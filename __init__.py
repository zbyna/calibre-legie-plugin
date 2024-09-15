#!/usr/bin/env python
# vim:fileencoding=UTF-8:ts=4:sw=4:sta:et:sts=4:ai
# *-* coding: utf-8 *-*
from __future__ import (unicode_literals, division, absolute_import,
                        print_function)

__license__   = 'GPL v3'
__copyright__ = '2024 seeder'
__docformat__ = 'restructuredtext en'

import time
try:
    from urllib.parse import quote
except ImportError:
    from urllib2 import quote

try:
    from queue import Empty, Queue
except ImportError:
    from Queue import Empty, Queue

from calibre.ebooks.metadata import check_isbn

try:
    load_translations()
except NameError:
    pass # load_translations() added in calibre 1.9

from .shared.utils import load_url, strip_accents
from .shared.prefs import PluginPrefsName
from .shared.source import Source


class Legie(Source):
    name                    = 'Legie'
    description             = _('Downloads metadata and covers from Legie.info (only books in Czech, mainly sci-fi and fantasy)')
    author                  = 'seeder'
    version                 = (2, 1, 2)
    minimum_calibre_version = (0, 8, 0)

    capabilities = frozenset(['identify', 'cover'])
    touched_fields = frozenset(['title', 'authors', 'identifier:legie_povidka', 'identifier:legie', 'identifier:isbn', 'identifier:ean', 'tags', 'comments', 'rating',
                                'series', 'series_index', 'publisher', 'pubdate', 'languages'])
    has_html_comments = True
    can_get_multiple_covers = True
    prefer_results_with_isbn = False

    config_message = _('Plugin version: <b>%s</b> - Report errors and suggestions through <a href="https://www.mobileread.com/forums/showthread.php?t=362097">MobileRead</a> forum.')%str(version).strip('()').replace(', ', '.')

    BASE_URL = 'https://www.legie.info'

    def config_widget(self):
        '''
        Overriding the default configuration screen for our own custom configuration
        '''
        from .config import ConfigWidget
        return ConfigWidget(self)
    
    def get_book_url(self, identifiers):
        legie_id = identifiers.get('legie', None)
        if legie_id:
            return ('legie', legie_id, ''.join([self.BASE_URL, '/kniha/', legie_id]))
        
        legie_povidka_id = identifiers.get('legie_povidka', None)
        if legie_povidka_id:
            return ('legie_povidka', legie_povidka_id, ''.join([self.BASE_URL, '/povidka/', legie_povidka_id]))
        
        ean = identifiers.get('ean', None)
        if ean:
            return ('ean', ean, ''.join(['https://search.worldcat.org/search?q=', ean]))
        return None
    
    def get_book_urls(self, identifiers):
        '''
        Override this method if you would like to return multiple URLs for this book.
        Return a list of 3-tuples. By default this method simply calls :func:`get_book_url`.
        '''
        ean = legie = legie_p = None
        legie_id = identifiers.get('legie', None)
        if legie_id:
            legie = self.get_book_url(dict((('legie', legie_id),)))

        ean_id = identifiers.get('ean', None)
        if ean_id:
            ean = self.get_book_url(dict((('ean', ean_id),)))

        try:
            import calibre_plugins.pitaval

            if ean is not None and legie is not None:
                return (legie, ean, )
        except:
            if ean is not None and legie is not None:
                return (legie, ean, )
        if legie is not None:
            return (legie, )

        legie_id = identifiers.get('legie_povidka', None)
        if legie_id:
            legie_p = self.get_book_url(dict((('legie_povidka', legie_id),)))
        if legie_p is not None:
            return (legie_p, )

        data = self.get_book_url(identifiers)
        if data is None:
            return ()
        return (data,)
    
    def get_book_url_name(self, idtype, idval, url):
        '''
        Return a human readable name from the return value of get_book_url().
        '''
        if idtype == 'legie_povidka':
            return 'Legie povídka'
        elif idtype == 'ean':
            return 'EAN %s'%idval
        else:
            return self.name

    def get_cached_cover_url(self, identifiers):
        url = None
        legie_id = identifiers.get('legie', None)
        if legie_id is None:
            isbn = check_isbn(identifiers.get('isbn', None))
            if isbn is not None:
                legie_id = self.cached_isbn_to_identifier(isbn)
        if legie_id is not None:
            url = self.cached_identifier_to_cover_url(legie_id)
            return url

    def get_pref(self, pref=None):
        """
        Returns MetadataPlugin specific preferences
        """
        try:
            from .prefs import get_pref
            return get_pref(pref)
        except ImportError:
            return None

    def identify_results_keygen(self, title=None, authors=None,
            identifiers={}):
        from .shared.compare import MetadataCompareKeyGen
        def keygen(mi):
            return MetadataCompareKeyGen(mi, self, title, authors,
                identifiers)
        return keygen

    def create_query(self, log, title=None, authors=None, tales=False, search_engine='legie'):
        if title is None:
            title = ''
        if authors is None:
            authors = ''
        elif isinstance(authors, list):
            discard = ['Unknown', 'Neznámý']
            for d in discard:
                if d in authors:
                    authors.remove(d)
            authors = ' '.join(authors)

        search_page = ''
        if search_engine == 'legie':
            if tales:
                search_page = ''.join([self.BASE_URL, '/index.php?cast=povidky&search_text={title}&search_autor_kp={authors}'])
            else:
                search_page = ''.join([self.BASE_URL, '/index.php?cast=knihy&search_text={title}&search_autor_kp={authors}'])
        elif search_engine == 'google':
            if tales:
                search_page = ''.join([self.GOOGLE_SEARCH_URL, 'site:', self.BASE_URL, '/povidka/ {title}+{authors}&num=50&udm=14'])
            else:
                search_page = ''.join([self.GOOGLE_SEARCH_URL, 'site:', self.BASE_URL, '/kniha/ {title}+{authors}&num=50&udm=14'])
        elif search_engine == 'duckduckgo':
            if tales:
                search_page = ''.join([self.DUCKDUCKGO_SEARCH_URL, 'site:', self.BASE_URL, '/povidka/ {title}+{authors}'])
            else:
                search_page = ''.join([self.DUCKDUCKGO_SEARCH_URL, 'site:', self.BASE_URL, '/kniha/ {title}+{authors}'])

        return search_page.format(title=quote(title.encode('utf-8')),
                                  authors=quote(authors.encode('utf-8')))

    def identify(self, log, result_queue, abort, title=None, authors=None,
                 identifiers={}, timeout=30):
        '''
        Note this method will retry without identifiers automatically if no
        match is found with identifiers.
        '''
        # search for identifiers and extra metadata in title field format identifier:123456; e.g. legie:1234, pubdate:2023
        title, identifiers = self.search_title_for_metadata(title, identifiers)
        self.identifiers = identifiers
        log.info('Title:\t', title, '\nAuthors:\t', authors, '\nIds:\t', identifiers)
        log.info('--------')
        legie_id = identifiers.get('legie', None)
        legie_povidka_id = identifiers.get('legie_povidka', None)
        isbn = check_isbn(identifiers.get('isbn', None))
        ean = check_isbn(identifiers.get('ean', None))

        # get plugin preferences
        max_results = self.get_pref(PluginPrefsName.KEY_MAX_DOWNLOADS)
        legie_id_search = self.get_pref(PluginPrefsName.IDENTIFIER_SEARCH)
        isbn_search = self.get_pref(PluginPrefsName.ISBN_SEARCH)
        tales_search = self.get_pref(PluginPrefsName.TALES_SEARCH) or self.identifiers.get('type', None) == 'p'
        google_engine = self.get_pref(PluginPrefsName.GOOGLE_SEARCH) or self.identifiers.get('search', None) == 'g'
        duckduckgo_engine = self.get_pref(PluginPrefsName.DUCKDUCKGO_SEARCH) or self.identifiers.get('search', None) == 'd'

        # add google search cookies
        br = self.browser
        br.set_header('user-agent', 'Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:47.0) Gecko/20100101 Firefox/47.0')
        if google_engine:
            br.set_simple_cookie('CONSENT', 'PENDING+987', '.google.com', path='/')
            template = b'\x08\x01\x128\x08\x14\x12+boq_identityfrontenduiserver_20231107.05_p0\x1a\x05en-US \x03\x1a\x06\x08\x80\xf1\xca\xaa\x06'
            from datetime import date
            from base64 import standard_b64encode
            template.replace(b'20231107', date.today().strftime('%Y%m%d').encode('ascii'))
            br.set_simple_cookie('SOCS', standard_b64encode(template).decode('ascii').rstrip('='), '.google.com', path='/')

        br = self.browser
        query = None
        matches = []
        no_matches = []
        # search via legie identifier
        exact_match = False
        if legie_id and legie_id_search:
            _, response = load_url(log, ''.join([self.BASE_URL, '/kniha/', legie_id]), br)
            try:
                if response.geturl().find(legie_id) != -1:
                    matches.append(response.geturl())
                    exact_match = True
                else:
                    log.error('Wrong legie identifier was inserted.\nContinuing with ISBN or Title/Author(s) search.')
            except:
                log.error('*** Could not open book page. Wrong URL inserted.')

        # search via isbn identifier
        if not exact_match and isbn and isbn_search:
            root, response = load_url(log, ''.join([self.BASE_URL, '/index.php?search_ignorovat_casopisy=on&omezeni=ksp&search_isbn=', isbn]), br)
            if response.geturl().find(isbn) == -1 and response.geturl().find('/kniha/'):
                matches.append(response.geturl())
                exact_match = True
            else:
                # when more than one result return from isbn search
                self._parse_search_results(log, title, authors, root, matches, no_matches, timeout)
        # search for isbn in notes
        if not exact_match and isbn and isbn_search:
            root, response = load_url(log, ''.join([self.BASE_URL, '/index.php?search_ignorovat_casopisy=on&omezeni=ksp&search_vydani_poznamka=', isbn]), br)
            if response.geturl().find(isbn) == -1 and response.geturl().find('/kniha/'):
                matches.append(response.geturl())
                exact_match = True
            else:
                # when more than one result return from isbn search
                self._parse_search_results(log, title, authors, root, matches, no_matches, timeout)

        #search via ean identifier (option tied with isbn search)
        if not exact_match and ean and isbn_search:
            root, response = load_url(log, ''.join([self.BASE_URL, '/index.php?search_ignorovat_casopisy=on&omezeni=ksp&search_isbn=', ean]), br)
            if response.geturl().find(ean) == -1 and response.geturl().find('/kniha/'):
                matches.append(response.geturl())
                exact_match = True
            else:
                # when more than one result return from ean search
                self._parse_search_results(log, title, authors, root, matches, no_matches, timeout)
        # search for ean in notes
        if not exact_match and ean and isbn_search:
            root, response = load_url(log, ''.join([self.BASE_URL, '/index.php?search_ignorovat_casopisy=on&omezeni=ksp&search_vydani_poznamka=', ean]), br)
            if response.geturl().find(ean) == -1 and response.geturl().find('/kniha/'):
                matches.append(response.geturl())
                exact_match = True
            else:
                # when more than one result return from isbn search
                self._parse_search_results(log, title, authors, root, matches, no_matches, timeout)
        
        ## TALES searching
        # search via legie_povidka identifier
        if legie_povidka_id and legie_id_search:
            _, response = load_url(log, ''.join([self.BASE_URL, '/povidka/', legie_povidka_id]), br)
            try:
                if response.geturl().find(legie_povidka_id) != -1:
                    matches.append(response.geturl())
                    exact_match = True
                else:
                    log.error('Wrong legie_povidka identifier was inserted.\nContinuing with ISBN or Title/Author(s) search.')
            except:
                log.error('*** Could not open book page. Wrong URL inserted.')
        
        # search for tales on Google (title + authors)
        try:
            if not exact_match and google_engine and tales_search:
                query = self.create_query(log, title=title, authors=authors, tales=True, search_engine='google')
                root, response = load_url(log, query, br)
                log.debug(u'Querying tales via google: %s'%query)
                self._parse_google_search_results(log, title, authors, root, matches, no_matches, timeout)
        except Exception as e:
            log.exception(u'*** Error while Google searching: %s'%e)

        # search for tales on DuckDuckGo (title + authors)
        try:
            if not exact_match and duckduckgo_engine and tales_search:
                query = self.create_query(log, title=title, authors=authors, tales=True, search_engine='duckduckgo')
                root, response = load_url(log, query, br)
                log.debug(u'Querying tales via duckduckgo: %s'%query)
                self._parse_duckduckgo_results(log, title, authors, root, matches, no_matches, timeout)
        except Exception as e:
            log.exception(u'*** Error while DuckDuckGo searching: %s'%e)
        
        # search in tales (title + authors)
        if not exact_match and len(matches) < max_results and tales_search:
            query = self.create_query(log, title=title, authors=authors, tales=True)
            log.debug('Querying for tales (title + authors)..)\n Query: %s'%query)
            root, response = load_url(log, query, br)
            if response.geturl().find( 'index.php?') == -1:
                matches.append(response.geturl())
                log.info('ID in query, redirected right to book page...')
                exact_match = True
            else:
                log.debug(u'Querying title + authors: %s'%query)
                self._parse_search_results(log, title, authors, root, matches, no_matches, timeout, tales=True)
                if matches:
                    exact_match = True
            log.debug('--- Matches after process: %s: %s' %(len(matches), matches))
        # search in tales only with title field
        if not exact_match and len(matches) < max_results and tales_search:
            query = self.create_query(log, title=title, authors=[], tales=True)
            log.debug('Querying for tales (title only)..)\n Query: %s'%query)
            root, response = load_url(log, query, br)
            if response.geturl().find( 'index.php?') == -1:
                matches.append(response.geturl())
                log.info('ISBN in query, redirected right to book page...')
                exact_match = True
            else:
                log.debug(u'Querying title + authors: %s'%query)
                self._parse_search_results(log, title, authors, root, matches, no_matches, timeout, tales=True)
                if matches:
                    exact_match = True
            log.debug('--- Matches after process: %s: %s' %(len(matches), matches))
        # search in tales only with one word from title (longest first)
        if not exact_match and len(matches) < max_results and title and tales_search:
            title_split = title.split(' ')
            title_split.sort(key=lambda i: (-len(i), i))
            if len(title_split) > 1:
                for word in title_split:
                    query = self.create_query(log, title=word, authors=None, tales=True)
                    log.debug('Querying only one word from tale title: %s (%s): %s' %(word, title, query))
                    root, response = load_url(log, query, br)
                    if response.geturl().find( 'index.php?') == -1:
                        matches.append(response.geturl())
                        log.info('ISBN in query, redirected right to book page...')
                        exact_match = True
                    else:
                        log.debug(u'Querying title + authors: %s'%query)
                        self._parse_search_results(log, word, None, root, matches, no_matches, timeout, tales=True)
        ## END of tales

        ## GOOGLE Search
        try:
            if not exact_match and len(matches) < max_results and google_engine:
                query = self.create_query(log, title=title, authors=authors, search_engine='google')
                log.debug(u'Querying via google: %s'%query)
                root, response = load_url(log, query, br)
                self._parse_google_search_results(log, title, authors, root, matches, no_matches, timeout)
        except Exception as e:
            log.debug(u'*** Error while Google searching: %s'%e)

        ## DUCKDUCKGO Search
        try:
            if not exact_match and len(matches) < max_results and duckduckgo_engine:
                query = self.create_query(log, title=title, authors=authors, search_engine='duckduckgo')
                log.debug(u'Querying via duckduckgo: %s'%query)
                root, response = load_url(log, query, br)
                self._parse_duckduckgo_results(log, title, authors, root, matches, no_matches, timeout)
        except Exception as e:
            log.debug(u'*** Error while DuckDuckGo searching: %s'%e)

        ## Title/Authors Combination search
        # try only with title
        if not exact_match and len(matches) < max_results and title:
            query = self.create_query(log, title=title, authors=None)
            root, response = load_url(log, query, br)
            if response.geturl().find( 'index.php?') == -1:
                matches.append(response.geturl())
                log.info('ISBN in query, redirected right to book page...')
                exact_match = True
            else:
                log.debug(u'Querying only title: %s'%query)
                self._parse_search_results(log, title, authors, root, matches, no_matches, timeout)
        # search via title and authors field
        if not exact_match and len(matches) < max_results:
            query = self.create_query(log, title=title, authors=authors)
            root, response = load_url(log, query, br)
            if response.geturl().find( 'index.php?') == -1:
                matches.append(response.geturl())
                log.info('ISBN in query, redirected right to book page...')
                exact_match = True
            else:
                log.debug(u'Querying title + authors: %s'%query)
                self._parse_search_results(log, title, authors, root, matches, no_matches, timeout)
        # try only with one word from title (longest first)
        if not exact_match and len(matches) < max_results and title:
            title_split = title.split(' ')
            title_split.sort(key=lambda i: (-len(i), i))
            if len(title_split) > 1:
                for word in title_split:
                    query = self.create_query(log, title=word, authors=None)
                    log.debug('Querying only one word from title: %s (%s): %s' %(word, title, query))
                    root, response = load_url(log, query, br)
                    if response.geturl().find( 'index.php?') == -1:
                        matches.append(response.geturl())
                        log.info('ISBN in query, redirected right to book page...')
                        exact_match = True
                    else:
                        log.debug(u'Querying only title: %s'%query)
                        self._parse_search_results(log, word, authors, root, matches, no_matches, timeout)

        # try only with authors
        if not exact_match and len(matches) < max_results and authors:
            query = self.create_query(log, title=None, authors=authors)
            log.debug(u'Querying only authors: %s'%query)
            root, response = load_url(log, query, br)
            self._parse_search_results(log, title, authors, root, matches, no_matches, timeout)

        # try only with one author
        if not exact_match and len(matches) < max_results and authors:
            for auth in authors:
                if len(matches) >= max_results:
                    break
                query = self.create_query(log, title=None, authors=[auth])
                log.debug('Querying only one author named %s \n Query: %s' %(auth, query))
                root, response = load_url(log, query, br)
                self._parse_search_results(log, title, authors, root, matches, no_matches, timeout)

        # try only with one part of authors name
        if not exact_match and len(matches) < max_results and authors:
            for auth in authors:
                if len(matches) >= max_results:
                    break
                name_split = auth.split(' ')
                if len(name_split) > 1:
                    for name in reversed(name_split):
                        if len(matches) >= max_results:
                            break
                        query = self.create_query(log, title=None, authors=[name])
                        log.debug('Querying only one part of authors name -  %s (%s): %s' %(name, auth, query))
                        root, response = load_url(log, query, br)
                        self._parse_search_results(log, title, authors, root, matches, no_matches, timeout)
                        log.debug('--- Matches after process: %s %s'%(len(matches), matches))

        if no_matches:
            for nmatch in no_matches:
                if len(matches) < max_results and not(nmatch in matches):
                    matches.append(nmatch)
        log.info('Matches: %s'%(matches))

        if abort.is_set():
            log.info("Abort is set to true, aborting")
            return

        if not matches:
            log.error('No matches found. Try to fill Title field.')
            return


        from calibre_plugins.legie.worker import Worker
        workers = [Worker(url, result_queue, self.browser, log, i, self) for i, url in
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

    def _parse_search_results(self, log, orig_title, orig_authors, root, matches, no_matches, timeout, tales=False):
        max_results = self.get_pref(PluginPrefsName.KEY_MAX_DOWNLOADS)
        
        if tales:
            results = root.xpath('//table[(preceding-sibling::ul[@id="zalozky"] or preceding-sibling::h2[position() = 1 and contains(text(), "Povídky")]) and @class="tabulka-s-okraji" and .//th[contains(text(), "Autor/Autoři díla") or contains(text(), "Název")]]//tr[not(th)]')
        else:
            results = root.xpath('//table[(preceding-sibling::ul[@id="zalozky"] or preceding-sibling::h2[position() = 1 and contains(text(), "Knihy")]) and @class="tabulka-s-okraji" and .//th[contains(text(), "Autor/Autoři díla") or contains(text(), "Název")]]//tr[not(th)]')
        result_url = None
        log.debug('Found %s results'%len(results))
        for result in results:
            vlozit = False

            title = result.xpath('td/a[(contains(@href, "kniha/") or contains(@href, "povidka/")) and position() = 1]/text()')
            title = title[0] if title else ''
            log.debug('kniha: %s .. orig.autor: %s' %(title, orig_authors))

            first_author = result.xpath('td/a[contains(@href, "autor/") and position() = 1]/text()')
            first_author = first_author[0].replace(' (p)', '').lower() if first_author else ''
            found_auths = {a for a in first_author.split()[1:] if len(a) > 2} # list of founded names (now with first names too)
            found_auths = {a.strip('ová') for a in found_auths} # without 'ová'
            found_auths_ova = {'%sová' %a for a in found_auths} #added 'ová'
            found_auths = found_auths.union(found_auths_ova)
            #hledá shodu v příjmení i jménu
            if orig_authors:
                orig_authors = ' '.join(orig_authors).split()
                orig_auths = {o.lower().replace(',', '') for o in orig_authors}
                if orig_auths.intersection(found_auths):
                    log.debug('found_auths:')
                    vlozit = True
                log.info('found_auths: %s .. orig_auths: %s'%(found_auths, orig_auths))

            vlozit = False
            #compare title match (without accents)
            if orig_title and title and strip_accents(orig_title).lower() == strip_accents(title).lower():
                vlozit = True


            book_url = result.xpath('td/a[(contains(@href, "kniha/") or contains(@href, "povidka/")) and position() = 1]/@href')
            result_url = '%s/%s'%(self.BASE_URL, book_url[0])
            log.debug('Result URL: %r'%result_url)
            if vlozit and result_url not in matches and len(matches) < max_results:
                matches.append(result_url)
            elif result_url is not None and result_url not in no_matches:
                no_matches.append(result_url)
            if len(matches) >= max_results:
                break

        log.info('Matches: %s .. No matches: %s'%(matches, no_matches))

    def download_cover(self, log, result_queue, abort,
            title=None, authors=None, identifiers={}, timeout=30, get_best_cover=False):
        max_covers = self.get_pref(PluginPrefsName.MAX_COVERS)
        obalky_cover = self.get_pref(PluginPrefsName.OBALKYKNIH_COVER)
        if max_covers == 0:
            log.info('Searching for covers on legie is disabled. You can enable it in plugin preferences.')
            return

        br = self.browser
        cached_url = self.get_cached_cover_url(identifiers)

        # none img_urls .. searching for some with identify
        if cached_url is None:
            log.info('No cached cover found, running identify')
            rq = Queue()
            self.identify(log, rq, abort, title=title, authors=authors, identifiers=identifiers)
            if abort.is_set():
                return
            results = []
            while True:
                try:
                    results.append(rq.get_nowait())
                except Empty:
                    break
            results.sort(key=self.identify_results_keygen(title=title, authors=authors, identifiers=identifiers))
            for mi in results:
                cached_url = self.get_cached_cover_url(mi.identifiers)
                if cached_url is not None:
                    break

        if cached_url is not None:
            # one img_url
            if len(cached_url) == 1:
                try:
                    cdata = br.open_novisit(cached_url[0], timeout=timeout).read()
                    result_queue.put((self, cdata))
                except:
                    log.exception('*** Failed to download cover - %s' % cached_url[0])
            # multiple img_urls
            elif len(cached_url) > 1:
                if obalky_cover:
                    checked_urls = cached_url[:max_covers+1]
                else:
                    checked_urls = cached_url[:max_covers]
                for url in checked_urls:
                    try:
                        cdata = br.open_novisit(url, timeout=timeout).read()
                        result_queue.put((self, cdata))
                    except:
                        log.exception('*** Failed to download cover - %s' % url)

        if cached_url is None:
            log.info('No cover found')
            return

        if abort.is_set():
            return


if __name__ == '__main__': # tests
    # To run these test use:
    # calibre-debug -e __init__.py
    from calibre.ebooks.metadata.sources.test import (test_identify_plugin,
                                                      title_test, authors_test, series_test)
    test_identify_plugin(Legie.name,
                         [

                             ( # A book with no id specified
                                 {'identifiers':{'legie': '11111111103#1996'}, 'title':"Poslední obyvatel z planety Zwor", 'authors':['Jean-pierre Garen']},
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


