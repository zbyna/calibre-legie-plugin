#!/usr/bin/env python
# vim:fileencoding=UTF-8:ts=4:sw=4:sta:et:sts=4:ai
from __future__ import (unicode_literals, division, absolute_import,
                        print_function)

__license__   = 'GPL v3'
__copyright__ = '2024 seeder'
__docformat__ = 'restructuredtext en'

try:
    load_translations()
except NameError:
    pass # load_translations() added in calibre 1.9

try:
    from qt.core import  Qt, QToolButton, QSpinBox, QLabel, QGroupBox, QCheckBox, QComboBox, QHBoxLayout, QVBoxLayout, QLineEdit, QTableWidgetItem, QTableWidget, \
                        QAbstractItemView, QIcon, QInputDialog, QTabWidget, QWidget
except ImportError:
    try:
        from PyQt5.Qt import Qt, QToolButton, QSpinBox, QLabel, QGroupBox, QCheckBox, QComboBox, QHBoxLayout, QVBoxLayout, QLineEdit, QTableWidgetItem, QTableWidget, \
                        QAbstractItemView, QIcon, QInputDialog, QTabWidget, QWidget
    except ImportError:
        from PyQt4.Qt import Qt, QToolButton, QSpinBox, QLabel, QGroupBox, QCheckBox, QComboBox, QHBoxLayout, QVBoxLayout, QLineEdit, QTableWidgetItem, QTableWidget, \
                        QAbstractItemView, QIcon, QInputDialog, QTabWidget, QWidget

from calibre.gui2.metadata.config import ConfigWidget as DefaultConfigWidget

from .shared.ui_components import BuilderWidget, MappingsTableWidget, BuilderTableType
from .shared.prefs import PluginPrefsName, MetadataIdentifier, MetadataName, TranslatingStrings
from .prefs import DEFAULT_STORE_VALUES, DEFAULT_CATEGORY_MAPPINGS, LINE_OPTIONS, COMMENT_OPTIONS, IDENTIFIER_OPTIONS, TAG_OPTIONS, get_pref, set_pref

# python/pyqt backwards compability
from calibre import as_unicode

def add_checklist_option(parent, name, help_desc, checkbox_list):
    pass

def add_spin_option(parent, name, help_desc, pref, min_val=1, max_val=100, **kwargs):
    spinbox_layout = QHBoxLayout()
    parent.addLayout(spinbox_layout)
    
    label = QLabel(name)
    label.setToolTip(help_desc)
    spinbox_layout.addWidget(label)
    
    spinbox = QSpinBox(**kwargs)
    spinbox.setMinimum(min_val)
    spinbox.setMaximum(max_val)
    spinbox.setMaximumWidth(kwargs.get('max_width', 60))
    spinbox.setProperty('value', get_pref(pref))
    spinbox.setProperty('option_name', pref)
    spinbox_layout.addWidget(spinbox)
    
    spinbox_layout.addStretch(1)
    return spinbox

def add_combobox_option(parent, name, help_desc, pref, choices, **kwargs):
    combobox_layout = QHBoxLayout()
    parent.addLayout(combobox_layout)
    
    label = QLabel(name)
    label.setToolTip(help_desc)
    combobox_layout.addWidget(label)

    combobox = QComboBox()
    combobox.setProperty('option_name', pref)
    [combobox.addItem(c) for c in choices]
    combobox.setCurrentIndex(get_pref(pref))
    combobox.setMaximumWidth(kwargs.get('max_width', 180))
    combobox_layout.addWidget(combobox)

    return combobox

def add_check_option(parent, name, help_desc=None, pref=None):
    checkbox = QCheckBox(name)
    if help_desc:
        checkbox.setToolTip(help_desc)
    if pref is not None:
        checkbox.setProperty('option_name', pref)
        checkbox.setChecked(get_pref(pref))
    else:
        checkbox.setChecked(True)
        checkbox.setEnabled(False)
    parent.addWidget(checkbox)
    
    return checkbox

def get_widget_value(widget):
    if isinstance(widget, QComboBox):
        return int(widget.currentIndex())
    elif isinstance(widget, QCheckBox):
        return widget.isChecked()
    elif isinstance(widget, QSpinBox):
        return int(as_unicode(widget.value()))
    elif isinstance(widget, QLineEdit):
        return str(widget.text())
    elif isinstance(widget, QTableWidget):
        return widget.get_data()

def set_widget_value(widget, value):
    if isinstance(widget, QComboBox):
        widget.setCurrentIndex(value)
    elif isinstance(widget, QCheckBox):
        widget.setChecked(value)
    elif isinstance(widget, QSpinBox):
        widget.setValue(int(value))
    elif isinstance(widget, QLineEdit):
        widget.setText(str(value))
    elif isinstance(widget, QTableWidget):
        widget.populate_table(value)
      
class ConfigWidget(DefaultConfigWidget):

    def connect_widget_value(self):
        connected = {}
        connected[PluginPrefsName.KEY_MAX_DOWNLOADS] = self.search_tab.max_downloads_spin
        connected[PluginPrefsName.MAX_COVERS] = self.search_tab.max_covers_spin
        connected[PluginPrefsName.OBALKYKNIH_COVER] = self.search_tab.obalkyknih_cover_check
        connected[PluginPrefsName.KEY_CATEGORY_MAPPINGS] = self.tag_tab.table_widget
        connected[PluginPrefsName.KEY_SERIES_MAPPINGS] = self.series_tab.table_widget
        connected[PluginPrefsName.KEY_PUBLISHER_MAPPINGS] = self.publisher_tab.table_widget
        connected[PluginPrefsName.CATEGORY_FILTER] = self.tag_tab.genre_filter_check
        connected[PluginPrefsName.SERIES_FILTER] = self.series_tab.series_filter_check
        connected[PluginPrefsName.PUBLISHER_FILTER] = self.publisher_tab.publishers_filter_check
        connected[PluginPrefsName.ONE_AUTHOR] = self.authors_tab.one_author_check
        connected[PluginPrefsName.IDENTIFIER_SEARCH] = self.search_tab.identifier_search_check
        connected[PluginPrefsName.ISBN_SEARCH] = self.search_tab.isbn_search_check
        connected[PluginPrefsName.TALES_SEARCH] = self.search_tab.tales_search_check
        connected[PluginPrefsName.GOOGLE_SEARCH] = self.search_tab.google_engine_check
        connected[PluginPrefsName.DUCKDUCKGO_SEARCH] = self.search_tab.duckduckgo_engine_check
        connected[PluginPrefsName.ISSUE_PREFERENCE] = self.search_tab.issue_pref_combo
        connected[PluginPrefsName.AUTHORS_INCLUDE] = self.authors_tab.authors_field_check
        connected[PluginPrefsName.TRANSLATORS_INCLUDE] = self.authors_tab.translators_field_check
        connected[PluginPrefsName.ILLUSTRATORS_INCLUDE] = self.authors_tab.illustrators_field_check
        connected[PluginPrefsName.COVER_AUTHORS_INCLUDE] = self.authors_tab.cover_authors_field_check

        connected[PluginPrefsName.APPEND_TO_COMMENTS] = self.comments_tab.comments_arrange_table
        connected[PluginPrefsName.APPEND_TO_TAG] = self.tag_tab.tag_items_table
        connected[PluginPrefsName.APPEND_TO_IDENTIFIERS] = self.identifiers_tab.identifier_items_table
        connected[PluginPrefsName.TITLE_LINE] = self.authors_tab.title_line_table
        connected[PluginPrefsName.PUBLISHER_LINE] = self.publisher_tab.publisher_line_table
        connected[PluginPrefsName.SERIES_LINE] = self.series_tab.series_line_table
        connected[PluginPrefsName.SERIES_INDEXING_ITEM] = self.series_tab.series_index_field

        connected[PluginPrefsName.PUBLICATION_DATE] = self.publisher_tab.publication_date
        connected[PluginPrefsName.SWAP_AUTHORS] = self.authors_tab.swap_authors_check
        connected[PluginPrefsName.AUTHOR_ROLE] = self.authors_tab.authors_role_check
        return connected

    def set_default_prefs(self):
        from calibre.gui2 import question_dialog
        if not question_dialog(self, TranslatingStrings.CONFIRMATION_TITLE, '<p>'+
            TranslatingStrings.CONFIRMATION_DEFAULTS_INFO,
                show_copy_button=False):
            return
        set_pref(DEFAULT_STORE_VALUES)
        for pref, widget in self.connected.items():
            set_widget_value(widget, get_pref(pref))

    def commit(self):
        DefaultConfigWidget.commit(self)
        new_prefs = {}
        for pref, widget in self.connected.items():
            new_prefs[pref] = get_widget_value(widget)
        new_prefs[PluginPrefsName.SERIES_INDEX_FIELD] = self.series_tab.index_item_options[get_widget_value(self.series_tab.series_index_field)]
        set_pref(new_prefs)

    def __init__(self, plugin):
        DefaultConfigWidget.__init__(self, plugin)

        top_box = QHBoxLayout(self)
        if plugin.config_message:
            config_message = QLabel(plugin.config_message)
            config_message.setWordWrap(True)
            config_message.setOpenExternalLinks(True)
            top_box.addWidget(config_message)

        reset_plugin_btn = QToolButton()
        reset_plugin_btn.setToolTip(TranslatingStrings.DEFAULTS_RESET_TOOLTIP)
        reset_plugin_btn.setIcon(QIcon(I('restart.png')))
        reset_plugin_btn.clicked.connect(self.set_default_prefs)
        reset_plugin_btn.setShortcut('Alt+Shift+R')
        reset_plugin_btn.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        reset_plugin_btn.setText(TranslatingStrings.DEFAULTS_RESET_TITLE)
        top_box.addWidget(reset_plugin_btn)

        try:
            self.overl.insertLayout(0, top_box)
        except AttributeError:
            self.l.addLayout(top_box, 0, 0, 1, 1)
            
        self.gb.setMaximumHeight(70)

        tab = QTabWidget(self)
        self.l.addWidget(tab, self.l.rowCount(), 0, 1, 1)

        self.search_tab = SearchTab()
        self.authors_tab = AuthorsTab()
        self.tag_tab = TagTab()
        self.series_tab = SeriesTab()
        self.publisher_tab = PublisherTab()
        self.comments_tab = CommentsTab()
        self.identifiers_tab = IdentifiersTab()

        tab.addTab(self.search_tab, _('Search'))
        tab.addTab(self.authors_tab, _('Title and Authors'))
        tab.addTab(self.tag_tab, _('Tags'))
        tab.addTab(self.series_tab, _('Series'))
        tab.addTab(self.publisher_tab, _('Publishers and Date'))
        tab.addTab(self.comments_tab, _('Comments'))
        tab.addTab(self.identifiers_tab, _('Identifiers'))

        self.connected = self.connect_widget_value()

class SearchTab(QWidget):
    def __init__(self):
        QWidget.__init__(self)

        other_group_box_layout = QVBoxLayout()
        self.setLayout(other_group_box_layout)
        
        self.max_downloads_spin = add_spin_option(other_group_box_layout, TranslatingStrings.MAX_DOWNLOADS_TITLE,
                                                  TranslatingStrings.MAX_DOWNLOADS_INFO,
                                                  PluginPrefsName.KEY_MAX_DOWNLOADS)

        search_group_box = QGroupBox(_('Searching priority'), self)
        search_group_box_layout = QHBoxLayout()
        search_group_box.setLayout(search_group_box_layout)

        title_identifiers_search_check = add_check_option(search_group_box_layout, 
                                                        _('Title ids'),
                                                        _("You can add identifiers into 'Title' field (in format identifier:value e.g. legie:123 or publisher:new_publisher)\nbefore you start metadata download and they will be used prior built-in one."\
                                                          "Identifiers can be combined in title\n\n"\
                                                          "Identifiers available:\n"\
                                                          "'legie' for books\n"\
                                                          "'legie_povidka' for tales/poems\n"\
                                                          "'isbn' and 'ean' for searching by isbn number (legie can search by ISBN without this prefixes too)\n\n"\
                                                          "Specify wanted issue when Author/Title matching with identifiers:\n"
                                                          "'publisher' for book issue publisher specification (use underscore '_' for spacing multiple words)\n"\
                                                          "'pubdate' and 'pubyear' published edition year specification\n(e.g. pubdate:2024 will force plugin to prior search for issues from year 2024)\n"\
                                                          "'lang' or 'language' for book language specification (lang:cs for czech and lang:sk for slovak)\n"\
                                                          "'type' for book type specification (type:audio type:audiobook type:part type:tale type:book_part)\n"\
                                                          "'search' for enabling specified search engine (search:google search:duckduckgo)"))
        
        search_group_box_layout.addWidget(QLabel('>', self))

        self.identifier_search_check = add_check_option(search_group_box_layout,
                                                        _('Id legie'),
                                                        _('If identifier found in book metadata, plugin will use it for faster book search.\n'\
                                                          'legie for books\n'\
                                                          'legie_povidka for poems/tales'),
                                                        PluginPrefsName.IDENTIFIER_SEARCH)
        search_group_box_layout.addWidget(QLabel('>', self))
        self.isbn_search_check = add_check_option(search_group_box_layout, 
                                                        'ISBN',
                                                        TranslatingStrings.ISBN_SEARCH_INFO,
                                                        PluginPrefsName.ISBN_SEARCH)
        search_group_box_layout.addWidget(QLabel('>', self))

        self.tales_search_check = add_check_option(search_group_box_layout, 
                                                        TranslatingStrings.TALES_SEARCH_TITLE,
                                                        TranslatingStrings.TALES_SEARCH_INFO,
                                                        PluginPrefsName.TALES_SEARCH)
        search_group_box_layout.addWidget(QLabel('>', self))

        authors_search_check = add_check_option(search_group_box_layout,
                                                        TranslatingStrings.BOOK_SEARCH_TITLE,
                                                        TranslatingStrings.BOOK_SEARCH_INFO) 
        search_group_box_layout.addStretch(1)
        other_group_box_layout.addWidget(search_group_box)

        # Search engines
        search_engine_group_box = QGroupBox(TranslatingStrings.SEARCH_ENGINE_TITLE, self)
        search_engine_group_box_layout = QHBoxLayout()
        search_engine_group_box.setLayout(search_engine_group_box_layout)

        self.google_engine_check = add_check_option(search_engine_group_box_layout,
                                                        TranslatingStrings.GOOGLE_SEARCH_TITLE,
                                                        TranslatingStrings.GOOGLE_SEARCH_INFO,
                                                        PluginPrefsName.GOOGLE_SEARCH)
        search_engine_group_box_layout.addWidget(QLabel('>', self))
        self.duckduckgo_engine_check = add_check_option(search_engine_group_box_layout,
                                                        TranslatingStrings.DUCKDUCKGO_SEARCH_TITLE,
                                                        TranslatingStrings.DUCKDUCKGO_SEARCH_INFO,
                                                        PluginPrefsName.DUCKDUCKGO_SEARCH)
        search_engine_group_box_layout.addWidget(QLabel('>', self))
        databazeknih_engine_check = add_check_option(search_engine_group_box_layout,
                                                        TranslatingStrings.BUILTIN_SEARCH_TITLE,
                                                        TranslatingStrings.BUILTIN_SEARCH_INFO) 
        
        search_engine_group_box_layout.addStretch(1)
        other_group_box_layout.addWidget(search_engine_group_box)

        # Issue choice
        book_issues_group_box = QGroupBox(TranslatingStrings.BOOK_ISSUE_TITLE, self)
        book_issues_group_box_layout = QHBoxLayout()
        book_issues_group_box.setLayout(book_issues_group_box_layout)
        self.issue_pref_combo = add_combobox_option(book_issues_group_box_layout,
                            TranslatingStrings.BOOK_ISSUE_COMBO_TITLE,
                            TranslatingStrings.BOOK_ISSUE_COMBO_INFO, 
                            PluginPrefsName.ISSUE_PREFERENCE,
                            choices=[_('Default'), _('Czech newest'), _('Czech oldest'), _('Slovak newest'), _('Slovak oldest')])
        
        other_group_box_layout.addWidget(book_issues_group_box)

        # Covers download
        covers_group_box = QGroupBox(TranslatingStrings.COVERS_TITLE, self)
        covers_group_box_layout = QVBoxLayout()
        covers_group_box.setLayout(covers_group_box_layout)
        self.max_covers_spin = add_spin_option(covers_group_box_layout,
                                                TranslatingStrings.COVERS_DOWNLOAD_TITLE,
                                                TranslatingStrings.COVERS_DOWNLOAD_INFO,
                                                PluginPrefsName.MAX_COVERS, min_val=0)

        self.obalkyknih_cover_check = add_check_option(covers_group_box_layout,
                                                        _('Search for additional cover on Obalky knih'),
                                                        _('Tries to search for additional cover using ISBN number on obalkyknih.cz site. Does not count into max cover limit option.'),
                                                        PluginPrefsName.OBALKYKNIH_COVER)
        
        
        other_group_box_layout.addWidget(covers_group_box)

        other_group_box_layout.addStretch(1)

class AuthorsTab(QWidget):
    def __init__(self):
        QWidget.__init__(self)
        layout = QVBoxLayout()
        self.setLayout(layout)

        #Title field
        title_builder_group_box = QGroupBox(TranslatingStrings.APPEND_TITLE_TITLE)
        title_builder_group_box.setMaximumHeight(100)
        layout.addWidget(title_builder_group_box)

        tablebox_layout = QVBoxLayout()
        title_builder_group_box.setLayout(tablebox_layout)
        combobox_layout = QHBoxLayout()

        title_items = get_pref(PluginPrefsName.TITLE_LINE)

        self.title_line_string = QLabel('')
        self.title_line_table = BuilderWidget(self, data=title_items,
                            default_data=DEFAULT_STORE_VALUES[PluginPrefsName.TITLE_LINE],
                            table_type=BuilderTableType.TITLE,
                            add_options=LINE_OPTIONS, 
                            line_preview=self.title_line_string)
        self.title_line_table.populate_table(title_items)
        title_line_layout = QHBoxLayout()
        title = QLabel(MetadataName.TITLE + ': ')
        font = title.font()
        font.setBold(True)
        title.setFont(font)
        title_line_layout.addWidget(title)
        title_line_layout.addWidget(self.title_line_string, 1)
        tablebox_layout.addLayout(title_line_layout)
        tablebox_layout.addLayout(combobox_layout)
        combobox_layout.addWidget(self.title_line_table)

        button_layout = QHBoxLayout()
        combobox_layout.addLayout(button_layout)
        add_btn = QToolButton()
        add_btn.setToolTip(_('Add item (Alt+Shift+W)'))
        add_btn.setIcon(QIcon(I('plus.png')))
        add_btn.clicked.connect(self.title_line_table.add_item)
        add_btn.setShortcut('Alt+Shift+W')
        button_layout.addWidget(add_btn)

        delete_btn = QToolButton()
        delete_btn.setToolTip(_('Delete item (Alt+Shift+S)'))
        delete_btn.setIcon(QIcon(I('minus.png')))
        delete_btn.clicked.connect(self.title_line_table.delete_item)
        delete_btn.setShortcut('Alt+Shift+S')
        button_layout.addWidget(delete_btn)

        move_left_btn = QToolButton()
        move_left_btn.setToolTip(_('Move left (Alt+Shift+A)'))
        move_left_btn.setIcon(QIcon(I('back.png')))
        move_left_btn.clicked.connect(self.title_line_table.move_cols_left)
        move_left_btn.setShortcut('Alt+Shift+A')
        button_layout.addWidget(move_left_btn)

        move_right_btn = QToolButton()
        move_right_btn.setToolTip(_('Move right (Alt+Shift+D)'))
        move_right_btn.setIcon(QIcon(I('forward.png')))
        move_right_btn.clicked.connect(self.title_line_table.move_cols_right)
        move_right_btn.setShortcut('Alt+Shift+D')
        button_layout.addWidget(move_right_btn)

        authors_field_group_box = QGroupBox(TranslatingStrings.APPEND_AUTHORS_TITLE, self)
        layout.addWidget(authors_field_group_box)
        
        group_box_layout = QHBoxLayout()
        authors_field_group_box.setLayout(group_box_layout)


        self.authors_field_check = add_check_option(group_box_layout,
                                                    _('Authors'),
                                                    _('Names of authors will be added into calibre authors metadata field.'),
                                                    PluginPrefsName.AUTHORS_INCLUDE)

        self.translators_field_check = add_check_option(group_box_layout,
                                                    _('Translators'),
                                                    _('Names of translators will be added into calibre authors metadata field.'),
                                                    PluginPrefsName.TRANSLATORS_INCLUDE)

        self.cover_authors_field_check = add_check_option(group_box_layout,
                                                    _('Book cover authors'),
                                                    _('Names of book cover authors will be added into calibre authors metadata field.'),
                                                    PluginPrefsName.COVER_AUTHORS_INCLUDE)

        self.illustrators_field_check = add_check_option(group_box_layout,
                                                    _('Illustrators'),
                                                    _('Names of illustrators will be added into calibre authors metadata field.'),
                                                    PluginPrefsName.ILLUSTRATORS_INCLUDE)
        
        self.authors_role_check = add_check_option(layout, _('Save authors with role'),
                                                   _('Writes role (author, translator, illustrator...) after every author in Authors field.\n'
                                                     '**WONT add role when only Author grabbing is checked'),
                                                   PluginPrefsName.AUTHOR_ROLE)

        self.swap_authors_check = add_check_option(layout, _('Swap authors names with last names'), 
                                                   _('Enable this option if you want to get names in Authors metadata field in format "Surname Name"\n **Global LN, FN Calibre option is prefered'),
                                                   PluginPrefsName.SWAP_AUTHORS)
        
        self.one_author_check = add_check_option(layout, _('Get only one author'),
                                                  _('If the information about the book contains more authors\n - plugin will add only first one.'), 
                                                  PluginPrefsName.ONE_AUTHOR)
        layout.addStretch(1)

class SeriesTab(QWidget):
    def __init__(self):
        QWidget.__init__(self)
        layout = QVBoxLayout()
        self.setLayout(layout)

        #Series field
        series_builder_group_box = QGroupBox(TranslatingStrings.APPEND_SERIES_TITLE)
        series_builder_group_box.setMaximumHeight(100)
        layout.addWidget(series_builder_group_box)

        tablebox_layout = QVBoxLayout()
        series_builder_group_box.setLayout(tablebox_layout)
        combobox_layout = QHBoxLayout()

        series_items = get_pref(PluginPrefsName.SERIES_LINE)

        self.series_line_string = QLabel('')
        self.series_line_table = BuilderWidget(self, data=series_items,
                            default_data=DEFAULT_STORE_VALUES[PluginPrefsName.SERIES_LINE],
                            table_type=BuilderTableType.SERIES,
                            add_options=LINE_OPTIONS,
                            line_preview=self.series_line_string)
        self.series_line_table.populate_table(series_items)
        series_line_layout = QHBoxLayout()
        title = QLabel(MetadataName.SERIES + ': ')
        font = title.font()
        font.setBold(True)
        title.setFont(font)
        series_line_layout.addWidget(title)
        series_line_layout.addWidget(self.series_line_string, 1)
        tablebox_layout.addLayout(series_line_layout)
        tablebox_layout.addLayout(combobox_layout)
        combobox_layout.addWidget(self.series_line_table)

        button_layout = QHBoxLayout()
        combobox_layout.addLayout(button_layout)
        add_btn = QToolButton()
        add_btn.setToolTip(_('Add item (Alt+Shift+W)'))
        add_btn.setIcon(QIcon(I('plus.png')))
        add_btn.clicked.connect(self.series_line_table.add_item)
        add_btn.setShortcut('Alt+Shift+W')
        button_layout.addWidget(add_btn)

        delete_btn = QToolButton()
        delete_btn.setToolTip(_('Delete item (Alt+Shift+S)'))
        delete_btn.setIcon(QIcon(I('minus.png')))
        delete_btn.clicked.connect(self.series_line_table.delete_item)
        delete_btn.setShortcut('Alt+Shift+S')
        button_layout.addWidget(delete_btn)

        move_left_btn = QToolButton()
        move_left_btn.setToolTip(_('Move left (Alt+Shift+A)'))
        move_left_btn.setIcon(QIcon(I('back.png')))
        move_left_btn.clicked.connect(self.series_line_table.move_cols_left)
        move_left_btn.setShortcut('Alt+Shift+A')
        button_layout.addWidget(move_left_btn)

        move_right_btn = QToolButton()
        move_right_btn.setToolTip(_('Move right (Alt+Shift+D)'))
        move_right_btn.setIcon(QIcon(I('forward.png')))
        move_right_btn.clicked.connect(self.series_line_table.move_cols_right)
        move_right_btn.setShortcut('Alt+Shift+D')
        button_layout.addWidget(move_right_btn)

        #Items in Series index metadata field
        self.index_item_options = [
        (MetadataIdentifier.SERIES_INDEX, True, MetadataName.SERIES_INDEX),
        (MetadataIdentifier.EDITION_INDEX, True, MetadataName.EDITION_INDEX),
        (MetadataIdentifier.PUB_YEAR, True, MetadataName.PUB_YEAR),
        (MetadataIdentifier.ORIGINAL_YEAR, True, MetadataName.ORIGINAL_YEAR),
        (MetadataIdentifier.PAGES, True, MetadataName.PAGES),
        (MetadataIdentifier.PRINT_RUN, True, MetadataName.PRINT_RUN),
        (MetadataIdentifier.RATING, True, MetadataName.RATING),
        (MetadataIdentifier.RATING10, True, MetadataName.RATING10),
        (MetadataIdentifier.RATING5, True, MetadataName.RATING5),
        (MetadataIdentifier.RATING_COUNT, True, MetadataName.RATING_COUNT),
        (MetadataIdentifier.READ_TEMPO, True, MetadataName.READ_TEMPO),
        (MetadataIdentifier.ORIG_ID, True, MetadataName.ORIG_ID),
        (MetadataIdentifier.SOURCE_RELEVANCE, True, MetadataName.SOURCE_RELEVANCE)
        ]
        self.series_index_field = add_combobox_option(layout, TranslatingStrings.APPEND_SERIES_INDEX_TITLE, TranslatingStrings.APPEND_SERIES_INDEX_INFO,
                            PluginPrefsName.SERIES_INDEXING_ITEM, choices=[i[2] for i in self.index_item_options])


        # Calibre Mapping Grid
        mapping_group_box = QGroupBox(_('Legie series and editions to calibre series and editions mappings'))
        mapping_group_box.setMaximumHeight(800)
        layout.addWidget(mapping_group_box)

        filter_layout = QHBoxLayout()
        self.series_filter_check = add_check_option(filter_layout, _('Filter series/editions via mappings'), _("Check this and only mapped series and editions below will get parsed to Calibre."), PluginPrefsName.SERIES_FILTER)

        from calibre.gui2 import get_current_db
        all_series = list()
        for s in get_current_db().all_series():
            if s[1] not in all_series:
                all_series.append(s[1])
        self.table_widget = MappingsTableWidget(self, all_series, headers=(_('series/editions'), _('Series/editions')), name='series/editions')
        tags_layout = RemapingTableLayout(self, self.table_widget, PluginPrefsName.KEY_SERIES_MAPPINGS, 'series/editions', self.series_filter_check)
        mapping_group_box.setLayout(tags_layout)


class PublisherTab(QWidget):
    def __init__(self):
        QWidget.__init__(self)
        layout = QVBoxLayout()
        self.setLayout(layout)

        #Items in Published date metadata field
        self.publication_date = add_combobox_option(layout, TranslatingStrings.APPEND_PUBLISHED_TITLE, TranslatingStrings.APPEND_PUBLISHED_INFO,
                            PluginPrefsName.PUBLICATION_DATE, choices=[_('Actual publication'), _('First publication')])
        

        #Publisher field
        publisher_builder_group_box = QGroupBox(TranslatingStrings.APPEND_PUBLISHER_TITLE)
        publisher_builder_group_box.setMaximumHeight(100)
        layout.addWidget(publisher_builder_group_box)

        tablebox_layout = QVBoxLayout()
        publisher_builder_group_box.setLayout(tablebox_layout)
        combobox_layout = QHBoxLayout()

        publisher_items = get_pref(PluginPrefsName.PUBLISHER_LINE)

        self.publisher_line_string = QLabel('')
        self.publisher_line_table = BuilderWidget(self, data=publisher_items,
                            default_data=DEFAULT_STORE_VALUES[PluginPrefsName.PUBLISHER_LINE],
                            table_type=BuilderTableType.PUBLISHER,
                            add_options=LINE_OPTIONS,
                            line_preview=self.publisher_line_string)

        self.publisher_line_table.populate_table(publisher_items)
        title_line_layout = QHBoxLayout()
        title = QLabel(MetadataName.PUBLISHER + ': ')
        font = title.font()
        font.setBold(True)
        title.setFont(font)
        title_line_layout.addWidget(title)
        title_line_layout.addWidget(self.publisher_line_string, 1)
        tablebox_layout.addLayout(title_line_layout)
        tablebox_layout.addLayout(combobox_layout)
        combobox_layout.addWidget(self.publisher_line_table)

        button_layout = QHBoxLayout()
        combobox_layout.addLayout(button_layout)
        add_btn = QToolButton()
        add_btn.setToolTip(_('Add item (Alt+Shift+W)'))
        add_btn.setIcon(QIcon(I('plus.png')))
        add_btn.clicked.connect(self.publisher_line_table.add_item)
        add_btn.setShortcut('Alt+Shift+W')
        button_layout.addWidget(add_btn)

        delete_btn = QToolButton()
        delete_btn.setToolTip(_('Delete item (Alt+Shift+S)'))
        delete_btn.setIcon(QIcon(I('minus.png')))
        delete_btn.clicked.connect(self.publisher_line_table.delete_item)
        delete_btn.setShortcut('Alt+Shift+S')
        button_layout.addWidget(delete_btn)

        move_left_btn = QToolButton()
        move_left_btn.setToolTip(_('Move left (Alt+Shift+A)'))
        move_left_btn.setIcon(QIcon(I('back.png')))
        move_left_btn.clicked.connect(self.publisher_line_table.move_cols_left)
        move_left_btn.setShortcut('Alt+Shift+A')
        button_layout.addWidget(move_left_btn)

        move_right_btn = QToolButton()
        move_right_btn.setToolTip(_('Move right (Alt+Shift+D)'))
        move_right_btn.setIcon(QIcon(I('forward.png')))
        move_right_btn.clicked.connect(self.publisher_line_table.move_cols_right)
        move_right_btn.setShortcut('Alt+Shift+D')
        button_layout.addWidget(move_right_btn)

        # Calibre Mapping Grid
        mapping_group_box = QGroupBox(_('Legie publishers to calibre publisher mappings'))
        mapping_group_box.setMaximumHeight(800)
        layout.addWidget(mapping_group_box)

        filter_layout = QHBoxLayout()
        self.publishers_filter_check = add_check_option(filter_layout, _('Filter publishers via mappings'), _("Check this and only mapped publishers below will get parsed to Calibre."), PluginPrefsName.PUBLISHER_FILTER)
        from calibre.gui2 import get_current_db
        all_publishers = list()
        for s in get_current_db().all_publishers():
            if s[1] not in all_publishers:
                all_publishers.append(s[1])
        self.table_widget = MappingsTableWidget(self, all_publishers, headers=(_('publisher'), _('Publisher')), name='publishers')
        tags_layout = RemapingTableLayout(self, self.table_widget, PluginPrefsName.KEY_PUBLISHER_MAPPINGS, 'publishers', self.publishers_filter_check)
        mapping_group_box.setLayout(tags_layout)

class TagTab(QWidget):
    def __init__(self):
        QWidget.__init__(self)
        #Tags
        tags_group_boxlayout = QVBoxLayout()
        self.setLayout(tags_group_boxlayout)

        #Append tags group box
        append_tags_group_box = QGroupBox(TranslatingStrings.APPEND_TAGS_TITLE, self)
        tags_group_boxlayout.addWidget(append_tags_group_box)

        table_layout = QHBoxLayout()
        append_tags_group_box.setLayout(table_layout)

        tag_items = get_pref(PluginPrefsName.APPEND_TO_TAG) \
        if get_pref(PluginPrefsName.APPEND_TO_TAG) is not None and \
        len(get_pref(PluginPrefsName.APPEND_TO_TAG)) == len(TAG_OPTIONS) else TAG_OPTIONS

        self.tag_items_table = BuilderWidget(self, data=tag_items,
                            default_data=TAG_OPTIONS,
                            table_type=BuilderTableType.TAG,
                            add_options=TAG_OPTIONS)

        table_layout.addWidget(self.tag_items_table)
        self.tag_items_table.populate_table(tag_items)

        # Calibre Genre Mapping Grid
        genre_group_box = QGroupBox(_('Legie category to calibre tag mappings'))
        genre_group_box.setMaximumHeight(800)
        tags_group_boxlayout.addWidget(genre_group_box)
        #self.l.addWidget(genre_group_box, self.l.rowCount(), 0, 1, 2)
        genre_group_box_layout = QVBoxLayout()
        genre_group_box.setLayout(genre_group_box_layout)

        filter_layout = QHBoxLayout()
        self.genre_filter_check = add_check_option(filter_layout, _('Filter category via mappings'), _("Check this and only mapped category below will get parsed to Calibre."), PluginPrefsName.CATEGORY_FILTER)

        #from calibre.gui2 import get_current_db
        #all_tags = get_current_db().all_tags()
        self.table_widget = MappingsTableWidget(self, get_pref(PluginPrefsName.KEY_CATEGORY_MAPPINGS), name='category', default_data=DEFAULT_CATEGORY_MAPPINGS)
        tags_layout = RemapingTableLayout(self, self.table_widget, PluginPrefsName.KEY_CATEGORY_MAPPINGS, 'category', self.genre_filter_check)
        genre_group_box_layout.addLayout(tags_layout)

class CommentsTab(QWidget):
    def __init__(self):
        QWidget.__init__(self)
        layout = QVBoxLayout()
        self.setLayout(layout)
        # Comment builder
        comment_group_box = QGroupBox(TranslatingStrings.APPEND_COMMENTS_TITLE)
        comment_group_box_layout = QVBoxLayout()
        layout.addWidget(comment_group_box)
        comment_group_box.setLayout(comment_group_box_layout)

        table_layout = QHBoxLayout()
        comment_group_box_layout.addLayout(table_layout)

        comment_items = get_pref(PluginPrefsName.APPEND_TO_COMMENTS)

        self.comments_arrange_table = BuilderWidget(self, data=comment_items,
                            default_data=DEFAULT_STORE_VALUES[PluginPrefsName.APPEND_TO_COMMENTS],
                            table_type=BuilderTableType.COMMENT,
                            add_options=COMMENT_OPTIONS)

        table_layout.addWidget(self.comments_arrange_table)
        self.comments_arrange_table.populate_table(get_pref(PluginPrefsName.APPEND_TO_COMMENTS))

        table_button_layout = QVBoxLayout()
        table_layout.addLayout(table_button_layout)
        plus_button = QToolButton(self)
        plus_button.setToolTip(_('Add item (Alt+A)'))
        plus_button.setIcon(QIcon(I('plus.png')))
        plus_button.setShortcut('Alt+A')
        plus_button.clicked.connect(self.comments_arrange_table.add_item)
        table_button_layout.addWidget(plus_button)
        minus_button = QToolButton(self)
        minus_button.setToolTip(_('Delete item (Alt+D)'))
        minus_button.setIcon(QIcon(I('minus.png')))
        minus_button.setShortcut('Alt+D')
        minus_button.clicked.connect(self.comments_arrange_table.delete_item)
        table_button_layout.addWidget(minus_button)

        add_all_button = QToolButton(self)
        add_all_button.setToolTip(_('Add all items at once (Alt+Q)'))
        add_all_button.setIcon(QIcon(I('sort.png')))
        add_all_button.setShortcut('Alt+Q')
        add_all_button.clicked.connect(self.comments_arrange_table.add_all_items)
        table_button_layout.addWidget(add_all_button)

        reset_button = QToolButton(self)
        reset_button.setToolTip(_('Reset to defaults (Alt+R)'))
        reset_button.setIcon(QIcon(I('restart.png')))
        reset_button.setShortcut('Alt+R')
        reset_button.clicked.connect(self.comments_arrange_table.reset_to_defaults)
        table_button_layout.addWidget(reset_button)

        move_up_button = QToolButton(self)
        move_up_button.setToolTip(_('Move item up (Alt+W)'))
        move_up_button.setIcon(QIcon(I('arrow-up.png')))
        move_up_button.setShortcut('Alt+Up')
        move_up_button.setShortcut('Alt+W')
        move_up_button.clicked.connect(self.comments_arrange_table.move_rows_up)
        table_button_layout.addWidget(move_up_button)
        move_down_button = QToolButton(self)
        move_down_button.setToolTip(_('Move item down (Alt+S)'))
        move_down_button.setIcon(QIcon(I('arrow-down.png')))
        move_down_button.setShortcut('Alt+Down')
        move_down_button.setShortcut('Alt+S')
        move_down_button.clicked.connect(self.comments_arrange_table.move_rows_down)
        table_button_layout.addWidget(move_down_button)

class RemapingTableLayout(QVBoxLayout):
    def __init__(self, parent, table_widget, prefs, name, filter_check_widget=None):
        super(RemapingTableLayout, self).__init__(parent)
        self.parent = parent
        self.name = name
        self.prefs = prefs
        self.table_widget = table_widget
        
        if filter_check_widget:
            filter_check_layout = QVBoxLayout()
            filter_check_layout.addWidget(filter_check_widget)
            self.addLayout(filter_check_layout)

        hbox_layout = QHBoxLayout()
        self.addLayout(hbox_layout)

        hbox_layout.addWidget(self.table_widget)

        button_layout = QVBoxLayout()
        hbox_layout.addLayout(button_layout)

        add_mapping_button = QToolButton()
        add_mapping_button.setToolTip(_('Add mapping (Alt+A)'))
        add_mapping_button.setIcon(QIcon(I('plus.png')))
        add_mapping_button.clicked.connect(self.table_widget.add_mapping)
        add_mapping_button.setShortcut('Alt+A')
        button_layout.addWidget(add_mapping_button)

        remove_mapping_button = QToolButton()
        remove_mapping_button.setToolTip(_('Delete mapping (Alt+D)'))
        remove_mapping_button.setIcon(QIcon(I('minus.png')))
        remove_mapping_button.clicked.connect(self.table_widget.delete_mapping)
        remove_mapping_button.setShortcut('Alt+D')
        button_layout.addWidget(remove_mapping_button)

        rename_genre_button = QToolButton()
        rename_genre_button.setToolTip(_('Rename item (Alt+S)'))
        rename_genre_button.setIcon(QIcon(I('edit-undo.png')))
        rename_genre_button.clicked.connect(self.table_widget.rename_genre)
        rename_genre_button.setShortcut('Alt+S')
        button_layout.addWidget(rename_genre_button)

        reset_defaults_button = QToolButton()
        reset_defaults_button.setToolTip(_('Reset to plugin default mappings (Alt+R)'))
        reset_defaults_button.setIcon(QIcon(I('restart.png')))
        reset_defaults_button.clicked.connect(self.table_widget.reset_to_defaults)
        reset_defaults_button.setShortcut('Alt+R')
        button_layout.addWidget(reset_defaults_button)

        # Populate the table
        self.table_widget.populate_table(get_pref(prefs))

class IdentifiersTab(QWidget):
    def __init__(self):
        QWidget.__init__(self)

        layout = QVBoxLayout()
        self.setLayout(layout)

        identifiers_group_boxlayout = QVBoxLayout()
        layout.addLayout(identifiers_group_boxlayout)
        #Additional info group box
        append_identifiers_group_box = QGroupBox(TranslatingStrings.APPEND_IDENTIFIER_TITLE, self)
        identifiers_group_boxlayout.addWidget(append_identifiers_group_box)

        table_layout = QVBoxLayout()
        append_identifiers_group_box.setLayout(table_layout)

        custom_cols_info = QLabel(TranslatingStrings.CUSTOM_COLUMNS_INFO)
        custom_cols_info.setWordWrap(True)
        custom_cols_info.setOpenExternalLinks(True)
        table_layout.addWidget(custom_cols_info)

        identifier_items = get_pref(PluginPrefsName.APPEND_TO_IDENTIFIERS) \
        if get_pref(PluginPrefsName.APPEND_TO_IDENTIFIERS) is not None and \
            len(get_pref(PluginPrefsName.APPEND_TO_IDENTIFIERS)) == len(IDENTIFIER_OPTIONS) else IDENTIFIER_OPTIONS

        self.identifier_items_table = BuilderWidget(self, data=identifier_items,
                            default_data=DEFAULT_STORE_VALUES[PluginPrefsName.APPEND_TO_IDENTIFIERS],
                            table_type=BuilderTableType.IDENTIFIER,
                            add_options=IDENTIFIER_OPTIONS)
        table_layout.addWidget(self.identifier_items_table)
        self.identifier_items_table.populate_table(identifier_items)

        layout.addStretch(1)