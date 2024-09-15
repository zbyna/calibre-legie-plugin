#!/usr/bin/env python
# vim:fileencoding=UTF-8:ts=4:sw=4:sta:et:sts=4:ai
from __future__ import (unicode_literals, division, absolute_import,
                        print_function)

__license__   = 'GPL v3'
__copyright__ = '2024 seeder'
__docformat__ = 'restructuredtext en'

from threading import Thread
from calibre.ebooks.metadata.sources.prefs import msprefs
from calibre.ebooks.metadata.book.base import Metadata
from datetime import datetime
import re
from calibre.utils.date import utc_tz
from lxml.html import tostring

from .shared.utils import load_url, strip_accents
from .shared.prefs import PluginPrefsName, MetadataIdentifier
from .prefs import get_pref

class Worker(Thread): # Get details
    '''
    Get book details from legie.cz book page in a separate thread
    '''

    def __init__(self, url, result_queue, browser, log, relevance, plugin, timeout=20):
        Thread.__init__(self)
        self.daemon = True
        self.url, self.result_queue = url, result_queue
        self.log, self.timeout = log, timeout
        self.relevance, self.plugin = relevance+1, plugin
        self.browser = browser.clone_browser()
        self.cover_url = self.legie_id = None
        self.cover_urls = None

        self.is_tale = True if '/povidka/' in url else False

    def run(self):
        self.log.info('Worker [%s] started.'%self.relevance)
        try:
            self.get_details()
        except:
            self.log.exception('*** get_details failed for url: %r'%self.url)

    def get_details(self):
        try:
            self.log.info('Get main parsing page: %s'%self.url)
            root, _ = load_url(self.log, self.url, self.browser)

            self.log.info('Get additional details: %s%s'%(self.url, '/vydani'))
            additional, _ = load_url(self.log, '%s%s'%(self.url, '/vydani'), self.browser)
            if root.xpath('//ul[@id="zalozky"]/li/a[contains(text(), "ocenění")]'):
                root_rewards, _ = load_url(self.log, '%s%s'%(self.url, '/oceneni'), self.browser)
            else:
                root_rewards = None
            if root.xpath('//ul[@id="zalozky"]/li/a[contains(text(), "povídky")]'):
                root_tales, _ = load_url(self.log, '%s%s'%(self.url, '/povidky'), self.browser)
            else:
                root_tales = None

        except Exception as e:
            self.log.error('Load url problem: %r - %s' % (self.url, e))
            additional = root_rewards = root_tales = None
            return

        # Saving main details into Metadata object
        mi = Metadata("")
        
        mi = self.parse_main_details(root, mi)
        mi = self.parse_sep_pages(mi, root_tales, root_rewards)
        if self.is_tale:
            mi.translators = []
            mi.illustrators = []
            mi.cover_authors = []
            mi.edition = mi.edition_index = mi.pages = mi.mi_publisher = \
            mi.mi_pubdate = mi.pubyear = mi.mi_isbn = mi.ean = \
            mi.mi_language = mi.dimensions = mi.print_run = mi.issue_number = \
            mi.note = mi.cover_type = mi.external_links = mi.price = mi.cover_url = None
            mi.source_relevance = self.relevance
            mi = self.field_metadata_build(root, mi)
            self.result_queue.put(mi)
        else:
            mi_list = self.parse_issue_details(additional, mi)
            mi_list = [self.field_metadata_build(root, m) for m in mi_list]
            mi_list = self.find_duplicate_issue(mi_list)
            if mi_list:
                mi = self.select_best_issue(mi_list)
                self.result_queue.put(mi)
        
    def get_parse_obalkyknih_cover(self, isbn):
        url_obalky = 'https://www.obalkyknih.cz/view?isbn=%s'%isbn

        try:
            self.log.info('Get obalkyknih page:%s'%url_obalky)
            root, _ = load_url(self.log, url_obalky, self.browser)
        except Exception as e:
            self.log.error('Load url problem: %r - %s' % (url_obalky, e))
            return
        cover_url = self.parse_first(root, '//a[@data-lightbox="book-cover"]/@href', 'obalkyknih_cover')
        if cover_url:
            return cover_url
        else:
            return None

    def parse_main_details(self, root, mi):
        ## Main details parsing
        self.log.info('Parse details:%s'%self.url)
        try:
            mi.mi_id = self.parse_legie_id(root)
            self.log.info('Parsed Legie identifier:%s'%mi.mi_id)
        except:
            self.log.exception('Error parsing legie id for url: %r'%self.url)

        try:
            mi.mi_title = self.parse_title(root)
            self.log.info('Parsed title:%s'%mi.mi_title)
        except:
            mi.mi_title = ''
            self.log.exception('Error parsing title for url: %r'%self.url)

        try:
            mi.subtitle = self.parse_subtitle(root)
            self.log.info('Parsed subtitle:%s'%mi.subtitle)
        except:
            self.log.exception('Error parsing title for url: %r'%self.url)
        
        try:
            mi.mi_authors = self.parse_authors(root)
            self.log.info('Parsed authors:%s'%mi.mi_authors)
        except:
            self.log.exception('Error parsing authors for url: %r'%self.url)

        try:
            mi.rating_star, mi.rating10, mi.rating100, mi.rating_count = self.parse_rating(root)
            mi.rating = mi.rating_star if mi.rating_star else 0
            self.log.info('Parsed rating:%s'%mi.rating)
        except:
            self.log.exception('Error parsing rating for url: %r'%self.url)

        try:
            mi.category = self.parse_category(root)
        except:
            self.log.exception('Error parsing tags or category for url: %r'%self.url)
   
        try:
            mi.mi_series, mi.mi_series_index = self.parse_series(root)
            self.log.info('Parsed series:%s'%mi.mi_series)
            self.log.info('Parsed series index:%s'%mi.mi_series_index)
        except Exception as e:
            self.log.exception('Error parsing series for url: %r - %s'%(self.url, e))

        try:
            mi.original_title = self.parse_origTitle(root)
        except:
            self.log.exception('Error parsing original title and year for url: %r'%self.url)

        try:
            mi.alt_original_title = self.parse_altTitle(root)
        except:
            self.log.exception('Error parsing alt original title and year for url: %r'%self.url)

        try:
            mi.world = self.parse_world(root)
            self.log.info('Parsed world:%s'%mi.world)
        except:
            self.log.exception('Error parsing title for url: %r'%self.url)

        try:
            mi.alt_title = self.parse_alt_titles(root)
            self.log.info('Parsed alt_title:%s'%mi.alt_title)
        except:
            self.log.exception('Error parsing alt_title for url: %r'%self.url)

        try:
            mi.contained_in = self.parse_contained_in(root)
            self.log.info('Parsed contained_in:%s'%mi.contained_in)
        except:
            self.log.exception('Error parsing contained_in for url: %r'%self.url)

        try:
            mi.sep_published = self.parse_sep_published(root)
            self.log.info('Parsed sep_published:%s'%mi.sep_published)
        except:
            self.log.exception('Error parsing sep_published for url: %r'%self.url)

        try:
            mi.original_date = self.parse_origDate(root)
            if mi.original_date and '/' in mi.original_date:
                org_date_splited = mi.original_date.split('/')
                if len(org_date_splited) == 2:
                    mi.original_month = org_date_splited[0]
                    mi.original_year = org_date_splited[1]
            elif mi.original_date and len(mi.original_date) == 4:
                mi.original_year = mi.original_date
                mi.original_month = '01'
            else:
                mi.original_year = mi.original_month = None
        except:
            self.log.exception('Error parsing original title and year for url: %r'%self.url)

        try:
            mi.mi_comments = self.parse_comments(root)
            self.log.info('Parsed comments:%s'%mi.mi_comments)
        except:
            self.log.exception('Error parsing comments for url: %r'%self.url)

        try:
            mi.external_links = self.parse_external_links(root)
            self.log.info('Parsed external_links:%s'%mi.external_links)
        except:
            self.log.exception('Error parsing external links for url: %r'%self.url)
        return mi

    def parse_sep_pages(self, mi, root_tales = None, root_rewards = None):
        try:
            if root_rewards:
                mi.awards = self.parse_awards(root_rewards)
            else:
                mi.awards = []
        except:
            self.log.exception('Error parsing awards for url: %r'%self.url)
            mi.awards = []
        try:
            if root_tales:
                mi.tales_in_book = self.parse_tales_list(root_tales)
            else:
                mi.tales_in_book = []
        except:
            self.log.exception('Error parsing tales_in_book.')
            mi.tales_in_book = []

        return mi

    def parse_issue_details(self, root, mi_base):
        self.log.info('Parsing issues...')
        mi_node_list = root.xpath('//div[@id="vycet_vydani"]/div[@class="vydani cl"]')
        mi_res_issues = []
        for i, mi_node in enumerate(mi_node_list):
            mi = mi_base.deepcopy()
            mi.source_relevance = float('%d.%d'%(self.relevance, i))
            ####### ISSUE SPECIFIC
            try:
                mi.illustrators = self.parse_illustrators(mi_node)
                mi.illustrators = [mi.illustrators] if mi.illustrators else []
                self.log.info('Parsed illustrators:%s'%mi.illustrators)
            except:
                self.log.exception('Error parsing illustrators for url: %r'%self.url)
                
            try:
                mi.cover_authors = self.parse_cover_authors(mi_node)
                mi.cover_authors = [mi.cover_authors] if mi.cover_authors else []
                self.log.info('Parsed cover authors:%s'%mi.cover_authors)
            except:
                self.log.exception('Error parsing cover authors for url: %r'%self.url)
                
            try:
                mi.translators = self.parse_translators(mi_node)
                mi.translators = [mi.translators] if mi.translators else []
                self.log.info('Parsed translators:%s'%mi.translators)
            except:
                self.log.exception('Error parsing translators for url: %r'%self.url)

            try:
                mi.edition, mi.edition_index = self.parse_editions(mi_node)
                self.log.info('Edition %s'%mi.edition)
                self.log.info('Edition index %s'%mi.edition_index)
            except:
                self.log.exception('Error parsing editions for url: %r'%self.url)
                
            try:
                mi.pages = self.parse_pages(mi_node)
                self.log.info('Pages %s'%mi.pages)
            except:
                self.log.exception('Error parsing pages number for url: %r'%self.url)

            try:
                mi.mi_publisher = self.parse_publisher(mi_node)
                self.log.info('Parsed publisher: %s'%mi.mi_publisher)
            except:
                self.log.exception('Error parsing publisher for url: %r'%self.url)
                
            try:
                mi.mi_pubdate, mi.pubyear = self.parse_pubdate(mi_node)
                self.log.info('Parsed pubdate:%s'%mi.mi_pubdate)
            except:
                self.log.exception('Error parsing pubdate for url: %r'%self.url)

            try:
                mi.mi_isbn = self.parse_isbn(mi_node)
                self.log.info('Parsed isbn:%s'%mi.mi_isbn)
            except:
                self.log.exception('Error parsing ISBN for url: %r'%self.url)

            try:
                mi.ean = self.parse_ean(mi_node)
                self.log.info('Parsed ean:%s'%mi.ean)
            except:
                self.log.exception('Error parsing EAN for url: %r'%self.url)

            try:
                mi.mi_language = self.parse_languages(mi_node)
                self.log.info('Parsed lang:%s'%mi.mi_language)
            except:
                self.log.exception('Error parsing lang for url: %r'%self.url)

            try:
                mi.dimensions = self.parse_dimensions(mi_node)
                self.log.info('Parsed dimensions:%s'%mi.dimensions)
            except:
                self.log.exception('Error parsing dimensions for url: %r'%self.url)
            
            try:
                mi.print_run = self.parse_print_run(mi_node)
                self.log.info('Parsed print_run:%s'%mi.print_run)
            except:
                self.log.exception('Error parsing print_run for url: %r'%self.url)
            
            try:
                mi.price = self.parse_price(mi_node)
                self.log.info('Parsed price:%s'%mi.price)
            except:
                self.log.exception('Error parsing price for url: %r'%self.url)

            try:
                mi.issue_number = self.parse_issue_number(mi_node)
                self.log.info('Parsed issue_number:%s'%mi.issue_number)
            except:
                self.log.exception('Error parsing issue_number for url: %r'%self.url)

            try:
                mi.note = self.parse_note(mi_node)
                self.log.info('Parsed note:%s'%mi.note)
            except:
                self.log.exception('Error parsing note for url: %r'%self.url)

            try:
                mi.cover_type = self.parse_cover_type(mi_node)
                self.log.info('Parsed cover_type:%s'%mi.cover_type)
            except:
                self.log.exception('Error parsing cover_type for url: %r'%self.url)
            
            try:
                mi.cover_url = self.parse_cover(mi_node)
                if mi.cover_url:
                    mi.cover_url = '%s/%s'%(self.plugin.BASE_URL, mi.cover_url)
                self.log.info('Parsed cover:%s'%mi.cover_url)
            except:
                self.log.exception('Error parsing cover_url for url: %r'%self.url)

            try:
                self.cover_urls = self.parse_cover_list(mi_node)
                if self.cover_urls:
                    self.cover_urls = ['%s/%s'%(self.plugin.BASE_URL, cover) for cover in self.cover_urls]
                self.log.info('Parsed cover:%s'%self.cover_urls)
            except:
                self.cover_urls = None
                self.log.exception('Error parsing cover_urls for url: %r'%self.url)

            mi_res_issues.append(mi)
        
        return mi_res_issues
    
    def find_duplicate_issue(self, mi_list):
        # No duplicates
        if len(mi_list) == 1:
            return mi_list

        dupli = dict()
        for i, mi in enumerate(mi_list):
            title_token = ''.join([mi.title if mi.title else '', ''.join(mi.authors if mi.authors else [])])
            if dupli.get(title_token, None):
                dupli[title_token].append(i)
            else:
                dupli[title_token] = [i]
        idx_deleting = []
        for k, v in dupli.items():
            if len(v) == 1:
                self.result_queue.put(mi_list[v[0]])
                idx_deleting.append(v[0])
        mi_list = [item for idx, item in enumerate(mi_list) if idx not in idx_deleting]
        return mi_list

    def select_best_issue(self, mi_list):
         # 0:default - 1:cz_new - 2:cz_old - 3:sk_new - 4:sk_old

        wanted_lang = self.plugin.identifiers.get('language', None)
        wanted_pubyear = self.plugin.identifiers.get('pubdate', None)
        wanted_publisher = self.plugin.identifiers.get('publisher', None)

        if not wanted_lang and not wanted_publisher and not wanted_pubyear and \
            get_pref(PluginPrefsName.ISSUE_PREFERENCE) == 0 and get_pref(PluginPrefsName.MAX_COVERS) <= 1:
            self.log.info('No need for special issue merging. '
                          'Keeping all issues for built-in merging methods.')
            return mi_list[0] if mi_list else None

        # preference lang cs
        wanted_lang = 'cs' if wanted_lang is None and \
            get_pref(PluginPrefsName.ISSUE_PREFERENCE) in (1, 2) else wanted_lang
        # preference lang sk
        wanted_lang = 'sk' if wanted_lang is None and \
            get_pref(PluginPrefsName.ISSUE_PREFERENCE) in (3, 4) else wanted_lang

        year_node = [int(mi.pubyear) for mi in mi_list]
        # preference pubdate newest
        if not wanted_pubyear and year_node and \
            get_pref(PluginPrefsName.ISSUE_PREFERENCE) in (1, 3):
            wanted_pubyear = max(year_node)
        # preference pubdate oldest
        elif not wanted_pubyear and year_node and \
            get_pref(PluginPrefsName.ISSUE_PREFERENCE) in (2, 4):
            wanted_pubyear = min(year_node)
        
        best_issue = None
        best_relevance = 10_000 # MAX_VAL
        for issue_index, mi in enumerate(mi_list):

            # Calculate relevance of each book issue
            relevance = 3
            if mi.mi_language and wanted_lang and mi.mi_language == wanted_lang:
                relevance -= 1
            elif mi.mi_language != wanted_lang:
                relevance += 1_000

            if mi.mi_publisher and wanted_publisher:
                # compare with remapped version
                c_mi_publisher = self._convert_to_calibre(mi.mi_publisher,
                                                            get_pref(PluginPrefsName.KEY_PUBLISHER_MAPPINGS),
                                                            get_pref(PluginPrefsName.PUBLISHER_FILTER))
                c_wanted_publisher = self._convert_to_calibre(wanted_publisher.replace('_', ' '),
                                                                get_pref(PluginPrefsName.KEY_PUBLISHER_MAPPINGS),
                                                                get_pref(PluginPrefsName.PUBLISHER_FILTER))
                if c_mi_publisher and c_wanted_publisher and \
                    (strip_accents(c_wanted_publisher.lower().replace('_', '')) == strip_accents(c_mi_publisher.lower().replace('_', '')) or\
                    strip_accents(c_wanted_publisher.lower().replace('_', '')) in strip_accents(c_mi_publisher.lower().replace('_', '')) or\
                    strip_accents(c_mi_publisher.lower().replace('_', '')) in strip_accents(c_wanted_publisher.lower().replace('_', ''))):
                    relevance -= 2
                else:
                    relevance += 1_000
            self.log(mi.pubyear, wanted_pubyear)
            if mi.pubyear and wanted_pubyear:
                relevance += abs(int(mi.pubyear) - int(wanted_pubyear))

            self.log.info(relevance)
            # Save index of best relevance issue
            if relevance < best_relevance:
                best_issue = issue_index
                best_relevance = relevance
                self.log('best index: %s'%best_issue)

        if best_issue is not None:
            self.cover_url = mi_list[best_issue].cover_url
            #self.cover_urls = img_urls
            return mi_list[best_issue]
        else:
            return mi_list[0]

    def field_metadata_build(self, root, mi):
        # keep only info for issue specify
        mi_result = Metadata('')
        mi_result.pubyear = mi.pubyear
        mi_result.mi_publisher = mi.mi_publisher
        mi_result.mi_language = mi.mi_language
        mi_result.cover_url = mi.cover_url

        # User defined options
        max_covers = get_pref(PluginPrefsName.MAX_COVERS)
        obalkyknih_cover = get_pref(PluginPrefsName.OBALKYKNIH_COVER)
        append_to_comments = get_pref(PluginPrefsName.APPEND_TO_COMMENTS)
        publication_date = get_pref(PluginPrefsName.PUBLICATION_DATE)
        swap_authors = get_pref(PluginPrefsName.SWAP_AUTHORS)
        only_one_author = get_pref(PluginPrefsName.ONE_AUTHOR)
        author_role = get_pref(PluginPrefsName.AUTHOR_ROLE)
  
        title_line = get_pref(PluginPrefsName.TITLE_LINE)
        publisher_line = get_pref(PluginPrefsName.PUBLISHER_LINE)
        series_line = get_pref(PluginPrefsName.SERIES_LINE)
        series_index_field = get_pref(PluginPrefsName.SERIES_INDEX_FIELD)

        append_to_tags = get_pref(PluginPrefsName.APPEND_TO_TAG)
        append_to_identifiers = get_pref(PluginPrefsName.APPEND_TO_IDENTIFIERS)
        authors_include = get_pref(PluginPrefsName.AUTHORS_INCLUDE)
        translators_include = get_pref(PluginPrefsName.TRANSLATORS_INCLUDE)
        illustrators_include = get_pref(PluginPrefsName.ILLUSTRATORS_INCLUDE)
        cover_authors_include = get_pref(PluginPrefsName.COVER_AUTHORS_INCLUDE)

        if mi.mi_id and dict([[tupl[0], tupl[1]] for tupl in append_to_identifiers]).get(MetadataIdentifier.ORIG_ID, True):
            if self.is_tale:
                mi_result.set_identifier('legie_povidka', mi.mi_id)
                self.legie_id = mi.mi_id
            else:
                if mi.pubyear:
                    mi_result.set_identifier('legie', '%s#%s'%(mi.mi_id, mi.pubyear))
                    mi_result.mi_id = '%s#%s'%(mi.mi_id, mi.pubyear)
                    self.legie_id = '%s#%s'%(mi.mi_id, mi.pubyear)
                    mi.mi_id = '%s#%s'%(mi.mi_id, mi.pubyear)
                else:
                    mi_result.mi_id = mi.mi_id
                    mi_result.set_identifier('legie', mi.mi_id)
                    self.legie_id = mi.mi_id

                if mi.ean and dict([[tupl[0], tupl[1]] for tupl in append_to_identifiers]).get(MetadataIdentifier.EAN, True):
                    mi_result.set_identifier('ean', mi.ean)

                if mi.mi_id:
                    self.plugin.cache_isbn_to_identifier(mi.mi_isbn, mi.mi_id)
            
        mi_result.rating = mi.rating_star if mi.rating_star else 0

        try:
            # 0: found book pubdate, 1: first book pubdate
            if publication_date == 0 and mi.mi_pubdate:
                mi_result.pubdate = mi.mi_pubdate
            elif publication_date == 1 and mi.original_year:
                mi_result.pubdate = datetime(int(mi.original_year), 1, 1, tzinfo=utc_tz)
        except:
            self.log.exception('Error adding published date.')
        
        try:
            mi_result.comments = ''
            # append_to_comments - list of tuples
            # (id_string, check_bool, visible_desc)
            def get_comment_variable(argument):
                if argument == MetadataIdentifier.DESCRIPTION and mi.mi_comments:
                    return mi.mi_comments
                elif argument == MetadataIdentifier.HR:
                    return '<hr>'
                elif argument == MetadataIdentifier.PAGES and mi.pages:
                    return '<p id="numberOfPages"><em>Počet stran:</em> %s</p>' %mi.pages
                elif argument == MetadataIdentifier.PRINT_RUN and mi.print_run:
                    return '<p id="printRun"><em>Náklad (ks):</em> %s</p>' %mi.print_run
                elif argument == MetadataIdentifier.DIMENSIONS and mi.dimensions:
                    return '<p id="dimensions"><em>Rozměry:</em> %s</p>' %mi.dimensions
                elif argument == MetadataIdentifier.COVER_TYPE and mi.cover_type:
                    return '<p id="coverType"><em>Vazba:</em> %s</p>' %mi.cover_type
                elif argument == MetadataIdentifier.NOTE and mi.note:
                    return '<p id="note"><em>Poznámka:</em> %s</p>' %mi.note
                elif argument == MetadataIdentifier.ISSUE_NUMBER and mi.issue_number:
                    return '<p id="issueNumber"><em>Vydání:</em> %s</p>' %mi.issue_number
                elif argument == MetadataIdentifier.PRICE and mi.price:
                    return '<p id="price"><em>Cena:</em> %s</p>' %mi.price
                elif argument == MetadataIdentifier.TITLE and mi.mi_title:
                    return '<p id="title"><em>Název:</em> %s</p>' %mi.mi_title
                elif argument == MetadataIdentifier.SUBTITLE and mi.subtitle:
                    return '<p id="subtitle"><em>Podtitul:</em> %s</p>' %mi.subtitle
                elif argument == MetadataIdentifier.ORIGINAL_TITLE and mi.original_title:
                    return '<p id="origTitle"><em>Původní název:</em> %s</p>' %mi.original_title
                elif argument == MetadataIdentifier.ALT_ORIGINAL_TITLE and mi.alt_original_title:
                    return '<p id="altOrigTitle"><em>Joný (obecně známý) název:</em> %s</p>' %mi.alt_original_title
                elif argument == MetadataIdentifier.ORIGINAL_YEAR and mi.original_year:
                    return '<p id="origYear"><em>Rok prvního vydání:</em> %s</p>' %mi.original_year
                elif argument == MetadataIdentifier.PUB_YEAR and mi.pubyear:
                    return '<p id="pubYear"><em>Rok vydání:</em> %s</p>' %mi.pubyear
                elif argument == MetadataIdentifier.PUBLISHER and mi.mi_publisher:
                    return '<p id="publisher"><em>Vydavatel:</em> %s</p>' %mi.mi_publisher
                elif argument == MetadataIdentifier.WORLD and mi.world:
                    return '<p id="world"><em>Svět:</em> %s</p>' %mi.world
                elif argument == MetadataIdentifier.RATING and mi.rating100:
                    return '<p id="rating100"><em>Hodnocení (%%):</em> %s</p>' %mi.rating100
                elif argument == MetadataIdentifier.RATING10 and mi.rating10:
                    return '<p id="rating10"><em>Hodnocení (0-10):</em> %s</p>' %mi.rating10
                elif argument == MetadataIdentifier.RATING5 and mi.rating_star:
                    return '<p id="rating5"><em>Hodnocení (0-5):</em> %s</p>' %mi.rating_star
                elif argument == MetadataIdentifier.RATING_COUNT and mi.rating_count:
                    return '<p id="ratingCount"><em>Počet hodnocení:</em> %s</p>' %mi.rating_count
                elif argument == MetadataIdentifier.LANGUAGE and mi.mi_language:
                    return '<p id="language"><em>Jazyk vydání:</em> %s </p>' %mi.mi_language
                elif argument == MetadataIdentifier.ISBN and mi.mi_isbn:
                    return '<p id="isbn"><em>ISBN:</em> %s </p>' %mi.mi_isbn
                elif argument == MetadataIdentifier.EAN and mi.ean:
                    return '<p id="ean"><em>EAN:</em> %s </p>' %mi.ean
                elif argument == MetadataIdentifier.ORIG_ID and mi.mi_id and not self.is_tale:
                    return '<p id="legie"><em>legie:</em> %s</p>' %mi.mi_id
                elif argument == MetadataIdentifier.ORIG_ID and mi.mi_id and self.is_tale:
                    return '<p id="legie_povidka"><em>legie povídka:</em> %s</p>' %mi.mi_id
                elif argument == MetadataIdentifier.SOURCE_RELEVANCE and mi.source_relevance:
                    return '<p id="relevance"><em>Pořadí ve vyhledávání:</em> %s</p>' %mi.source_relevance
                elif argument == MetadataIdentifier.SERIES and mi.mi_series:
                    if mi.mi_series_index:
                        return '<p id="series"><em>Série:</em> %s [%s]</p>' %(mi.mi_series, mi.mi_series_index)
                    else:
                        return '<p id="series"><em>Série:</em> %s</p>' %mi.mi_series
                elif argument == MetadataIdentifier.EDITION and mi.edition:
                    if mi.edition_index:
                        return '<p id="edition"><em>Edice:</em> %s [%s]</p>' %(mi.edition, mi.edition_index)
                    else:
                        return '<p id="edition"><em>Edice:</em> %s</p>' %mi.edition
                elif argument == MetadataIdentifier.CONTAINED_IN and mi.contained_in:
                    return '<p id="containedIn"><em>Součástí knih:</em> <br>%s</p>'%('<br>'.join(mi.contained_in))
                elif argument == MetadataIdentifier.SEP_PUBLISHED and mi.sep_published:
                    return '<p id="sepPublished"><em>Vydáno i samostatně jako:</em> %s</p>'%(', '.join(mi.sep_published))
                elif argument == MetadataIdentifier.ALT_TITLE and mi.alt_title:
                    return '<p id="altTitleList"><em>Vydáno i pod názvy:</em> %s</p>'%(', '.join(mi.alt_title))
                elif argument == MetadataIdentifier.AUTHORS and mi.mi_authors:
                    return '<p id="authors"><em>Autoři:</em> %s</p>'%(' & '.join(mi.mi_authors))
                elif argument == MetadataIdentifier.TRANSLATION and mi.translators:
                    return '<p id="translator"><em>Překlad:</em> %s</p>'%(' & '.join(mi.translators))
                elif argument == MetadataIdentifier.ILLUSTRATION and mi.illustrators:
                    return '<p id="illustrators"><em>Ilustrace:</em> %s</p>'%(' & '.join(mi.illustrators))
                elif argument == MetadataIdentifier.COVER_AUTHORS and mi.cover_authors:
                    return '<p id="coverAuthors"><em>Autoři obálky:</em> %s</p>'%(' & '.join(mi.cover_authors))
                elif argument == MetadataIdentifier.CATEGORY and mi.category:
                    return '<p id="category"><em>Kategorie:</em> %s</p>' %', '.join(mi.category)
                elif argument == MetadataIdentifier.AWARDS and mi.awards:
                    return '<p id="awards"><em>Ocenění:</em> <br>%s</p>' %'<br>'.join(mi.awards)
                elif argument == MetadataIdentifier.TALES_IN_BOOK and mi.tales_in_book:
                    return '<p id="bookParts"><em>Části díla:</em> <br>%s</p>' %'<br>'.join(mi.tales_in_book)
                elif argument == MetadataIdentifier.EXTERNAL_LINKS and mi.external_links:
                    return '<p id="externalLinks"><em>Externí odkazy:</em> <br>%s</p>' %mi.external_links
                else:
                    return ''
            
            self.log.info('append to comments:', append_to_comments)
            for item in append_to_comments:
                if item[1]:
                    argument = item[0]
                    # converts parsed information into html paragraph string
                    mi_result.comments = '%s %s'%(mi_result.comments, get_comment_variable(item[0]))
        except:
            self.log.exception('Error adding more info to comments for url: %r'%self.url)
            mi.comments = mi.mi_comments
                    
        try:
            def get_tag_variable(argument):
                switch_check = {
                    MetadataIdentifier.CATEGORY: mi.category,
                    MetadataIdentifier.PAGES: mi.pages,
                    MetadataIdentifier.AUTHORS: mi.mi_authors,
                    MetadataIdentifier.TRANSLATION: mi.translators,
                    MetadataIdentifier.ILLUSTRATION: mi.illustrators,
                    MetadataIdentifier.COVER_AUTHORS: mi.cover_authors,
                    MetadataIdentifier.TITLE: mi.mi_title,
                    MetadataIdentifier.ORIGINAL_TITLE: mi.original_title,
                    MetadataIdentifier.ORIGINAL_YEAR: mi.original_year,
                    MetadataIdentifier.PUB_YEAR: mi.pubyear,
                    MetadataIdentifier.PUBLISHER: mi.mi_publisher,
                    MetadataIdentifier.SERIES: (mi.mi_series, mi.mi_series_index),
                    MetadataIdentifier.EDITION: (mi.edition, mi.edition_index),
                    MetadataIdentifier.RATING: mi.rating100,
                    MetadataIdentifier.RATING5: mi.rating_star,
                    MetadataIdentifier.RATING10: mi.rating10,
                    MetadataIdentifier.RATING_COUNT: mi.rating_count,
                    MetadataIdentifier.ISBN: mi.mi_isbn,
                    MetadataIdentifier.EAN: mi.ean,
                    MetadataIdentifier.LANGUAGE: mi.mi_language,
                    MetadataIdentifier.PRICE: mi.price,
                    MetadataIdentifier.DIMENSIONS: mi.dimensions,
                    MetadataIdentifier.PRINT_RUN: mi.print_run,
                    MetadataIdentifier.ISSUE_NUMBER: mi.issue_number,
                    MetadataIdentifier.ALT_TITLE: mi.alt_title,
                    MetadataIdentifier.SEP_PUBLISHED: mi.sep_published,
                    MetadataIdentifier.CONTAINED_IN: mi.contained_in,
                    MetadataIdentifier.WORLD: mi.world,
                    MetadataIdentifier.ALT_ORIGINAL_TITLE: mi.alt_original_title,
                    MetadataIdentifier.SUBTITLE: mi.subtitle,
                    MetadataIdentifier.ORIG_ID: mi.mi_id,
                    MetadataIdentifier.AWARDS: mi.awards,
                    MetadataIdentifier.COVER_TYPE: mi.cover_type,
                    MetadataIdentifier.NOTE: mi.note,
                    MetadataIdentifier.EXTERNAL_LINKS: mi.external_links,
                    MetadataIdentifier.TALES_IN_BOOK: mi.tales_in_book,
                    MetadataIdentifier.SOURCE_RELEVANCE: mi.source_relevance,
                }
                switch = {
                    MetadataIdentifier.CATEGORY: mi.category,
                    MetadataIdentifier.PAGES: ['Počet stran: %s' %mi.pages],
                    MetadataIdentifier.EAN: ['EAN: %s' %mi.ean],
                    MetadataIdentifier.COVER_TYPE: ['Vazba: %s' %mi.cover_type],
                    MetadataIdentifier.LANGUAGE: ['Jazyk vydání: %s' %mi.mi_language],
                    MetadataIdentifier.PRICE: ['Cena: %s' %mi.price],
                    MetadataIdentifier.DIMENSIONS: ['Rozměry: %s' %mi.dimensions],
                    MetadataIdentifier.PRINT_RUN: ['Náklad (ks): %s' %mi.print_run],
                    MetadataIdentifier.ISSUE_NUMBER: ['Vydání: %s' %mi.issue_number],
                    MetadataIdentifier.WORLD: ['Svět: %s' %mi.world],
                    MetadataIdentifier.ORIGINAL_YEAR: ['Rok prvního vydání: %s' %mi.original_year],
                    MetadataIdentifier.PUB_YEAR: ['Rok vydání: %s' %mi.pubyear],
                    MetadataIdentifier.RATING: ['Hodnocení (%%): %s' %mi.rating100],
                    MetadataIdentifier.RATING5: ['Hodnocení (0-5): %s' %mi.rating_star],
                    MetadataIdentifier.RATING10: ['Hodnocení (0-10): %s' %mi.rating10],
                    MetadataIdentifier.RATING_COUNT: ['Počet hodnocení: %s' %mi.rating_count],
                    MetadataIdentifier.ISBN: ['ISBN: %s' %mi.mi_isbn],
                    MetadataIdentifier.SOURCE_RELEVANCE: ['Pořadí ve vyhledávání: %s' %mi.source_relevance]
                }
                if switch_check.get(argument, None):
                    if argument == MetadataIdentifier.ORIG_ID and mi.mi_id and self.is_tale:
                        return ['legie povídka: %s' %mi.mi_id.replace(',', ';')]
                    if argument == MetadataIdentifier.ORIG_ID and mi.mi_id and not self.is_tale:
                        return ['legie: %s' %mi.mi_id.replace(',', ';')]
                    if argument == MetadataIdentifier.TITLE and mi.mi_title:
                        return ['Název: %s' %mi.mi_title.replace(',', ';')]
                    elif argument == MetadataIdentifier.SUBTITLE and mi.subtitle:
                        return ['Podtitul: %s' %mi.subtitle.replace(',', ';')]
                    elif argument == MetadataIdentifier.PUBLISHER and mi.mi_publisher:
                        return ['Vydavatel: %s' %mi.mi_publisher.replace(',', ';')]
                    elif argument == MetadataIdentifier.ORIGINAL_TITLE and mi.original_title:
                        return ['Původní název: %s' %mi.original_title.replace(',', ';')]
                    elif argument == MetadataIdentifier.NOTE and mi.note:
                        return ['Poznámka: %s' %mi.note.replace(',', ';')]
                    elif argument == MetadataIdentifier.DIMENSIONS and mi.dimensions:
                        return ['Rozměry: %s' %mi.dimensions.replace(',', ';')]
                    elif argument == MetadataIdentifier.PRINT_RUN and mi.print_run:
                        return ['Náklad (ks): %s' %mi.print_run.replace(',', ';')]
                    elif argument == MetadataIdentifier.ISSUE_NUMBER and mi.issue_number:
                        return ['Vydání: %s' %mi.issue_number.replace(',', ';')]
                    elif argument == MetadataIdentifier.COVER_TYPE and mi.cover_type:
                        return ['Vazba: %s' %mi.cover_type.replace(',', ';')]
                    elif argument == MetadataIdentifier.EDITION and mi.edition:
                        if mi.edition_index:
                            return ['Edice: %s [%s]' %(mi.edition, mi.edition_index)]
                        else:
                            return ['Edice: %s' %mi.edition]
                    elif argument == MetadataIdentifier.SERIES and mi.mi_series:
                        if mi.mi_series_index:
                            return ['Série: %s [%s]' %(mi.mi_series, mi.mi_series_index)]
                        else:
                            return ['Série: %s' %mi.mi_series]
                    elif argument == MetadataIdentifier.ALT_ORIGINAL_TITLE and mi.alt_original_title:
                        return ['Jiný (obecně známý) název: %s'%t.replace(',', ';') for t in mi.alt_original_title]
                    elif argument == MetadataIdentifier.SEP_PUBLISHED and mi.sep_published:
                        return ['Vydáno samostatně i jako: %s'%t.replace(',', ';') for t in mi.sep_published]
                    elif argument == MetadataIdentifier.CONTAINED_IN and mi.contained_in:
                        return ['Součástí knihy: %s'%t.replace(',', ';') for t in mi.contained_in]
                    elif argument == MetadataIdentifier.AUTHORS and mi.mi_authors:
                        return ['Autor: %s'%a.replace(',', ';') for a in mi.mi_authors]
                    elif argument == MetadataIdentifier.AUTHORS and mi.mi_authors:
                        return ['Autor: %s'%a.replace(',', ';') for a in mi.mi_authors]
                    elif argument == MetadataIdentifier.TRANSLATION and mi.translators:
                        return ['Překlad: %s'%t.replace(',', ';') for t in mi.translators]
                    elif argument == MetadataIdentifier.ILLUSTRATION and mi.illustrators:
                        return ['Ilustrace: %s'%i.replace(',', ';') for i in mi.illustrators]
                    elif argument == MetadataIdentifier.COVER_AUTHORS and mi.cover_authors:
                        return ['Autor obálky: %s'%a.replace(',', ';') for a in mi.cover_authors]
                    elif argument == MetadataIdentifier.AWARDS and mi.awards:
                        return ['Ocenění: %s'%a.replace(',', ';') for a in mi.awards]
                    elif argument == MetadataIdentifier.TALES_IN_BOOK and mi.tales_in_book:
                        return ['Část díla: %s'%t.replace(',', ';') for t in mi.tales_in_book]
                    elif argument == MetadataIdentifier.ALT_TITLE and mi.alt_title:
                        return ['Vydáno také pod názvem: %s'%t.replace(',', ';') for t in mi.alt_title]
                    else:
                        return switch.get(argument, '')
                return ''

            for item in append_to_tags:
                if item[1]:
                    mi_result.tags.extend(get_tag_variable(item[0]))
        except:
            self.log.exception('Error adding additional tags for url: %r'%self.url)

        
        try:
            def get_identifier_variable(argument):
                switch_check = {
                    MetadataIdentifier.CATEGORY: mi.category,
                    MetadataIdentifier.PAGES: mi.pages,
                    MetadataIdentifier.AUTHORS: mi.mi_authors,
                    MetadataIdentifier.TRANSLATION: mi.translators,
                    MetadataIdentifier.ILLUSTRATION: mi.illustrators,
                    MetadataIdentifier.COVER_AUTHORS: mi.cover_authors,
                    MetadataIdentifier.TITLE: mi.mi_title,
                    MetadataIdentifier.SUBTITLE: mi.subtitle,
                    MetadataIdentifier.ALT_TITLE: mi.alt_title,
                    MetadataIdentifier.ORIGINAL_TITLE: mi.original_title,
                    MetadataIdentifier.ALT_ORIGINAL_TITLE: mi.alt_original_title,
                    MetadataIdentifier.SEP_PUBLISHED: mi.sep_published,
                    MetadataIdentifier.CONTAINED_IN: mi.contained_in,
                    MetadataIdentifier.WORLD: mi.world,
                    MetadataIdentifier.ORIGINAL_YEAR: mi.original_year,
                    MetadataIdentifier.PUB_YEAR: mi.pubyear,
                    MetadataIdentifier.PUBLISHER: mi.mi_publisher,
                    MetadataIdentifier.SERIES: (mi.mi_series, mi.mi_series_index),
                    MetadataIdentifier.EDITION: (mi.edition, mi.edition_index),
                    MetadataIdentifier.RATING: mi.rating100,
                    MetadataIdentifier.RATING5: mi.rating_star,
                    MetadataIdentifier.RATING10: mi.rating10,
                    MetadataIdentifier.RATING_COUNT: mi.rating_count,
                    MetadataIdentifier.ISBN: mi.mi_isbn,
                    MetadataIdentifier.EAN: mi.ean,
                    MetadataIdentifier.LANGUAGE: mi.mi_language,
                    MetadataIdentifier.PRICE: mi.price,
                    MetadataIdentifier.DIMENSIONS: mi.dimensions,
                    MetadataIdentifier.PRINT_RUN: mi.print_run,
                    MetadataIdentifier.ISSUE_NUMBER: mi.issue_number,
                    MetadataIdentifier.ORIG_ID: mi.mi_id,
                    MetadataIdentifier.COVER_TYPE: mi.cover_type,
                    MetadataIdentifier.NOTE: mi.note,
                    MetadataIdentifier.EXTERNAL_LINKS: mi.external_links,
                    MetadataIdentifier.AWARDS: mi.awards,
                    MetadataIdentifier.TALES_IN_BOOK: mi.tales_in_book,
                    MetadataIdentifier.SOURCE_RELEVANCE: mi.source_relevance,
                }
                return switch_check.get(argument, '')
            for item in append_to_identifiers:
                appending = get_identifier_variable(item[0])
                if item[0] in [MetadataIdentifier.CATEGORY, MetadataIdentifier.TAGS, MetadataIdentifier.AWARDS, MetadataIdentifier.TALES_IN_BOOK, MetadataIdentifier.ALT_TITLE, MetadataIdentifier.SEP_PUBLISHED, MetadataIdentifier.CONTAINED_IN] and appending:
                    appending = '| '.join([a.replace(',', ';') for a in appending])
                elif item[0] in [MetadataIdentifier.AUTHORS, MetadataIdentifier.TRANSLATION, MetadataIdentifier.ILLUSTRATION, MetadataIdentifier.COVER_AUTHORS] and appending:
                    appending = '| '.join([a.replace(',', ';') for a in appending])
                elif item[0] in [MetadataIdentifier.SERIES, MetadataIdentifier.EDITION] and appending:
                    if appending[0] and appending[1]:
                        appending = ' '.join([appending[0].replace(',', '|'), str(appending[1])])
                    elif appending[0]:
                        appending = appending[0].replace(',', '|')
                    else:
                        appending = None
                elif isinstance(appending, str) and appending:
                    appending = appending.replace(',', '|')
                if item[1] and appending:
                    if self.is_tale and 'legie' == item[3]:
                        mi_result.identifiers['legie_povidka'] = str(appending)
                    else:
                        mi_result.identifiers[item[3]] = str(appending)
        except:
            self.log.exception('Error adding extra identifiers for url: %r'%self.url)

        def get_metadata_variable(argument):
            switch_check = {
                MetadataIdentifier.CATEGORY: ', '.join(mi.category),
                MetadataIdentifier.PAGES: mi.pages,
                MetadataIdentifier.AUTHORS: ' & '.join(mi.mi_authors),
                MetadataIdentifier.ILLUSTRATION: ' & '.join(mi.illustrators),
                MetadataIdentifier.TRANSLATION: ' & '.join(mi.translators),
                MetadataIdentifier.COVER_AUTHORS: ' & '.join(mi.cover_authors),
                MetadataIdentifier.WORLD: mi.world,
                MetadataIdentifier.SEP_PUBLISHED: ', '.join(mi.sep_published),
                MetadataIdentifier.CONTAINED_IN: ', '.join(mi.contained_in),
                MetadataIdentifier.TITLE: mi.mi_title,
                MetadataIdentifier.SUBTITLE: mi.subtitle,
                MetadataIdentifier.ALT_TITLE: ', '.join(mi.alt_title),
                MetadataIdentifier.ALT_ORIGINAL_TITLE: mi.alt_original_title,
                MetadataIdentifier.ORIGINAL_TITLE: mi.original_title,
                MetadataIdentifier.ORIGINAL_YEAR: mi.original_year,
                MetadataIdentifier.PUB_YEAR: mi.pubyear,
                MetadataIdentifier.PUBLISHER: mi.mi_publisher,
                MetadataIdentifier.SERIES: mi.mi_series,
                MetadataIdentifier.SERIES_INDEX: mi.mi_series_index,
                MetadataIdentifier.EDITION: mi.edition,
                MetadataIdentifier.EDITION_INDEX: mi.edition_index,
                MetadataIdentifier.RATING: mi.rating100,
                MetadataIdentifier.RATING5: mi.rating_star,
                MetadataIdentifier.RATING10: mi.rating10,
                MetadataIdentifier.RATING_COUNT: mi.rating_count,
                MetadataIdentifier.ISBN: mi.mi_isbn,
                MetadataIdentifier.EAN: mi.ean,
                MetadataIdentifier.LANGUAGE: mi.mi_language,
                MetadataIdentifier.PRICE: mi.price,
                MetadataIdentifier.DIMENSIONS: mi.dimensions,
                MetadataIdentifier.PRINT_RUN: mi.print_run,
                MetadataIdentifier.ISSUE_NUMBER: mi.issue_number,
                MetadataIdentifier.ORIG_ID: mi.mi_id,
                MetadataIdentifier.AWARDS: mi.awards,
                MetadataIdentifier.COVER_TYPE: mi.cover_type,
                MetadataIdentifier.NOTE: mi.note,
                MetadataIdentifier.EXTERNAL_LINKS: mi.external_links,
                MetadataIdentifier.TALES_IN_BOOK: mi.tales_in_book,
                MetadataIdentifier.SOURCE_RELEVANCE: mi.source_relevance,
                MetadataIdentifier.CUSTOM_TEXT: argument
            }
            return switch_check.get(argument, None)
            
        try:
            mi_result.publisher = ''
            for item in publisher_line:
                appending = get_metadata_variable(item[0])

                if appending == MetadataIdentifier.CUSTOM_TEXT and item[1]:
                    mi_result.publisher += str(item[2])
                elif item[1] and appending:
                    mi_result.publisher += str(appending)
        except:
            mi_result.publisher = mi.mi_publisher if mi.mi_publisher else None
            self.log.exception('Error parsing publisher for url: %r'%self.url)

        try:
            mi_result.series = ''
            for item in series_line:
                appending = get_metadata_variable(item[0])

                if appending == MetadataIdentifier.CUSTOM_TEXT and item[1]:
                    mi_result.series += str(item[2])
                elif item[1] and appending:
                    mi_result.series += str(appending)
        except:
            mi_result.series = mi.mi_series if mi.mi_series else None
            self.log.exception('Error parsing series for url: %r'%self.url)

        try:
            mi_result.series_index = None
            appending = get_metadata_variable(series_index_field[0])
            if series_index_field[1] and appending:
                mi_result.series_index = float(appending)
        except:
            mi_result.series_index = mi.mi_series_index if mi.mi_series_index else None
            self.log.exception('Error parsing series_index for title: %r'%mi.mi_title)

        try:
            mi_result.title = ''
            for item in title_line:
                appending = get_metadata_variable(item[0])

                if appending == MetadataIdentifier.CUSTOM_TEXT and item[1]:
                    mi_result.title += str(item[2])
                elif item[1] and appending:
                    mi_result.title += str(appending)
        except:
            mi_result.title = mi.mi_title if mi.mi_title else ''
            self.log.exception('Error parsing title for url: %r'%self.url)

        # cover handling
        try:
            obalky_cover_url = None

            if mi.mi_isbn and obalkyknih_cover:
                obalky_cover_url = self.get_parse_obalkyknih_cover(mi.mi_isbn)
            if obalky_cover_url is None and mi.ean and obalkyknih_cover:
                obalky_cover_url = self.get_parse_obalkyknih_cover(mi.ean)

            if max_covers == 0:
                mi_result.has_cover = False
            elif max_covers > 1 and self.cover_urls:
                if obalky_cover_url:
                    self.cover_urls.append(obalky_cover_url)
                self.plugin.cache_identifier_to_cover_url(mi.mi_id, self.cover_urls)
                if mi.mi_isbn:
                    self.plugin.cache_isbn_to_identifier(mi.mi_isbn, mi.mi_id)
                mi_result.has_cover = True if self.cover_urls else False
            else:
                self.log.info('Parsed URL for cover:%r'%mi.cover_url)
                if obalky_cover_url:
                    self.plugin.cache_identifier_to_cover_url(mi.mi_id, [mi.cover_url, obalky_cover_url])
                else:
                    self.plugin.cache_identifier_to_cover_url(mi.mi_id, [mi.cover_url])
                if mi.mi_isbn:
                    self.plugin.cache_isbn_to_identifier(mi.mi_isbn, mi.mi_id)
                mi_result.has_cover = bool(mi.cover_url)
        except:
            self.log.exception('Error parsing cover for url: %r'%self.url)
             
        try:
            if mi.mi_language:
                mi_result.language = mi.mi_language
                mi_result.languages = [mi.mi_language]
        except:
            self.log.exception('Error parsing language for url: %r'%self.url)

        # authors field creating
        authors_to_add = []
        if author_role:
            if authors_include:
                authors_to_add.extend(['%s (Autor)'%a for a in mi.mi_authors])
            if translators_include and mi.translators:
                authors_to_add.extend(['%s (Překlad)'%a for a in mi.translators])
            if cover_authors_include and mi.cover_authors:
                authors_to_add.extend(['%s (Obálka)'%a for a in mi.cover_authors])
            if illustrators_include and mi.illustrators:
                authors_to_add.extend(['%s (Ilustrace)'%a for a in mi.illustrators])
        else:
            if authors_include:
                authors_to_add.extend(mi.mi_authors)
            if translators_include and mi.translators:
                authors_to_add.extend(mi.translators)
            if cover_authors_include and mi.cover_authors:
                authors_to_add.extend(mi.cover_authors)
            if illustrators_include and mi.illustrators:
                authors_to_add.extend(mi.illustrators)

        # Add only first
        if (only_one_author == 1 and authors_to_add and len(authors_to_add) > 1) or len(authors_to_add) == 1:
            authors_to_add = authors_to_add[:1]
            first_a = authors_to_add[0].split()
            if first_a[-1] in ('(Autor)'): # if (Autor) only.. don't write role
                first_a.pop()
            authors_to_add[0] = ' '.join(first_a)

        # Swap authors from FN LN to LN FN format
        UNSWAPPABLE = set(('neznámý - neuveden', '* antologie', 'kolektiv autorů'))
        AVAILABLE_ROLES = set(('(Autor)', '(Obálka)', '(Ilustrace)', '(Překlad)', '(Ortonym)', '(Interpret)'))
        UNSWAPPABLE_WITH_ROLES = {u + ' ' + a for u in UNSWAPPABLE for a in AVAILABLE_ROLES}

        lookup = set()  # a temporary lookup set
        authors_to_add = [a for a in authors_to_add if a not in lookup and lookup.add(a) is None]
        if swap_authors and not msprefs.get('swap_author_names'):
            swapped = []
            for a in authors_to_add:
                if a in UNSWAPPABLE_WITH_ROLES:
                    swapped.append(a)
                    continue
                auth_parts = a.split()
                if auth_parts[-1] in AVAILABLE_ROLES:
                    role = auth_parts.pop()
                    swapped.append('%s %s %s' %(auth_parts[-1], ' '.join(auth_parts[:-1]), role))
                else:
                    swapped.append('%s %s' %(auth_parts[-1], ' '.join(auth_parts[:-1])))
            authors_to_add = swapped
        elif msprefs.get('swap_author_names'):
            # prepare for built-in reswap function
            swapped = []
            for a in authors_to_add:
                if a in UNSWAPPABLE_WITH_ROLES:
                    swapped.append(a)
                    continue
                auth_parts = a.split()
                if auth_parts[-1] in AVAILABLE_ROLES:
                    role = auth_parts.pop()
                    swapped.append('%s %s %s' %(' '.join(auth_parts[:-1]), role, auth_parts[-1]))
                else:
                    swapped.append('%s %s' %(' '.join(auth_parts[:-1]), auth_parts[-1]))
            authors_to_add = swapped
            
        mi_result.authors = authors_to_add
        mi_result.source_relevance = mi.source_relevance
        # self.plugin.clean_downloaded_metadata(mi)

        self.log.info(mi_result)
        return mi_result

    def parse_first(self, root, xpath, loginfo, convert=lambda x: x[0].replace('&nbsp;','').strip()):
        try:
            nodes = root.xpath(xpath)
            self.log.info('Found %s: %s' % (loginfo,nodes))
            return convert(nodes) if nodes else None
        except Exception as e:
            self.log.exception('Error parsing for %s with xpath: %s' % (loginfo, xpath))

    def parse_all(self, root, xpath, loginfo, convert=lambda x: [node.strip() for node in x]):
        try:
            if isinstance(xpath, list):
                self.log.info('Multiple paths.. %s'%xpath)
                all_nodes = []
                for path in xpath:
                    nodes = root.xpath(path)
                    self.log.info('Found %s: %s' % (loginfo,','.join(nodes)))
                    if nodes:
                        all_nodes.extend(nodes)
                return convert(all_nodes) if all_nodes else []
            else:
                nodes = root.xpath(xpath)
                self.log.info('Found %s: %s' % (loginfo,','.join(nodes)))
                return convert(nodes) if nodes else []
        except Exception:
            self.log.exception('Error parsing for %s with xpath: %s' % (loginfo, xpath))

    ## GLOBAL INFO
    def parse_legie_id(self, root):
        return self.parse_first(root, '//div[@data-kasp-id]/@data-kasp-id', 'legie_id')

    def parse_title(self, root):
        title =  self.parse_first(root,'//h2[@itemprop="name" or @id="nazev_povidky"]/text()','title', lambda x: x[0].replace('&nbsp;','').strip())
        return title if title else ''

    def parse_subtitle(self, root):
        return self.parse_first(root,'//h3[@id="podtitul_knihy"]/text()','subtitle', lambda x: x[0].replace('&nbsp;','').strip())

    def parse_series(self, root):
        series_node = self.parse_first(root,'//div[@id="kniha_info"]/div/p/text()[contains(., "série: ")]/following-sibling::a[contains(@href, "serie")]/text()','series', lambda x: x[0].replace('&nbsp;','&').strip().replace("série", ""))
        filter_check = get_pref(PluginPrefsName.SERIES_FILTER)
        if series_node:
            series_node = self._convert_to_calibre(series_node, get_pref(PluginPrefsName.KEY_SERIES_MAPPINGS), filter_check)

        index = self.parse_first(root, '//div[@id="kniha_info"]/div/p/text()[contains(., "díl v sérii: ")]', 'series_index', lambda x: x[0].strip().replace("díl v sérii: ", ""))
        if isinstance(index, str) and str.isdigit(index):
            index = float(index)
        elif isinstance(index, str):
            index = 0.
        else:
            index = None
        return series_node, index

    def parse_rating(self, root):
        rating_node = self.parse_first(root, '//span[@itemprop="ratingValue"]/text()', 'rating_percent', lambda x: int(x[0].strip()))
        star_rating = rating_node/20 if rating_node else None
        rating_count = self.parse_first(root, '//span[@itemprop="ratingCount"]/text()', 'rating_count', lambda x: int(x[0].strip()))
        return star_rating, star_rating*2 if star_rating else None, rating_node, rating_count

    def parse_origTitle(self, root):
        return self.parse_first(root, '//p[@id="jine_nazvy"]/text()[contains(., "originální název:")]', 'orig_title', lambda x: x[0].strip().replace("originální název: ", ""))

    def parse_altTitle(self, root):
        return self.parse_first(root, '//p[@id="jine_nazvy"]/text()[contains(., "jiný (obecně známý) název: ")]', 'orig_title', lambda x: x[0].strip().replace("jiný (obecně známý) název: ", ""))

    def parse_origDate(self, root):
        return self.parse_first(root, '//p[@id="jine_nazvy"]/text()[contains(., "originál vyšel: ")]', 'orig_year', lambda x: x[0].strip().replace("originál vyšel: ", ""))

    def parse_world(self, root):
        return self.parse_first(root, '//p/text()[contains(., "kniha patří do světa: ") or contains(., "ovídka patří do světa: ")]/following-sibling::a[contains(@href, "detektiv/") or contains(@href, "svet/")]/text()',
                                'world', lambda x: x[0].strip().replace("kniha patří do světa: ", ""))

    def parse_contained_in(self, root):
        return self.parse_all(root, '//p/text()[contains(., "Tato kniha je částí i jiných knih:")]/following-sibling::a[contains(@href, "kniha/")]/text() | //div[@id="zarazena_do_knih"]/a/text()', 'contained in')

    def parse_sep_published(self, root):
        return self.parse_all(root, '//div/p/text()[contains(., "Tento svazek obsahuje díla vydaná samostatně: ")]/following-sibling::a[contains(@href, "kniha/")]/text()', 'publised_separately_as')

    def parse_alt_titles(self, root):
        return self.parse_all(root, '//p[@class="i"]/span[@class="large b"]/text()', 'alt_titles')

    def parse_category(self, root):
        tags = self.parse_all(root, '//a[contains(@href, "tagy/")]/text()', 'category')
        if not tags:
            tags = self.parse_first(root, '//div[@id="povidka_info"]/p/text()[contains(., "Kategorie: ")]', 'category', convert=lambda x: x[0].strip().replace('Kategorie: ', '')).split(' - ')
        filter_check = get_pref(PluginPrefsName.CATEGORY_FILTER)
        if tags:
            calibre_tags = self._convert_category_to_calibre_tags(tags, filter_check)
            if len(calibre_tags) > 0:
                tags = calibre_tags
        return tags
    
    def parse_authors(self, root):
        return self.parse_all(root, '//div[@id="pro_obal"]/../h3/a/text()', 'authors', lambda x: list({node.strip() for node in x}))

    def parse_comments(self, root):
        desc_nodes = root.xpath('//div[@id="anotace" or @id="nic"]/strong/following-sibling::p[not(strong[contains(text(), "Jiné ocenění")])]')
        desc = '<br>'.join([tostring(n, pretty_print=True).decode('utf-8').replace('<p>', '').replace('</p>', '') for n in desc_nodes]) if desc_nodes else ''
        # Links on the same site
        desc = desc.replace('<a href="index.php?', '<a href="%s/index.php?'%self.plugin.BASE_URL)
        return '<p id="description">{}</p>'.format(desc) if desc else ''

    def parse_external_links(self, root):
        link_nodes = root.xpath('//div[@id="anotace"]/dl/dt')
        link = '<br>'.join([tostring(n, pretty_print=True).decode('utf-8').replace('<dt>', '').replace('</dt>', '') for n in link_nodes]) if link_nodes else ''
        return '{}'.format(link) if link else ''

    ## ISSUE SPECIFIC INFO
    def parse_isbn(self, root):
        return self.parse_first(root, './/span[@title="ISBN-International Serial Book Number / mezinarodni unikatni cislo knihy"]/following-sibling::text()',
                                'ISBN', lambda x: x[0].replace("\xa0", " ").replace(": ", "").strip())

    def parse_ean(self, root):
        return self.parse_first(root, './/span[contains(text(), "EAN")]/following-sibling::text()', 'EAN', convert=lambda x: x[0].replace("\xa0", " ").replace(": ", "").strip())

    def parse_dimensions(self, root):
        return self.parse_first(root, 'div[@class="data_vydani"]/table//tr/td[contains(text(), "rozměry")]/text()', 'dimensions', convert=lambda x: x[0].replace("\xa0", " ").replace("rozměry: ", "").strip())

    def parse_print_run(self, root):
        return self.parse_first(root, 'div[@class="data_vydani"]/table//tr/td[contains(text(), "výtisků")]/text()', 'print_run', convert=lambda x: x[0].replace("\xa0", " ").replace("počet výtisků: ", "").strip())

    def parse_issue_number(self, root):
        return self.parse_first(root, 'div[@class="data_vydani"]/table//tr/td[starts-with(text(), " vydání")]/text()', 'issue_number', convert=lambda x: x[0].replace("\xa0", " ").replace("vydání: ", "").strip())

    def parse_price(self, root):
        return self.parse_first(root, 'div[@class="data_vydani"]/table//tr/td[contains(text(), "cena")]/text()', 'price', convert=lambda x: x[0].replace("\xa0", " ").replace("cena: ", "").strip())

    def parse_note(self, root):
        return self.parse_first(root, 'div[@class="data_vydani"]/table//tr/td[@colspan="2" and contains(text(), "poznámka:")]/text()', 'note', convert=lambda x: x[0].replace("\xa0", " ").replace("poznámka: ", "").strip())

    def parse_cover_type(self, root):
        return self.parse_first(root, 'div[@class="data_vydani"]/table//tr/td[contains(text(), "vazba:")]/text()', 'cover_type', convert=lambda x: x[0].replace("\xa0", " ").replace("vazba: ", "").strip())

    def parse_pages(self, root):
        return self.parse_first(root, 'div[@class="data_vydani"]/table//tr/td[contains(text(), "počet") and contains(text(), "stran")]/text()', 'numberOfPages', convert=lambda x: x[0].replace("\xa0", " ").replace("počet stran: ", "").strip())

    def parse_pubdate(self, root):
        pubdate_node = self.parse_first(root, 'div[@class="data_vydani"]/table//tr/td[contains(text(), "přibližné")]/text()', 'pubdate')
        date_found = date_final = ap_year = None
        if pubdate_node:
            self.log.info('pubdate_node %s'%pubdate_node)
            date_pattern = r'\b(\d{2})\.(\d{2})\.(\d{4})\b'
            date_found = re.search(date_pattern, pubdate_node)
            if date_found:
                date_final = None
                try:
                    ap_day, ap_month, ap_year = date_found.group(1), date_found.group(2), date_found.group(3)
                    if ap_day == '00':
                        ap_day = '01'
                    if ap_month == '00':
                        ap_month = '01'
                    self.log.info(date_final)
                    date_final = prepare_date(int(ap_year), int(ap_month), int(ap_day))
                except:
                    self.log.exception('Failed to parse approx date.')
        if not date_found:
            pubdate_node = self.parse_first(root, 'h3/a[contains(@href, "rok/")]/text()', 'pubdate', lambda x: x[0].strip())
            ap_year = pubdate_node if pubdate_node else None
            date_final = prepare_date(int(pubdate_node)) if pubdate_node else None
        return date_final, ap_year

    def parse_publisher(self, root):
        publisher = self.parse_first(root, 'div[@class="data_vydani"]/a[contains(@href, "vydavatel/")]/text()', 'publisher')
        filter_check = get_pref(PluginPrefsName.PUBLISHER_FILTER)
        if publisher:
            publisher = self._convert_to_calibre(publisher, get_pref(PluginPrefsName.KEY_PUBLISHER_MAPPINGS), filter_check)
        return publisher
    
    def parse_editions(self, root):
        series_node = self.parse_first(root,'div[@class="data_vydani" and contains(., "edici")]/a[contains(@href, "edice/")]/text()','edition', lambda x: x[0].replace('&nbsp;','&').strip())
        filter_check = get_pref(PluginPrefsName.SERIES_FILTER)
        if series_node:
            series_node = self._convert_to_calibre(series_node, get_pref(PluginPrefsName.KEY_SERIES_MAPPINGS), filter_check)
        index = self.parse_first(root, 'div[@class="data_vydani" and contains(., "edici")]/a[contains(@href, "edice/")]/following-sibling::text()[contains(., "číslem")]',
                                 'edition_index', lambda x: x[0].replace("\xa0", "").replace("&nbsp;", "").replace("podčíslem", "").strip())
        index = float(''.join(i for i in index if i.isdigit())) if index else None
        return series_node, index

    def parse_languages(self, root):
        return self.parse_first(root, 'div[@class="data_vydani"]/table//tr/td[contains(text(), "jazyk")]/text()', 'languages', convert=lambda x: x[0].replace("\xa0", " ").replace("&nbsp;", " ").replace("jazyk vydání: ", "").replace("cz", "cs").strip())

    def parse_translators(self, root):
        return self.parse_first(root, 'div[@class="data_vydani"]/table//td[contains(text(), "překlad:")]/text()', 'translators', lambda x: x[0].replace("\xa0", "").replace("&nbsp;", "").replace('překlad:','').strip())

    def parse_illustrators(self, root):
        return self.parse_first(root, 'div[@class="data_vydani"]/table//td[contains(text(), "ilustrací:")]/text()', 'illustrators', lambda x: x[0].replace("\xa0", "").replace("&nbsp;", "").replace('autorilustrací:','').strip())

    def parse_cover_authors(self, root):
        return self.parse_first(root, 'div[@class="data_vydani"]/table//td[contains(text(), "obálky:")]/text()', 'cover_authors', lambda x: x[0].replace("\xa0", "").replace("&nbsp;", "").replace('autorobálky:','').strip())

    def parse_cover(self, root):
        return self.parse_first(root, '//img[@class="obalk"]/@src', 'cover', lambda x: x[0].strip())

    def parse_cover_list(self, root):
        return self.parse_all(root, '//img[@class="obalk"]/@src', 'cover')

    ## SEPARATE PAGES
    def parse_awards(self, root):
        award_name = root.xpath('//div/h3/a[contains(@href, "oceneni/")]/text()')
        award_href = root.xpath('//div/h3/a[contains(@href, "oceneni/")]/@href')
        if award_href:
            award_href = [a.split('/')[1] for i, a in enumerate(award_href)]
        href_to_name = dict(map(lambda i, j : (i, j), award_href, award_name))

        categories_href = root.xpath('//div//h3[a[contains(@href, "oceneni/")]]/following-sibling::*[self::ul or self::li]//a[position() = 1]/@href')
        categories_name = root.xpath('//div//h3[a[contains(@href, "oceneni/")]]/following-sibling::*[self::ul or self::li]//a[position() = 1]/text()')
        categories_year = root.xpath('//div//h3[a[contains(@href, "oceneni/")]]/following-sibling::*[self::ul or self::li]//a[position() = 2]/text()')
        categories_result = root.xpath('//div//h3[a[contains(@href, "oceneni/")]]/following-sibling::*[self::ul or self::li]//a[position() = 2]/following-sibling::text()')
        if categories_result:
            categories_result = [c.replace(') - ', '') for c in categories_result]
        if categories_href:
            award_name = [href_to_name[c.split('/')[1]] for i, c in enumerate(categories_href)]
        
        awards = []
        if categories_result and categories_name and categories_year and award_name:
            for i, a in enumerate(categories_name):
                award = '%s • %s • %s • %s'%(award_name[i], categories_name[i], categories_year[i], categories_result[i])
                awards.append(award)
        self.log.info('Parsed awards: %s'%awards)
        return awards

    def parse_tales_list(self, root):
        return self.parse_all(root, '//dl/dt/a[contains(@href, "povidka/")]/text()', 'tales_in_book_title')

    ## Utils
    def _convert_category_to_calibre_tags(self, genre_tags, filter_check=False):
        # for each tag, add if we have a dictionary lookup
        calibre_tag_lookup = get_pref(PluginPrefsName.KEY_CATEGORY_MAPPINGS)
        calibre_tag_map = dict((k.lower(),v) for (k,v) in calibre_tag_lookup.items())
        tags_to_add = list()
        for genre_tag in genre_tags:
            if genre_tag.lower() in calibre_tag_map:
                tags = calibre_tag_map.get(genre_tag.lower(), None)
                if tags:
                    for tag in tags:
                        if tag not in tags_to_add:
                            tags_to_add.append(tag.replace(',', ';'))
            elif filter_check:
                continue
            else: 
                tag = genre_tag
                if tag not in tags_to_add:
                            tags_to_add.append(tag.replace(',', ';'))
            
        return list(tags_to_add)

    def	_convert_to_calibre(self, remap_item, prefs, filter_check=False):
        # for each tag, add if we have a dictionary lookup
        calibre_map = dict((k.lower(),v) for (k,v) in prefs.items())
        self.log.info('calibre_map: %s'%calibre_map)
        calibre_remap_item = calibre_map.get(remap_item.lower(), None)
        if calibre_remap_item:
            return calibre_remap_item[0]
        elif filter_check:
            return None
        else:
            return remap_item

def prepare_date(year, month=1, day=1):
    from calibre.utils.date import utc_tz
    return datetime(year, month, day, tzinfo=utc_tz)

def split_authors(authors_string):
    pass

