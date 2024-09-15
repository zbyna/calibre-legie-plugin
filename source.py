#!/usr/bin/env python
# vim:fileencoding=UTF-8:ts=4:sw=4:sta:et:sts=4:ai
from __future__ import (unicode_literals, division, absolute_import,
                        print_function)

__license__   = 'GPL v3'
__copyright__ = '2024 seeder'
__docformat__ = 'restructuredtext en'

import re
from calibre.ebooks.metadata import check_isbn
from calibre.ebooks.metadata.sources.base import Source as BaseSource
from .prefs import PluginPrefsName
from .utils import strip_accents

class Source(BaseSource):
    version                 = (0, 0, 0)
    config_message = _('Plugin version: <b>%s</b>')%str(version).strip('()').replace(', ', '.')
    GOOGLE_SEARCH_URL = 'https://www.google.com/search?q='
    DUCKDUCKGO_SEARCH_URL = 'https://html.duckduckgo.com/html/?q='

    def get_pref(self, pref=None):
        """
        Returns MetadataPlugin specific preferences
        """
        return {}

    @staticmethod
    def search_title_for_metadata(title, identifiers):
        if not title:
            return title, identifiers
        search_regex = re.compile(r"(?:(?:"
                                  r"isbn|ean|oclc|"
                                  r"dbk|dbknih|databazeknih|"
                                  r"dbkp|dbk_povidka|databazeknih_povidka|dbknih_povidka|"
                                  r"xtrance_id|xtrance|xtr|"
                                  r"legie|legie_povidka|"
                                  r"pitaval|pitaval_povidka|"
                                  r"publisher|pubdate|pubyear|language|lang|"
                                  r"type|search"
                                  r"):(?:\S*)(?: |$))")
        meta_title = re.findall(search_regex, title)
        # Remove matched metadata from title
        title = re.sub(pattern=search_regex, string=title, repl='')
        title = ' '.join(title.split())

        identifiers.update(dict([i.rstrip(' ').split(':', 1) for i in meta_title]))

        identifiers_mapping = {
            'databazeknih': ['databazeknih', 'dbknih', 'dbk'],
            'databazeknih_povidka': ['databazeknih_povidka', 'dbknih_povidka', 'dbk_povidka', 'dbk_p', 'dbkp'],
            'legie': ['legie'],
            'legie_povidka': ['legie_povidka'],
            'pitaval': ['pitaval'],
            'pitaval_povidka': ['pitaval_povidka'],
            'xtrance': ['xtrance', 'xtrance_id', 'xtr'],
            'isbn': ['isbn', 'ean'],
            'pubdate': ['pubdate', 'pubyear'],
            'publisher': ['publisher'],
            'language': ['language', 'lang'],
            'type': ['type'],
            'search': ['search'],
        }
        for identifier, keys in identifiers_mapping.items():
            for key in keys:
                value = identifiers.get(key, None)
                if value is not None:
                    identifiers[identifier] = value

        # check for type audiobook/tale
        book_type = identifiers.get('type', None)
        if book_type:
            if strip_accents(book_type).lower() in ['audio', 'audiokniha', 'audiobook']:
                identifiers['type'] = 'a'
            elif strip_accents(book_type).lower() in ['povidka', 'basen', 'cast_dila', 'part', 'book_part', 'tale', 'poem']:
                identifiers['type'] = 'p'

        # check for search engine
        search_engine = identifiers.get('search', None)
        if search_engine:
            if strip_accents(search_engine).lower() in ['google']:
                identifiers['search'] = 'g'
            elif strip_accents(search_engine).lower() in ['duckduckgo', 'ddg', 'duck']:
                identifiers['search'] = 'd'

        # find ISBN in title and pass it into identifiers
        title_list = title.split()
        title_isbn = [t for t in title_list if check_isbn(t) is not None]
        if title_isbn:
            identifiers['isbn'] = title_isbn[0]
            title = title.replace(title_isbn[0], '')

        if identifiers.get('legie', None) and \
            '#' in identifiers['legie']:
            if not identifiers.get('pubdate', None):
                year = identifiers['legie'].split('#')[1]
                if year.isdigit() and len(year) == 4:
                    identifiers['pubdate'] = year
            identifiers['legie'] = identifiers['legie'].split('#')[0]

        if identifiers.get('pitaval', None) and \
            '#' in identifiers['pitaval']:
            if not identifiers.get('pubdate', None):
                year = identifiers['pitaval'].split('#')[1]
                if year.isdigit() and len(year) == 4:
                    identifiers['pubdate'] = year
            identifiers['pitaval'] = identifiers['pitaval'].split('#')[0]

        return title, identifiers

    def _parse_duckduckgo_results(self, log, orig_title, orig_authors, root, matches, no_matches, timeout):
        log.debug('Parsing duckduckgo results......')

        max_results = self.get_pref(PluginPrefsName.KEY_MAX_DOWNLOADS)
        results = root.xpath('//h2/a')
        found_title = ''
        result_url = ''
        log.debug('Found %s results'%len(results))
        for result in results:
            try:
                found_title = result.xpath('text()')[0].replace(' | Databáze knih', '')
                result_url = result.xpath('@href')[0].replace('/prehled-knihy/', '/zajimavosti-knihy/').replace('/knihy/', '/zajimavosti-knihy/').split('?')[0]
                log.debug('kniha: %s .. orig.autor: %s' %(found_title, orig_authors))
            except:
                log.debug('Xpath with found_title or URL not found in result')
                continue
            log.debug('Result URL: %r'%result_url)
            if result_url.find(self.BASE_URL) == -1:
                log.debug('Result is not on wanted site, skipping..')
                continue

            # try to recognize authors
            vlozit = False
            if orig_authors:
                title_list = found_title.split('-')
                if len(title_list) == 2:
                    title, author = title_list
                else:
                    title = found_title
                    author = found_title
                author = author.replace(' (p)', '').lower()
                found_auths = {a for a in author.split()[1:] if len(a) > 2} # list of founded names
                found_auths = {a.strip('ová') for a in found_auths} # without 'ová
                found_auths_ova = {'%sová' %a for a in found_auths} #added 'ová'
                found_auths = found_auths.union(found_auths_ova)
                #hledá shodu v příjmení i jménu
                log.debug('Orig_strip: %s .. title_strip: %s'%(strip_accents(orig_title).lower().replace('-', ''), strip_accents(title).lower().replace('-', '')))
                if orig_authors:
                    orig_authors = ' '.join(orig_authors).split()
                    orig_auths = {o.lower().replace(',', '') for o in orig_authors}
                    if orig_auths.intersection(found_auths):
                        vlozit = True
                    log.info('found_auths: %s .. orig_auths: %s'%(found_auths, orig_auths))
                #pokud je zadán pouze název
                if not vlozit and orig_title and \
                strip_accents(orig_title).lower().replace('-', '') in strip_accents(title).lower().replace('-', ''):
                    vlozit = True

            if vlozit and result_url not in matches and len(matches) < max_results:
                matches.append(result_url)
            elif result_url is not None and result_url not in no_matches:
                no_matches.append(result_url)
            if len(matches) >= max_results:
                break

        log.info('Matches: %s .. No matches: %s'%(matches, no_matches))
        if no_matches:
            for nmatch in no_matches:
                if len(matches) < max_results and not(nmatch in matches):
                    matches.append(nmatch)

    def _parse_google_search_results(self, log, orig_title, orig_authors, root, matches, no_matches, timeout):
        log.debug('Parsing google results......')
        max_results = self.get_pref(PluginPrefsName.KEY_MAX_DOWNLOADS)

        results = root.xpath('//div[@id="main"]/div/div[div/a]')
        found_title = ''
        result_url = ''
        log.debug('Found %s results'%len(results))
        for result in results:
            try:
                found_title = result.xpath('div/a//h3/div/text()')[0]
                result_url = result.xpath('div/a/@href')[0].replace('/prehled-knihy/', '/zajimavosti-knihy/')\
                    .replace('/knihy/', '/zajimavosti-knihy/')
                string_match = re.findall(r'%s.*?(?=&)'%self.BASE_URL, result_url)
                result_url = string_match[0] if string_match else ''
                log.debug('kniha: %s .. orig.autor: %s url: %s' %(found_title, orig_authors, result_url))
            except:
                log.debug('Xpath with found_title or URL not found in result')
                continue
            log.debug('Result URL: %r'%result_url)
            if result_url.find(self.BASE_URL) == -1:
                log.debug('Result is not on wanted site, skipping..')
                continue

            # try to recognize authors
            vlozit = False
            if orig_authors:
                title_list = found_title.split('-')
                if len(title_list) == 2:
                    title, author = title_list
                else:
                    title = found_title
                    author = found_title
                author = author.replace(' (p)', '').lower()
                found_auths = {a for a in author.split()[1:] if len(a) > 2} # list of founded names
                found_auths = {a.strip('ová') for a in found_auths} # without 'ová
                found_auths_ova = {'%sová' %a for a in found_auths} #added 'ová'
                found_auths = found_auths.union(found_auths_ova)
                #hledá shodu v příjmení i jménu
                if orig_authors:
                    orig_authors = ' '.join(orig_authors).split()
                    orig_auths = {o.lower().replace(',', '') for o in orig_authors}
                    if orig_auths.intersection(found_auths):
                        vlozit = True
                    log.info('found_auths: %s .. orig_auths: %s'%(found_auths, orig_auths))
                #pokud je zadán pouze název
                if not vlozit and orig_title and \
                strip_accents(orig_title).lower().replace('-', '') in strip_accents(title).lower().replace('-', ''):
                    vlozit = True

            if vlozit and result_url not in matches and len(matches) < max_results:
                matches.append(result_url)
            elif result_url is not None and result_url not in no_matches:
                no_matches.append(result_url)
            if len(matches) >= max_results:
                break

        log.info('Matches: %s .. No matches: %s'%(matches, no_matches))
        if no_matches:
            for nmatch in no_matches:
                if len(matches) < max_results and not(nmatch in matches):
                    matches.append(nmatch)
