#!/usr/bin/env python
# vim:fileencoding=UTF-8:ts=4:sw=4:sta:et:sts=4:ai
from __future__ import (unicode_literals, division, absolute_import,
                        print_function)

__license__   = 'GPL v3'
__copyright__ = '2024 seeder'
__docformat__ = 'restructuredtext en'

from lxml.html import fromstring
from calibre.utils.cleantext import clean_ascii_chars
from calibre import as_unicode

def load_url(log, query, br, timeout=30):
    try:
        log.info('-- querying: %s' % query)
        response = br.open_novisit(str(query), timeout=timeout)
    except Exception as e:
        msg = '*** Failed to make identify query: %r - %s ' % (query, e)
        log.exception(msg)
        raise Exception(msg)
    try:
        raw = response.read().strip().decode('utf-8', errors='replace')\
                             .lstrip('<?xml version="1.0" encoding="utf-8"?>')
        if not raw:
            msg = '*** Failed to get raw result for query: %r' % query
            log.error(msg)
            raise Exception(msg)
        
        # legie/pitaval specific
        if 'nebyla v databázi nalezena' in raw:
            msg = '*** Item with specified ID not found: %r' % query
            log.error(msg)
        if 'Nevyhledán žádný výsledek pro řetězec' in raw:
            msg = '*** Not found any results: %r' % query
            log.error(msg)
        root = fromstring(clean_ascii_chars(raw))
    except:
        msg = '*** Failed to parse page for query: %r' % query
        log.exception(msg)
        raise Exception(msg)
    return root, response

def strip_accents(s):
    if not isinstance(s, (str)):
        return s  # Return the original value if it's not a string or unicode
    if isinstance(s, str):
        s = as_unicode(s)  # Convert str to unicode if it's a str type
    symbols = (u"öÖüÜóÓőŐúÚůŮéÉěĚáÁűŰíÍýÝąĄćĆčČęĘłŁńŃóÓśŚšŠźŹżŻžŽřŘďĎťŤňŇ\t @#$?%ˇ´˝¸~^˘°|/*()[]{}:<>.,;¨˛`·'_\"\\",
               u"oOuUoOoOuUuUeEeEaAuUiIyYaAcCcCeElLnNoOsSsSzZzZzZrRdDtTnN--------------------------------------")
    tr = dict((ord(a), ord(b)) for (a, b) in zip(*symbols))
    return s.translate(tr)
