#!/usr/bin/env python
# vim:fileencoding=UTF-8:ts=4:sw=4:sta:et:sts=4:ai
from __future__ import (unicode_literals, division, absolute_import,
                        print_function)

__license__   = 'GPL v3'
__copyright__ = '2024 seeder'
__docformat__ = 'restructuredtext en'

from functools import total_ordering
from polyglot.builtins import cmp
from .utils import strip_accents
from .prefs import PluginPrefsName


@total_ordering
class MetadataCompareKeyGen:
    def __init__(self, mi, source_plugin, title, authors, identifiers):
        if not mi:
            self.base = (2,2,2,2,2,2,2,2,2,2,2,2,2)
            self.comments_len = 0
            self.extra = 0
            return

        title, identifiers = source_plugin.search_title_for_metadata(title, identifiers)

        isbn = 1 if mi.isbn and identifiers.get('isbn', None) is not None \
                and mi.isbn == identifiers.get('isbn', None) else 2

        all_fields = 1 if source_plugin.test_fields(mi) is None else 2

        cl_title = title
        cl_title_mi = mi.title

        exact_title = 1 if title and \
                cl_title ==cl_title_mi else 2

        exact_clean_title = 1 if cl_title and cl_title_mi and \
                strip_accents(cl_title.lower()).replace('-', ' ') == strip_accents(cl_title_mi.lower()).replace('-', ' ') else 2

        contains_title = 1 if cl_title and cl_title_mi and \
                cl_title in cl_title_mi else 2

        contains_clean_title = 1 if title and \
                strip_accents(cl_title.lower()).replace('-', ' ') in strip_accents(cl_title_mi.lower()).replace('-', ' ') else 2


        auths = []
        if authors:
            for a in authors:
                auths.append(strip_accents(a.split(" ")[-1]).lower())
        miauths = []
        for a in mi.authors:
            miauths.append(strip_accents(a.split(" ")[-1]).lower())

        author_segments = list(set(miauths) & set(auths)) #authors surname list compare
        title_segments = list(set(strip_accents(mi.title.lower()).replace('-', '').split()) & set(strip_accents(title).replace('-', '').lower().split())) #authors surname list compare

        has_cover = 2 if (not source_plugin.cached_cover_url_is_reliable or
                source_plugin.get_cached_cover_url(mi.identifiers) is None) else 1
        
        author_match_relevance = getattr(mi, 'author_match_relevance', 2)
        title_relevance = getattr(mi, 'title_relevance', 2)

        # compare wanted year from Identifiers in title (pubyear:2000 or pubdate:2000)
        wanted_year = source_plugin.identifiers.get('pubdate', None)
        wanted_lang = source_plugin.identifiers.get('language', None)
        issue_pref = source_plugin.get_pref(PluginPrefsName.ISSUE_PREFERENCE)
        if not wanted_year and issue_pref in (1, 3):
            wanted_year = 10000 #MAX_VAL
        elif not wanted_year and issue_pref in (2, 4):
            wanted_year = 0 #MIN_VAL
        if not wanted_lang and issue_pref in (1, 2):
            wanted_lang = 'cs'
        elif not wanted_lang and issue_pref in (3, 4):
            wanted_lang = 'sk'
        pubyear = getattr(mi, 'pubyear', None)
        language = getattr(mi, 'language', None)
        if wanted_year and pubyear:
            closest_year = abs(int(wanted_year) - int(pubyear))
        else:
            closest_year = 0
        closest_lang = 0 if language == wanted_lang else 2
        

        self.base = (author_match_relevance, title_relevance, exact_title, exact_clean_title, contains_title, -len(title_segments), contains_clean_title, -len(author_segments), closest_lang, closest_year, all_fields, isbn, has_cover)
        self.extra = (getattr(mi, 'source_relevance', 0), )

    def compare_to_other(self, other):
        a = cmp(self.base, other.base)
        if a != 0:
            return a
        return cmp(self.extra, other.extra)

    def __eq__(self, other):
        return self.compare_to_other(other) == 0

    def __ne__(self, other):
        return self.compare_to_other(other) != 0

    def __lt__(self, other):
        return self.compare_to_other(other) < 0

    def __le__(self, other):
        return self.compare_to_other(other) <= 0

    def __gt__(self, other):
        return self.compare_to_other(other) > 0

    def __ge__(self, other):
        return self.compare_to_other(other) >= 0
