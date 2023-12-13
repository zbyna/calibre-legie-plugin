#!/usr/bin/env python
# vim:fileencoding=UTF-8:ts=4:sw=4:sta:et:sts=4:ai
from __future__ import (unicode_literals, division, absolute_import,
                        print_function)

__license__ = 'GPL v3'
__copyright__ = '2011, Michal Rezny <miisha@seznam.cz>'
__docformat__ = 'restructuredtext en'

import socket, re, datetime, math
from threading import Thread

from lxml.html import fromstring, tostring

from calibre.ebooks.metadata.book.base import Metadata
from calibre.library.comments import sanitize_comments_html
from calibre.utils.cleantext import clean_ascii_chars
from calibre.utils.icu import lower


class Worker(Thread):  # Get details

    '''
    Get book details from Webscription book page in a separate thread
    '''

    def __init__(self, url, match_authors, result_queue, browser, log, relevance, plugin, extra_metadata, timeout=20):
        Thread.__init__(self)
        self.daemon = True
        self.url, self.result_queue = url, result_queue
        self.match_authors = match_authors
        self.log, self.timeout = log, timeout
        self.relevance, self.plugin = relevance, plugin
        self.browser = browser.clone_browser()
        self.cover_url = self.legie_id = self.isbn = None

        self.pubdate = extra_metadata.get('pubdate', None)

    def run(self):
        try:
            self.get_details()
        except:
            self.log.exception('get_details failed for url: %r' % self.url)

    def get_details(self):
        try:
            self.log.info('Legie url: %r' % self.url)
            raw = self.browser.open_novisit(self.url, timeout=self.timeout).read().strip()
        except Exception as e:
            if callable(getattr(e, 'getcode', None)) and \
                    e.getcode() == 404:
                self.log.error('URL malformed: %r' % self.url)
                return
            attr = getattr(e, 'args', [None])
            attr = attr if attr else [None]
            if isinstance(attr[0], socket.timeout):
                msg = 'Legie timed out. Try again later.'
                self.log.error(msg)
            else:
                msg = 'Failed to make details query: %r' % self.url
                self.log.exception(msg)
            return

        raw = raw.decode('utf-8', errors='replace')
        # open('E:\\t3.html', 'wb').write(raw)

        if '<title>404 - ' in raw:
            self.log.error('URL malformed: %r' % self.url)
            return

        try:
            root = fromstring(clean_ascii_chars(raw))
        except:
            msg = 'Failed to parse Legie details page: %r' % self.url
            self.log.exception(msg)
            return

        self.parse_details(root)

    def parse_details(self, root):
        try:
            legie_id = self.parse_legie_id(self.url)
        except:
            self.log.exception('Error parsing Legie id for url: %r' % self.url)
            legie_id = None

        try:
            title = self.parse_title(root)
        except:
            self.log.exception('Error parsing title for url: %r' % self.url)
            title = None

        try:
            authors = self.parse_authors(root)
        except:
            self.log.exception('Error parsing authors for url: %r' % self.url)
            authors = []

        if not title or not authors or not legie_id:
            self.log.error('Could not find title/authors/Legie id for %r' % self.url)
            self.log.error('Legie: %r Title: %r Authors: %r' % (legie_id, title,
                                                                authors))
            return

        self.legie_id = legie_id

        rating = comments = series = series_index = None
        try:
            rating = self.parse_rating(root)
        except:
            self.log.exception('Error parsing ratings for url: %r' % self.url)

        try:
            comments = self.parse_comments(root)
        except:
            self.log.exception('Error parsing comments for url: %r' % self.url)

        try:
            (series, series_index) = self.parse_series(root)
        except:
            self.log.info('Series not found.')

        try:
            tags = self.parse_tags(root)
        except:
            self.log.exception('Error parsing tags for url: %r' % self.url)
            tags = None

        if legie_id:
            editions = self.get_editions()

            if editions:
                num_editions = len(editions)
                self.log.info('Nalezeno %d vydani' % num_editions)
                for edition in editions:
                    (date_final, cover_url, publisher, isbn) = edition
                    mi = Metadata(title, authors)
                    self.legie_id = "%s#%s" % (legie_id, str(date_final.year))
                    mi.set_identifier('legie', self.legie_id)
                    mi.source_relevance = self.relevance
                    mi.rating = rating
                    mi.comments = comments
                    mi.series = series
                    mi.series_index = series_index
                    if cover_url:
                        mi.cover_url = self.cover_url = cover_url
                        self.plugin.cache_identifier_to_cover_url(self.legie_id, self.cover_url)
                    if tags:
                        mi.tags = tags
                    mi.has_cover = bool(self.cover_url)
                    mi.publisher = publisher
                    mi.isbn = isbn
                    mi.pubdate = date_final
                    mi.language = "ces"
                    self.result_queue.put(mi)
            else:
                mi = Metadata(title, authors)
                mi.set_identifier('legie', self.legie_id)
                mi.source_relevance = self.relevance
                mi.rating = rating
                mi.comments = comments
                mi.series = series
                mi.series_index = series_index
                try:
                    self.cover_url = self.parse_cover(root)
                except:
                    self.log.exception('Error parsing cover for url: %r' % self.url)
                if tags:
                    mi.tags = tags
                mi.has_cover = bool(self.cover_url)
                mi.publisher = publisher
                mi.isbn = isbn
                mi.pubdate = date_final
                mi.language = "ces"
                self.result_queue.put(mi)
                if self.legie_id:
                    if self.cover_url:
                        self.plugin.cache_identifier_to_cover_url(self.legie_id, self.cover_url)

    def parse_legie_id(self, url):
        result = re.search('/kniha/(\d+)', url);
        if result is None:
            return None;
        return result.groups(0)[0]

    def parse_title(self, root):
        title_node = root.xpath('//h2[@id="nazev_knihy"]')
        if title_node:
            self.log.info('Title: %s' % title_node[0].text)
            return title_node[0].text

    def parse_authors(self, root):
        author_nodes = root.xpath('//div[@id="pro_obal"]/../h3/a')
        authors = []
        if author_nodes:
            for author_node in author_nodes:
                author = author_node.text.strip()
                authors.append(author)
        else:
            self.log.info('No author has been found')

        def ismatch(authors_internal):
            authors_internal = lower(' '.join(authors_internal))
            amatch = not self.match_authors
            for a in self.match_authors:
                if lower(a) in authors_internal:
                    amatch = True
                    break
            if not self.match_authors: amatch = True
            return amatch

        if not self.match_authors or ismatch(authors):
            return authors
        self.log('Rejecting authors as not a close match: ', ','.join(authors))

    def parse_comments(self, root):
        description_nodes = root.xpath('//div[@id="anotace"]/strong/following-sibling::p')
        if not description_nodes:
            description_nodes = root.xpath('//div[@id="nic"]/strong/following-sibling::p')

        if description_nodes:
            comments = []
            for node in description_nodes:
                node_text = node.text_content()
                if node_text != None:
                    comments.append("<p>" + node_text + "</p>")

            # comments = tostring(description_node, method='html')
            comments = sanitize_comments_html("".join(comments))
            return comments
        else:
            self.log.info('No comment node was found.')

    def parse_cover(self, root):
        cover_node = root.xpath('//img[@id="hlavni_obalka"]/@src')
        if cover_node:
            cover_url = 'http://www.legie.info/' + cover_node[0]
            return cover_url

    def parse_rating(self, root):
        rating_node = root.xpath('//div[@id="procenta"]/span[1]')
        if rating_node:
            rating_string = rating_node[0].text
            if len(rating_string) > 0:
                stars_ = int(rating_string)
                rating_value = float(stars_ / 20)
                self.log('Found rating:%s' % rating_value)
                return rating_value
        else:
            self.log.info('Rating node not found')

    def parse_series(self, root):
        series_node = root.xpath('//div[@id="kniha_info"]/div/p[starts-with(text(),"série:")]')
        if series_node:
            series_name_node = series_node[0].xpath('./a[1]')
            if series_name_node:
                series_name = series_name_node[0].text
            else:
                return (None, None)

            series_text = series_node[0].text_content()
            match = re.search('díl v sérii: (\d+)', series_text)
            if match:
                self.log.info('Series Index found: %s' % match.groups(0)[0])
                return (series_name, int(match.groups(0)[0]))
            else:
                self.log.info('Series: %s, Index not found' % series_name)
                return (series_name, None)
        else:
            self.log.info('Series node not found')
        return (None, None)

    def parse_tags(self, root):
        tags = []
        tags_nodes = root.xpath('//div[@id="kniha_info"]/div/p[starts-with(text(),"Kategorie:")]/a')
        if tags_nodes:
            for node in tags_nodes:
                tags.append(node.text)
        return tags

    def get_editions(self):
        url_parts = self.url.split('#')
        if len(url_parts) == 2:
            base_url, edition_year = url_parts
        else:
            base_url = url_parts[0]
            edition_year = None
        url = '%s/vydani' % (base_url)
        try:
            self.log.info('Legie url: %r' % url)
            raw = self.browser.open_novisit(url, timeout=self.timeout).read().strip()
        except Exception as e:
            if callable(getattr(e, 'getcode', None)) and \
                    e.getcode() == 404:
                self.log.error('URL malformed: %r' % url)
                return
            attr = getattr(e, 'args', [None])
            attr = attr if attr else [None]
            if isinstance(attr[0], socket.timeout):
                msg = 'Legie timed out. Try again later.'
                self.log.error(msg)
            else:
                msg = 'Failed to make details query: %r' % url
                self.log.exception(msg)
            return

        raw = raw.decode('utf-8', errors='replace')
        # open('E:\\t3.html', 'wb').write(raw)

        if '<title>404 - ' in raw:
            self.log.error('URL malformed: %r' % url)
            return

        try:
            root = fromstring(clean_ascii_chars(raw))
        except:
            msg = 'Failed to parse Legie details page: %r' % url
            self.log.exception(msg)
            return

        self.log.info('Trying to parse editions')
        try:
            editions = self.parse_editions(root, edition_year)
        except:
            self.log.exception('Failed to parse editions page')
            editions = []

        return editions

    def parse_editions(self, root, edition_year):
        editions = []
        edition_nodes = root.xpath('//div[@id="vycet_vydani"]/div[@class="vydani cl"]')
        year = cover_url = publisher = isbn = None
        if self.pubdate:
            edition_year = self.pubdate
        if edition_nodes:
            for node in edition_nodes:
                year_node = node.xpath('./h3/a/text()')
                if year_node:
                    year = year_node[0]
                cover_node = node.xpath('./div[@class="ob"]/img/@src')
                if cover_node:
                    if cover_node[0] != 'images/kniha-neni.jpg':
                        cover_url = 'http://www.legie.info/' + cover_node[0]
                publisher_node = node.xpath('./div[@class="data_vydani"]/a[@class="large"]/text()')
                if publisher_node:
                    publisher = publisher_node[0]
                isbn_node = node.xpath(
                    './/span[@title="ISBN-International Serial Book Number / mezinarodni unikatni cislo knihy"]/following-sibling::text()')
                if isbn_node:
                    match = re.search('([0-9\-xX]+)', isbn_node[0])
                    if match:
                        isbn = match.groups(0)[0].upper()
                approx_date_node = node.xpath('./div[@class="data_vydani"]/table/tbody/tr/td[contains(text(), "přibližné")]/text()')
                if approx_date_node:
                    approx_date = approx_date_node[0]
                    date_pattern = r'\b(\d{2})\.(\d{2})\.(\d{4})\b'
                    date_found = re.search(date_pattern, approx_date)
                    if date_found:
                        date_final = None
                        try:
                            ap_day, ap_month, ap_year = date_found.group(1), date_found.group(2), date_found.group(3)
                            if ap_day == '00':
                                ap_day = '01'
                            date_final = self.prepare_date(int(ap_year), int(ap_month), int(ap_day))
                        except:
                            self.log.exception('Failed to parse approx date')
                        if date_final:
                            if year == edition_year:
                                return [(date_final, cover_url, publisher, isbn)]
                            editions.append((date_final, cover_url, publisher, isbn))
                            continue

                if year == edition_year:
                    return [(self.prepare_date(int(year)), cover_url, publisher, isbn)]
                editions.append((self.prepare_date(int(year)), cover_url, publisher, isbn))
        else:
            self.log.info("No edition nodes")
        return editions

    def prepare_date(self, year, month=1, day=1):
        from calibre.utils.date import utc_tz
        return datetime.datetime(year, month, day, tzinfo=utc_tz)
