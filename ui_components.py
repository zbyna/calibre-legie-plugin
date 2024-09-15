#!/usr/bin/env python
# vim:fileencoding=UTF-8:ts=4:sw=4:sta:et:sts=4:ai
from __future__ import (unicode_literals, division, absolute_import,
                        print_function)

__license__   = 'GPL v3'
__copyright__ = '2024 seeder'
__docformat__ = 'restructuredtext en'

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

from enum import Enum
from .prefs import MetadataIdentifier, MetadataName, TranslatingStrings

# python/pyqt backwards compability
from calibre import as_unicode
try:
    from calibre.gui2 import QVariant
    del QVariant
except ImportError:
    is_qt4 = False
    convert_qvariant = lambda x: x
else:
    is_qt4 = True
    def convert_qvariant(x):
        vt = x.type()
        if vt == x.String:
            return as_unicode(x.toString())
        if vt == x.List:
            return [convert_qvariant(i) for i in x.toList()]
        return x.toPyObject()

try:
    load_translations()
except NameError:
    pass # load_translations() added in calibre 1.9

class ReadOnlyTableWidgetItem(QTableWidgetItem):

    def __init__(self, text):
        if text is None:
            text = ''
        try:
            QTableWidgetItem.__init__(self, text, QTableWidgetItem.ItemType.UserType)
            self.setFlags(Qt.ItemFlag.ItemIsSelectable|Qt.ItemFlag.ItemIsEnabled)
        except (AttributeError, NameError) as e:
            QTableWidgetItem.__init__(self, text, QTableWidgetItem.UserType)
            self.setFlags(Qt.ItemIsSelectable|Qt.ItemIsEnabled)

class ReadOnlyCheckableTableWidgetItem(ReadOnlyTableWidgetItem):

    def __init__(self, text, checked=False, is_tristate=False):
        super(ReadOnlyCheckableTableWidgetItem, self).__init__(text)
        try:
            self.setFlags(Qt.ItemFlag(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled ))
        except:
            self.setFlags(Qt.ItemFlags(Qt.ItemIsSelectable | Qt.ItemIsUserCheckable | Qt.ItemIsEnabled ))
        if is_tristate:
            try:
                self.setFlags(self.flags() | Qt.ItemFlag.ItemIsAutoTristate)
            except:
                self.setFlags(self.flags() | Qt.ItemIsTristate)
        if checked:
            try:
                self.setCheckState(Qt.CheckState.Checked)
            except:
                self.setCheckState(Qt.Checked)
        else:
            if is_tristate and checked is None:
                try:
                    self.setCheckState(Qt.CheckState.PartiallyChecked)
                except:
                    self.setCheckState(Qt.PartiallyChecked)
            else:
                try:
                    self.setCheckState(Qt.CheckState.Unchecked)
                except:
                    self.setCheckState(Qt.Unchecked)

    def get_boolean_value(self):
        '''
        Return a boolean value indicating whether checkbox is checked
        If this is a tristate checkbox, a partially checked value is returned as None
        '''
        try:
            if self.checkState() == Qt.CheckState.PartiallyChecked:
                return None
            else:
                return self.checkState() == Qt.CheckState.Checked
        except:
            if self.checkState() == Qt.PartiallyChecked:
                return None
            else:
                return self.checkState() == Qt.Checked

class MappingsTableWidget(QTableWidget):
    def __init__(self, parent, all_tags, headers=(MetadataName.GENRES, MetadataName.TAGS), name='genre', default_data=None, **kwargs):
        QTableWidget.__init__(self, parent, **kwargs)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tags_values = all_tags
        self.headers = headers
        self.default_data = default_data
        self.name = name

    def populate_table(self, tag_mappings):
        self.clear()
        self.setAlternatingRowColors(True)
        self.setRowCount(len(tag_mappings))
        header_labels = [self.headers[0], TranslatingStrings.MAPS_TO_CALIBRE + ' ' + self.headers[1]]
        self.setColumnCount(len(header_labels))
        self.setHorizontalHeaderLabels(header_labels)
        self.verticalHeader().setDefaultSectionSize(24)
        self.horizontalHeader().setStretchLastSection(True)

        for row, genre in enumerate(sorted(tag_mappings.keys(), key=lambda s: (s.lower(), s))):
            self.populate_table_item(row, genre, sorted(tag_mappings[genre]))

        self.set_minimum_column_width(0, 300)
        self.resizeColumnToContents(0)
        self.setSortingEnabled(False)
        if len(tag_mappings) > 0:
            self.selectRow(0)

    def set_minimum_column_width(self, col, minimum):
        if self.columnWidth(col) < minimum:
            self.setColumnWidth(col, minimum)

    def populate_table_item(self, row, genre, tags):
        self.setItem(row, 0, ReadOnlyTableWidgetItem(genre))
        tags_value = ', '.join(tags)
        # Add a widget under the cell just for sorting purposes
        self.setItem(row, 1, QTableWidgetItem(tags_value))
        self.setCellWidget(row, 1, self.create_tags_edit(tags_value, row))

    def create_tags_edit(self, value, row):
        try:
            from calibre.gui2.complete2 import EditWithComplete
            tags_edit = EditWithComplete(self)
        except ImportError:
            from calibre.gui2.complete import MultiCompleteComboBox
            tags_edit = MultiCompleteComboBox(self)
        tags_edit.set_add_separator(False)
        tags_edit.update_items_cache(self.tags_values)
        tags_edit.setText(value)

        #tags_edit.editingFinished.connect(partial(self.tags_editing_finished, row, tags_edit))
        return tags_edit

    def tags_editing_finished(self, row, tags_edit):
        # Update our underlying widget for sorting
        self.item(row, 1).setText(tags_edit.text())

    def get_data(self):
        tag_mappings = {}
        for row in range(self.rowCount()):
            genre = as_unicode(self.item(row, 0).text()).strip()
            tags_text = as_unicode(self.cellWidget(row, 1).text()).strip()
            tag_values = tags_text.split(',')
            tags_list = []
            for tag in tag_values:
                if len(tag.strip()) > 0:
                    tags_list.append(tag.strip())
            tag_mappings[genre] = tags_list
        return tag_mappings

    def select_genre(self, genre_name):
        for row in range(self.rowCount()):
            if as_unicode(self.item(row, 0).text()) == genre_name:
                self.setCurrentCell(row, 1)
                return

    def get_selected_genre(self):
        if self.currentRow() >= 0:
            return as_unicode(self.item(self.currentRow(), 0).text())

    def add_mapping(self):
        from calibre.gui2 import error_dialog
        new_genre_name, ok = QInputDialog.getText(self, TranslatingStrings.ADD_MAPPING_TITLE,
                    TranslatingStrings.ADD_MAPPING_INFO, text='')
        if not ok:
            # Operation cancelled
            return
        new_genre_name = as_unicode(new_genre_name).strip().replace(',', ';')
        if not new_genre_name:
            return
        # Verify it does not clash with any other mappings in the list
        data = self.get_data()
        for genre_name in data.keys():
            if genre_name.lower() == new_genre_name.lower():
                return error_dialog(self, TranslatingStrings.ADD_MAPPING_ERROR_TITLE, TranslatingStrings.ADD_MAPPING_ERROR_INFO, show=True)
        data[new_genre_name] = []
        self.populate_table(data)
        self.select_genre(new_genre_name)

    def delete_mapping(self):
        from calibre.gui2 import question_dialog
        if not self.selectionModel().hasSelection():
            return
        if not question_dialog(self, TranslatingStrings.CONFIRMATION_TITLE, '<p>'+
                TranslatingStrings.DELETE_MAPPING_INFO,
                show_copy_button=False):
            return
        for row in reversed(sorted(self.selectionModel().selectedRows())):
            self.removeRow(row.row())

    def rename_genre(self):
        from calibre.gui2 import error_dialog
        selected_genre = self.get_selected_genre()
        if not selected_genre:
            return
        new_genre_name, ok = QInputDialog.getText(self, TranslatingStrings.RENAME_MAPPING_TITLE,
                    TranslatingStrings.RENAME_MAPPING_INFO, text=selected_genre)
        if not ok:
            # Operation cancelled
            return
        new_genre_name = as_unicode(new_genre_name).strip().replace(',', ';')
        if not new_genre_name or new_genre_name == selected_genre:
            return
        data = self.get_data()
        if new_genre_name.lower() != selected_genre.lower():
            # Verify it does not clash with any other mappings in the list
            for genre_name in data.keys():
                if genre_name.lower() == new_genre_name.lower():
                    return error_dialog(self, TranslatingStrings.RENAME_MAPPING_ERROR_TITLE, TranslatingStrings.RENAME_MAPPING_ERROR_INFO, show=True)
        data[new_genre_name] = data[selected_genre]
        del data[selected_genre]
        self.populate_table(data)
        self.select_genre(new_genre_name)

    def reset_to_defaults(self):
        from calibre.gui2 import question_dialog
        if not question_dialog(self, TranslatingStrings.CONFIRMATION_TITLE,
            TranslatingStrings.DEFAULTS_MAPPING_RESET_INFO,
                show_copy_button=False):
            return
        self.populate_table(self.default_data)

class BuilderWidgetPosition(Enum):
    VERTICAL = 'vertical'
    HORIZONTAL = 'horizontal'

class BuilderTableType(Enum):
    TAG         =   'tag'
    COMMENT     =   'comment'
    IDENTIFIER  =   'identifier'
    TITLE       =   'title'
    SERIES      =   'series'
    PUBLISHER   =   'publisher'

class BuilderWidget(QTableWidget):
    def __init__(self, parent, table_type=BuilderTableType.COMMENT, data=None, default_data=None, line_preview=None, add_options=None, **kwargs):
        QTableWidget.__init__(self, parent, **kwargs)
        self.table_type = table_type
        self.position = BuilderWidgetPosition.HORIZONTAL if table_type in (BuilderTableType.TITLE, BuilderTableType.SERIES, BuilderTableType.PUBLISHER) else BuilderWidgetPosition.VERTICAL
        self.default_data = default_data
        self.add_options = add_options
        self.line_preview = line_preview
        self.data = data

        header_labels = kwargs.get('header_labels', None)
        if header_labels:
            self.header_labels = header_labels
        elif self.table_type == BuilderTableType.COMMENT:
            self.header_labels = [TranslatingStrings.COMMENT_ITEM]
        elif self.table_type == BuilderTableType.TAG:
            self.header_labels = [TranslatingStrings.TAG_ITEM]
        elif self.table_type == BuilderTableType.IDENTIFIER:
            self.header_labels = [TranslatingStrings.METADATA_ITEM, TranslatingStrings.IDENTIFIER_FORMAT]
        elif self.table_type == BuilderTableType.TITLE:
            self.header_labels = [MetadataName.TITLE + ': ']
        elif self.table_type == BuilderTableType.SERIES:
            self.header_labels = [MetadataName.SERIES + ': ']
        elif self.table_type == BuilderTableType.PUBLISHER:
            self.header_labels = [MetadataName.PUBLISHER + ': ']

        self.setSortingEnabled(False)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        if self.position == BuilderWidgetPosition.VERTICAL:
            self.setMinimumSize(50, 0)
            self.setAlternatingRowColors(True)
            self.setSelectionBehavior(QAbstractItemView.SelectRows)
        elif self.position == BuilderWidgetPosition.HORIZONTAL:
            self.setMinimumSize(0, 50)
            self.setAlternatingRowColors(False)
            self.setSelectionBehavior(QAbstractItemView.SelectColumns)

        if data:
            self.populate_table(data)
        else:
            self.populate_table(default_data)
        if isinstance(line_preview, QLabel):
            line_preview.setText(self.get_string())
     
    def __setattr__(self, attr, value):
        if attr == 'data' and self.line_preview and isinstance(self.line_preview, QLabel):
            self.line_preview.setText(self.get_string())
        QTableWidget.__setattr__(self, attr, value)
    
    def setMinimumColumnWidth(self, col, minimum):
        if self.columnWidth(col) < minimum:
            self.setColumnWidth(col, minimum)

    def select_and_scroll_to_row(self, row):
        self.selectRow(row)
        self.scrollToItem(self.currentItem())

    def swap_row_col_widgets(self, src, dest):
        """
        Swaps src and dest row (for VERTICAL position widget) or col (for HORIZONTAL position widget).
        """
        self.blockSignals(True)
        if self.position == BuilderWidgetPosition.VERTICAL:
            self.insertRow(dest)
            for col in range(self.columnCount()):
                self.setItem(dest, col, self.takeItem(src, col))
            self.removeRow(src)
        elif self.position == BuilderWidgetPosition.HORIZONTAL:
            self.insertColumn(dest)
            for row in range(self.rowCount()):
                self.setItem(row, dest, self.takeItem(row, src))
            self.removeColumn(src)
            self.resizeColumnsToContents()
        self.blockSignals(False)

    def move_cols_left(self):
        cols = self.selectionModel().selectedColumns()
        if len(cols) == 0:
            return
        first_sel_col = cols[0].column()
        if first_sel_col <= 0:
            return
        # Workaround for strange selection bug in Qt which "alters" the selection
        # in certain circumstances which meant move down only worked properly "once"
        selcols = []
        for col in cols:
            selcols.append(col.column())
        selcols.sort()
        for selcol in selcols:
            self.swap_row_col_widgets(selcol - 1, selcol + 1)
        #self.books[selrow-1], self.books[selrow] = self.books[selrow], self.books[selrow-1]

        scroll_to_row = first_sel_col - 1
        if scroll_to_row > 0:
            scroll_to_row = scroll_to_row - 1
        self.scrollToItem(self.item(scroll_to_row, 0))

        if self.line_preview:
            self.line_preview.setText(self.get_string())

    def move_cols_right(self):
        cols = self.selectionModel().selectedColumns()
        if len(cols) == 0:
            return
        last_sel_col = cols[-1].column()
        if last_sel_col == self.columnCount() - 1:
            return
        # Workaround for strange selection bug in Qt which "alters" the selection
        # in certain circumstances which meant move down only worked properly "once"
        selcols = []
        for col in cols:
            selcols.append(col.column())
        selcols.sort()
        for selcol in reversed(selcols):
            self.swap_row_col_widgets(selcol + 2, selcol)

        scroll_to_row = last_sel_col + 1
        if scroll_to_row < self.columnCount() - 1:
            scroll_to_row = scroll_to_row + 1
        self.scrollToItem(self.item(scroll_to_row, 0))

        if self.line_preview:
            self.line_preview.setText(self.get_string())
        # self.renumber_series()

    def move_rows_up(self):
        rows = self.selectionModel().selectedRows()
        if len(rows) == 0:
            return
        first_sel_row = rows[0].row()
        if first_sel_row <= 0:
            return
        # Workaround for strange selection bug in Qt which "alters" the selection
        # in certain circumstances which meant move down only worked properly "once"
        selrows = []
        for row in rows:
            selrows.append(row.row())
        selrows.sort()
        for selrow in selrows:
            self.swap_row_col_widgets(selrow - 1, selrow + 1)

        scroll_to_row = first_sel_row - 1
        if scroll_to_row > 0:
            scroll_to_row = scroll_to_row - 1
        self.scrollToItem(self.item(scroll_to_row, 0))

    def move_rows_down(self):
        rows = self.selectionModel().selectedRows()
        if len(rows) == 0:
            return
        last_sel_row = rows[-1].row()
        if last_sel_row == self.rowCount() - 1:
            return
        # Workaround for strange selection bug in Qt which "alters" the selection
        # in certain circumstances which meant move down only worked properly "once"
        selrows = []
        for row in rows:
            selrows.append(row.row())
        selrows.sort()
        for selrow in reversed(selrows):
            self.swap_row_col_widgets(selrow + 2, selrow)

        scroll_to_row = last_sel_row + 1
        if scroll_to_row < self.rowCount() - 1:
            scroll_to_row = scroll_to_row + 1
        self.scrollToItem(self.item(scroll_to_row, 0))

    def reset_to_defaults(self):
        from calibre.gui2 import question_dialog
        if not question_dialog(self, TranslatingStrings.CONFIRMATION_TITLE, '<p>'+
                TranslatingStrings.DEFAULTS_BUILDER_RESET_INFO,
                show_copy_button=False):
            return
        self.setColumnCount(0)
        self.populate_table(self.default_data)
        if self.line_preview:
            self.line_preview.setText(self.get_string())

    def delete_item(self):
        from calibre.gui2 import question_dialog
        if not self.selectionModel().hasSelection():
                return
        if not question_dialog(self, TranslatingStrings.CONFIRMATION_TITLE, '<p>'+
                TranslatingStrings.DELETE_ITEM_INFO,
                show_copy_button=False):
            return
        if self.position == BuilderWidgetPosition.VERTICAL:
            for row in reversed(sorted(self.selectionModel().selectedRows())):
                self.removeRow(row.row())
        elif self.position == BuilderWidgetPosition.HORIZONTAL:
            for col in reversed(sorted(self.selectionModel().selectedColumns())):
                self.removeColumn(col.column())
        if self.line_preview:
            self.line_preview.setText(self.get_string())

    def add_item(self):
        item, ok = QInputDialog().getItem(self, TranslatingStrings.ADD_ITEM_TITLE,
                                            TranslatingStrings.CHOOSE_ITEM_TITLE, [tuple_item[2] for tuple_item in self.add_options], 0, False)
        if ok and item:
            new_items = self.get_data()
            new_item = [i for i in self.add_options if item in i][0]
            if new_item[0] == MetadataIdentifier.CUSTOM_TEXT:
                text, ok_text = QInputDialog().getText(self, TranslatingStrings.ADD_CUSTOM_TEXT_TITLE,
                                            TranslatingStrings.ADD_CUSTOM_TEXT_INFO)
                if not ok_text or not text:
                    return
                else:
                    new_item = (MetadataIdentifier.CUSTOM_TEXT, True, text)
            new_items.append(new_item)
            self.populate_table(new_items)
            if self.line_preview:
                self.line_preview.setText(self.get_string())
            if self.position == BuilderWidgetPosition.VERTICAL:
                self.selectRow(self.rowCount() - 1)
            elif self.position == BuilderWidgetPosition.HORIZONTAL:
                self.selectColumn(self.columnCount() - 1)
        if not item:
            return

    def add_all_items(self):
        from calibre.gui2 import question_dialog
        if not question_dialog(self, TranslatingStrings.CONFIRMATION_TITLE, '<p>'+
                TranslatingStrings.APPEND_ALL_INFO,
                show_copy_button=False):
            return

        new_items = ([i for i in self.add_options])
        if self.position == BuilderWidgetPosition.VERTICAL:
            self.setRowCount(0)
            self.populate_table(new_items)
            self.selectRow(self.rowCount() - 1)
        elif self.position == BuilderWidgetPosition.HORIZONTAL:
            self.setColumnCount(0)
            self.populate_table(new_items)
            self.selectColumn(self.columnCount() - 1)

    def populate_table(self, data):
        self.clear()
        if self.position == BuilderWidgetPosition.VERTICAL:
            self.setRowCount(len(data))
            self.setColumnCount(len(self.header_labels))
            self.setHorizontalHeaderLabels(self.header_labels)
            self.horizontalHeader().setStretchLastSection(True)

            for row, item in enumerate(data):
                self.populate_table_item(row, item)

            self.setMinimumColumnWidth(0, 150)
            self.selectRow(0)

        elif self.position == BuilderWidgetPosition.HORIZONTAL:
            self.setColumnCount(len(data))
            self.setRowCount(len(self.header_labels))
            self.setVerticalHeaderLabels(self.header_labels)
            self.horizontalHeader().setDefaultSectionSize(32)
            self.verticalHeader().setStretchLastSection(True)

            for col, item in enumerate(data):
                self.populate_table_item(col, item)
            #self.setMinimumColumnWidth(0, 150)
            self.selectColumn(0)
        self.resizeColumnsToContents()
        self.data = data

    def populate_table_item(self, pos, item):
        if self.table_type == BuilderTableType.COMMENT:
            name_widget = ReadOnlyTableWidgetItem(item[2])
            try:
                name_widget.setData(Qt.ItemDataRole.UserRole, item[0])
            except:
                name_widget.setData(Qt.UserRole, item[0])
            self.setItem(pos, 0, name_widget)
        elif self.table_type == BuilderTableType.TAG:
            name_widget = ReadOnlyCheckableTableWidgetItem(item[2], checked=item[1])
            try:
                name_widget.setData(Qt.ItemDataRole.UserRole, item[0])
            except:
                name_widget.setData(Qt.UserRole, item[0])
            self.setItem(pos, 0, name_widget)
        elif self.table_type == BuilderTableType.IDENTIFIER:
            name_widget = ReadOnlyCheckableTableWidgetItem(item[2], checked=item[1])
            identifier_format = ReadOnlyTableWidgetItem(item[3])
            try:
                name_widget.setData(Qt.ItemDataRole.UserRole, item[0])
            except:
                name_widget.setData(Qt.UserRole, item[0])
            self.setItem(pos, 0, name_widget)
            self.setItem(pos, 1, identifier_format)
        elif self.table_type in (BuilderTableType.TITLE, BuilderTableType.SERIES, BuilderTableType.PUBLISHER):
            name_widget = ReadOnlyTableWidgetItem(item[2])
            # Bold text when not custom
            if item[0] != MetadataIdentifier.CUSTOM_TEXT:
                try:
                    font = name_widget.font()
                    font.setBold(True)
                    name_widget.setFont(font)
                except:
                    font = name_widget.font()
                    font.setBold(True)
                    name_widget.setFont(font)
            try:
                name_widget.setData(Qt.ItemDataRole.UserRole, item[0])
            except:
                name_widget.setData(Qt.UserRole, item[0])
            self.setItem(0, pos, name_widget)
            self.resizeColumnsToContents()

    def get_string(self):
        return ''.join([tupl[2] for tupl in self.get_data()])

    def get_data(self):
        if self.table_type == BuilderTableType.COMMENT:
            items = []
            for row in range(self.rowCount()):
                try:
                    item_id = convert_qvariant(self.item(row, 0).data(Qt.ItemDataRole.UserRole))
                except:
                    item_id = convert_qvariant(self.item(row, 0).data(Qt.UserRole))
                item_name = as_unicode(str(self.item(row, 0).text()))
                #active = self.item(row, 0).get_boolean_value()
                items.append((item_id, True, item_name))
            return items
        elif self.table_type == BuilderTableType.TAG:
            items = []
            for row in range(self.rowCount()):
                try:
                    item_id = convert_qvariant(self.item(row, 0).data(Qt.ItemDataRole.UserRole))
                except:
                    item_id = convert_qvariant(self.item(row, 0).data(Qt.UserRole))
                item_name = as_unicode(str((self.item(row, 0).text())))
                active = self.item(row, 0).get_boolean_value()
                items.append((item_id, active, item_name))
            return items
        elif self.table_type == BuilderTableType.IDENTIFIER:
            items = []
            for row in range(self.rowCount()):
                try:
                    item_id = convert_qvariant(self.item(row, 0).data(Qt.ItemDataRole.UserRole))
                except:
                    item_id = convert_qvariant(self.item(row, 0).data(Qt.UserRole))
                item_name = as_unicode(str((self.item(row, 0).text())))
                active = self.item(row, 0).get_boolean_value()
                identifier_format = as_unicode(str((self.item(row, 1).text())))
                items.append((item_id, active, item_name, identifier_format))
            return items
        elif self.table_type in (BuilderTableType.TITLE, BuilderTableType.SERIES, BuilderTableType.PUBLISHER):
            items = []
            for col in range(self.columnCount()):
                try:
                    item_id = convert_qvariant(self.item(0, col).data(Qt.ItemDataRole.UserRole))
                except:
                    item_id = convert_qvariant(self.item(0, col).data(Qt.UserRole))
                item_name = as_unicode(str((self.item(0, col).text())))
                items.append((item_id, True, item_name))
            return items
