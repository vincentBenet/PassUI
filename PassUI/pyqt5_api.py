import os
import sys
import types
import shutil
import webbrowser

import pyperclip
import validators

import PyQt5
import PyQt5.uic
import PyQt5.QtCore
import PyQt5.QtWidgets
from PyQt5 import Qt, QtGui
from PyQt5.QtCore import Qt

"""Top priority"""
# TODO: Init pass directory

"""TODO"""
# TODO: git pull
# TODO: git push
# TODO: git init
# TODO: passpy init
# TODO: link git remote url

"""Features"""
# TODO: Import windows wifi passwords
# TODO: Import windows chrome passwords
# TODO: Import windows edges passwords
# TODO: Import windows firefox passwords

# TODO: Import MAC chrome passwords
# TODO: Import MAC safari passwords
# TODO: Import MAC wifi passwords


def get_rel_path(item):
    parents = []
    current = item
    while True:
        if current is None:
            break
        parent = current.parent()
        if parent is None:
            break
        parents.append(parent)
        current = parent
    parents.reverse()
    return os.sep.join([parent.text(0) for parent in parents])


class PassUI(PyQt5.QtWidgets.QMainWindow):
    def __init__(self, passpy_obj):
        super().__init__()
        self.clicked_item = None
        self.clicked_key = None
        self.setWindowTitle("PassUI")
        self.passpy_obj = passpy_obj
        self.ui = PyQt5.uic.loadUi(os.path.join(os.path.dirname(__file__), "data", "PassUI.ui"), self)
        self.ui.treeWidget.dragMoveEvent = types.MethodType(PassUI.dragMoveEvent, self)
        self.ui.treeWidget.dropEvent = types.MethodType(PassUI.dropEvent, self)
        self.setWindowTitle("PassUI")
        self.edit_table = False
        self.in_dupplicate = False
        self.ui.PYPASS_GPG_BIN.setText(passpy_obj.PYPASS_GPG_BIN)
        self.ui.PYPASS_GIT_BIN.setText(passpy_obj.PYPASS_GIT_BIN)
        self.ui.PYPASS_STORE_DIR.setText(passpy_obj.PYPASS_STORE_DIR)
        self.ui.GIT_DIR.setText(passpy_obj.git_folder_name)
        self.ui.WEBBROWER_PATH.setText(passpy_obj.WEBBROWER_PATH)
        self.load_tree()
        self.events()
        self.show()

    def events(self):
        self.event_tree()
        self.event_table()
        self.event_settings()

    def event_tree(self):
        self.ui.treeWidget.itemChanged.connect(self.on_item_tree_changed)
        self.ui.treeWidget.itemClicked.connect(self.on_item_tree_clicked)
        self.ui.treeWidget.itemExpanded.connect(self.on_item_tree_extend)
        self.ui.treeWidget.itemCollapsed.connect(self.on_item_tree_extend)
        self.ui.treeWidget.setContextMenuPolicy(PyQt5.QtCore.Qt.CustomContextMenu)
        self.ui.treeWidget.customContextMenuRequested.connect(self.context_menu_tree)

    def event_table(self):
        self.ui.tableWidget.cellChanged.connect(self.on_item_table_changed)
        self.ui.tableWidget.cellClicked.connect(self.on_item_table_clicked)
        self.ui.tableWidget.setContextMenuPolicy(PyQt5.QtCore.Qt.CustomContextMenu)
        self.ui.tableWidget.customContextMenuRequested.connect(self.context_menu_table)

    def event_settings(self):
        self.ui.PYPASS_GPG_BIN.editingFinished.connect(self.edit_settings)
        self.ui.PYPASS_GIT_BIN.editingFinished.connect(self.edit_settings)
        self.ui.PYPASS_STORE_DIR.editingFinished.connect(self.edit_settings)
        self.ui.GIT_DIR.editingFinished.connect(self.edit_settings)
        self.ui.WEBBROWER_PATH.editingFinished.connect(self.edit_settings)

    def edit_settings(self):
        self.passpy_obj.PYPASS_GPG_BIN = self.ui.PYPASS_GPG_BIN.text()
        self.passpy_obj.PYPASS_GIT_BIN = self.ui.PYPASS_GIT_BIN.text()
        self.passpy_obj.PYPASS_STORE_DIR = self.ui.PYPASS_STORE_DIR.text()
        self.passpy_obj.git_folder_name = self.ui.GIT_DIR.text()
        self.passpy_obj.WEBBROWER_PATH = self.ui.WEBBROWER_PATH.text()
        if self.passpy_obj.overwrite_config():
            PyQt5.QtCore.QCoreApplication.quit()
            PyQt5.QtCore.QProcess.startDetached(sys.executable, sys.argv)

    @PyQt5.QtCore.pyqtSlot(PyQt5.QtWidgets.QTreeWidgetItem, int)
    def on_item_tree_changed(self, item, _):
        if self.in_dupplicate:
            return
        path = self.get_abs_path(item)
        if self.clicked_key is None:
            return
        initial_path = os.path.join(os.sep.join(path.split(os.sep)[:-1]), self.clicked_key + ".gpg")
        if not os.path.isfile(initial_path):
            path = self.get_abs_path(item, folder=True)
            initial_path = os.path.join(os.sep.join(path.split(os.sep)[:-1]), self.clicked_key)
        os.rename(initial_path, path)
        self.resize_tree()

    def context_menu_tree(self, position):
        item = self.ui.treeWidget.itemAt(position)
        if item is None:
            return self.add_context([
                # ["Export all to CSV", self.action_export_csv_all],
                # ["GIT PULL", self.action_git_pull],
                # ["GIT PUSH", self.action_git_push],
                ["Add folder", self.action_add_folder_top],
            ], self.treeWidget, position)
        if os.path.isfile(self.get_abs_path(item)):
            return self.add_context([
                ["Delete", self.action_remove],
                ["Copy infos", self.action_copy_clipboard],
                ["Dupplicate file", self.action_dupplicate],
            ], item, position)
        else:
            return self.add_context([
                ["Add folder", self.action_add_folder],
                ["Delete", self.action_remove_folder],
                ["Add password", self.action_copy_clipboard],
                # ["Export to CSV", self.action_export_csv],
            ], item, position)

    def context_menu_table(self, position):
        index = self.ui.tableWidget.indexAt(position)
        menu = PyQt5.QtWidgets.QMenu(self)
        actions = []
        if not index.isValid():
            return
        actions_bind = [
            ["Remove field", self.action_remove_field],
            ["Add field", self.action_add_field],
        ]
        for action, func in actions_bind:
            actions.append(menu.addAction(action))
        action = menu.exec_(self.ui.tableWidget.viewport().mapToGlobal(position))
        for i, action_check in enumerate(actions):
            if action == action_check:
                actions_bind[i][1](index)

    def action_remove_field(self, _):
        rows = []
        items = self.ui.tableWidget.selectedItems()
        for item in items:
            row = item.row()
            if row not in rows:
                rows.append(row)
        if len(rows) == 1:
            row = rows[0]
            variable = self.ui.tableWidget.item(row, 0).text()
            value = self.ui.tableWidget.item(row, 1).text()
            self.confirm(
                lambda: self.remove_field(row),
                f"Delete field '{variable}' with value '{value}' ?"
            )
        else:
            rows.sort()
            rows.reverse()
            self.confirm(
                lambda: self.remove_fields(rows),
                f"Delete {len(rows)} fields ?"
            )

    def remove_fields(self, rows):
        item = self.clicked_item
        path = os.path.join(get_rel_path(item), item.text(0))
        infos = self.passpy_obj.get_infos(path)
        for row in rows:
            del infos[self.ui.tableWidget.item(row, 0).text()]
            self.ui.tableWidget.removeRow(row)
        self.passpy_obj.write_key(path, infos)

    def remove_field(self, row):
        item = self.clicked_item
        path = os.path.join(get_rel_path(item), item.text(0))
        infos = self.passpy_obj.get_infos(path)
        del infos[self.ui.tableWidget.item(row, 0).text()]
        self.ui.tableWidget.removeRow(row)
        self.passpy_obj.write_key(path, infos)

    def action_add_field(self, index):
        row = index.row()
        item = self.clicked_item
        path = os.path.join(get_rel_path(item), item.text(0))
        infos = self.passpy_obj.get_infos(path)
        res = {}
        for i, key in enumerate(infos):
            if i == row:
                keyadd = "field"
                j = 0
                while keyadd in infos:
                    j += 1
                    keyadd = f"field_{j}"
                res[keyadd] = ""
                self.ui.tableWidget.insertRow(row + 1)
                self.ui.tableWidget.setItem(row + 1, 0, PyQt5.QtWidgets.QTableWidgetItem(keyadd))
                self.ui.tableWidget.setItem(row + 1, 1, PyQt5.QtWidgets.QTableWidgetItem(res[keyadd]))
            res[key] = infos[key]
        self.passpy_obj.write_key(path, res)

    def add_context(self, actions_bind, item, position):
        menu = PyQt5.QtWidgets.QMenu(self)
        actions = []
        for action, func in actions_bind:
            actions.append(menu.addAction(action))
        action = menu.exec_(self.ui.treeWidget.viewport().mapToGlobal(position))
        for i, action_check in enumerate(actions):
            if action == action_check:
                actions_bind[i][1](item)

    def action_add_folder(self, item):
        self.in_dupplicate = True
        key = "new_folder"
        path = os.path.join(self.get_abs_path(item, folder=True), key)
        i = 0
        while os.path.isdir(path):
            i += 1
            key = f"new_folder_{i}"
            path = os.path.join(self.get_abs_path(item, folder=True), key)
        os.mkdir(path)
        child = PyQt5.QtWidgets.QTreeWidgetItem()
        child.setText(0, key)
        parent = item.parent()
        if parent is None:
            index = self.ui.treeWidget.indexOfTopLevelItem(item)
            parent = self.ui.treeWidget.topLevelItem(index)
        else:
            parent = item
        parent.addChild(child)
        child.setFlags(child.flags() | PyQt5.QtCore.Qt.ItemIsEditable)
        self.resize_tree()
        self.in_dupplicate = False

    def action_add_folder_top(self, _):
        self.in_dupplicate = True
        key = "new_folder"
        path = os.path.join(self.passpy_obj.PYPASS_STORE_DIR, key)
        i = 0
        while os.path.isdir(path):
            i += 1
            key = f"new_folder_{i}"
            path = os.path.join(self.passpy_obj.PYPASS_STORE_DIR, key)
        os.mkdir(path)
        child = PyQt5.QtWidgets.QTreeWidgetItem()
        child.setText(0, key)
        self.ui.treeWidget.invisibleRootItem().addChild(child)
        child.setFlags(child.flags() | PyQt5.QtCore.Qt.ItemIsEditable)
        self.resize_tree()
        self.in_dupplicate = False

    def action_export_csv_all(self, item):
        raise NotImplementedError

    def action_git_pull(self, item):
        raise NotImplementedError

    def action_git_push(self, item):
        raise NotImplementedError

    def action_remove_folder(self, item):
        path = get_rel_path(item)
        if not path:
            path = self.passpy_obj.PYPASS_STORE_DIR
        self.confirm(
            lambda: self.remove_folder(item),
            f"Delete folder '{item.text(0)}' in '{path}' ?"
        )

    def remove_folder(self, item):
        path_to_remove = self.get_abs_path(item, folder=True)
        shutil.rmtree(path_to_remove)
        parent = item.parent()
        if parent is None:
            index = self.ui.treeWidget.indexOfTopLevelItem(item)
            self.ui.treeWidget.takeTopLevelItem(index)
        else:
            parent.removeChild(item)

    def action_export_csv(self, item):
        raise NotImplementedError

    def action_remove(self, item):
        self.confirm(
            lambda: self.remove_password(item),
            f"Delete file '{item.text(0)}.gpg' in '{get_rel_path(item)}'"
        )

    def action_copy_clipboard(self, item):
        pyperclip.copy("\n".join([f"{key}: {value}" for key, value in self.passpy_obj.get_infos(
            os.path.join(get_rel_path(item), item.text(0))).items()]))

    def action_dupplicate(self, item):
        path = self.get_abs_path(item)
        last = path[:-len(".gpg")].split("_")[-1]
        if last.isdigit():
            i = int(last)
            is_copied = True
        else:
            i = 1
            is_copied = False
        while True:
            if is_copied:
                key = "_".join(item.text(0).split("_")[:-1]) + f"_{i}"
            else:
                key = item.text(0) + f"_{i}"
            path_dest = os.path.join(os.sep.join(path.split(os.sep)[:-1]), key + ".gpg")
            if not (os.path.isdir(path_dest) or os.path.isfile(path_dest)):
                break
            i += 1
        shutil.copy(path, path_dest)
        self.in_dupplicate = True
        child = PyQt5.QtWidgets.QTreeWidgetItem([key], 0)
        item.parent().addChild(child)
        self.clicked_key = key
        self.resize_tree()
        child.setFlags(child.flags() | PyQt5.QtCore.Qt.ItemIsEditable)
        self.in_dupplicate = False

    def confirm(self, func, txt):
        if PyQt5.QtWidgets.QMessageBox.question(
                self, '', txt + " ?",
                PyQt5.QtWidgets.QMessageBox.Yes | PyQt5.QtWidgets.QMessageBox.No
        ) == PyQt5.QtWidgets.QMessageBox.Yes:
            return func()

    def remove_password(self, item):
        path_to_remove = self.get_abs_path(item)
        os.remove(path_to_remove)
        item.parent().removeChild(item)

    def get_abs_path(self, item, folder=False):
        if item is None and folder:
            return self.passpy_obj.PYPASS_STORE_DIR
        return os.path.join(self.passpy_obj.PYPASS_STORE_DIR, get_rel_path(item), item.text(0)) + (
                ".gpg" * (not folder))

    def on_item_table_clicked(self, row, col):
        value = self.ui.tableWidget.item(row, 1).text()
        if col == 0:
            pyperclip.copy(value)
        elif col == 1:
            info_key = self.ui.tableWidget.item(row, 0).text()
            if info_key == "url" and validators.url(value):
                try:
                    webbrowser_user = webbrowser.get(self.passpy_obj.WEBBROWER_PATH)
                except webbrowser.Error:
                    print(f"Fail to open with {self.passpy_obj.WEBBROWER_PATH}")
                    webbrowser_user = webbrowser.get(None)
                webbrowser_user.open(value)

    def on_item_tree_extend(self):
        self.ui.tableWidget.setRowCount(0)
        self.resize_tree()

    def resize_tree(self):
        self.ui.treeWidget.invisibleRootItem().setExpanded(True)
        self.ui.treeWidget.resizeColumnToContents(0)
        self.ui.treeWidget.invisibleRootItem().setExpanded(False)

    def load_tree(self):
        self.ui.treeWidget.clear()
        self.fill_item(self.ui.treeWidget.invisibleRootItem(), self.passpy_obj.keys)

    def fill_item(self, item, value):
        for key, val in sorted(value.items()):
            child = PyQt5.QtWidgets.QTreeWidgetItem()
            child.setText(0, key)
            item.addChild(child)
            if type(val) is dict:
                self.fill_item(child, val)
            child.setFlags(child.flags() | PyQt5.QtCore.Qt.ItemIsEditable)
        self.resize_tree()

    @PyQt5.QtCore.pyqtSlot(PyQt5.QtWidgets.QTreeWidgetItem, int)
    def on_item_tree_clicked(self, item, _):
        key = item.text(0)
        self.clicked_item = item
        self.clicked_key = key
        if os.path.isfile(self.get_abs_path(item)):
            parents = [key]
            current_it = item
            while True:
                parent = current_it.parent()
                if not isinstance(parent, PyQt5.QtWidgets.QTreeWidgetItem):
                    break
                parent_key = parent.text(0)
                parents.append(parent_key)
                current_it = parent
            parents.reverse()
            infos = self.passpy_obj.get_infos(os.sep.join(parents))
            if "PASSWORD" in infos:
                pyperclip.copy(infos["PASSWORD"])
            self.fill_table(infos)

    def on_item_table_changed(self):
        if self.edit_table:
            return
        res = {}
        for row in range(self.ui.tableWidget.rowCount()):
            key = self.ui.tableWidget.item(row, 0).text()
            value = self.ui.tableWidget.item(row, 1).text()
            i = 0
            while key in res:
                i += 1
                split = key.split('_')
                last = split[-1]
                if last.isdigit():
                    key = '_'.join(split[:-1])
                key = f"{key}_{i}"
            if i > 0:
                self.ui.tableWidget.setItem(row, 0, PyQt5.QtWidgets.QTableWidgetItem(key))
            res[key] = value
        item = self.clicked_item
        path = os.path.join(get_rel_path(item), item.text(0))
        self.passpy_obj.write_key(path, res)

    def fill_table(self, infos):
        self.edit_table = True
        self.ui.tableWidget.setRowCount(0)
        [self.ui.tableWidget.insertRow(0) for _ in range(len(infos))]
        for line, info_key in enumerate(infos):
            value = infos[info_key]
            self.ui.tableWidget.setItem(line, 0, PyQt5.QtWidgets.QTableWidgetItem(info_key))
            self.ui.tableWidget.setItem(line, 1, PyQt5.QtWidgets.QTableWidgetItem(value))
        self.edit_table = False
        header = self.ui.tableWidget.horizontalHeader()
        header.setSectionResizeMode(PyQt5.QtWidgets.QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, PyQt5.QtWidgets.QHeaderView.Stretch)

    def dragMoveEvent(self, event):
        """
        Validation during drap n drop action of possible drag action
        :param self:
        :param event:
        :return:
        """
        position = event.pos()
        item_at_position = self.ui.treeWidget.itemAt(position)
        if item_at_position is None:
            return event.accept()
        current_item = self.ui.treeWidget.currentItem()
        if current_item is None:
            return event.ignore()
        parent_current = current_item.parent()
        path_dir_dest = self.get_abs_path(item_at_position, folder=True)
        if item_at_position == parent_current:
            return event.ignore()
        elif os.path.isdir(path_dir_dest):
            return event.accept()
        else:
            return event.ignore()

    def dropEvent(self, event: QtGui.QDropEvent):
        self.in_dupplicate = True
        position = event.pos()
        item_at_position = self.ui.treeWidget.itemAt(position)
        abs_path_dir_dest = self.get_abs_path(item_at_position, folder=True)
        actual_item = self.ui.treeWidget.currentItem()
        actual_item_text = actual_item.text(0)
        abs_path_dest = os.path.join(abs_path_dir_dest, actual_item_text + ".gpg")
        abs_path_source = self.get_abs_path(actual_item, folder=False)

        i = 0
        while os.path.isfile(abs_path_dest):
            i += 1
            split = abs_path_dest.split("_")
            key = f"_{i}.gpg"
            if len(split) == 1:
                abs_path_dest = abs_path_dest[:-len(".gpg")] + key
                continue
            abs_path_dest = "_".join(split[:-1]) + key
        os.rename(abs_path_source, abs_path_dest)
        if i > 0:
            actual_item.setText(0, os.path.basename(abs_path_dest)[:-len(".gpg")])
        parent_item = actual_item.parent()

        if parent_item is not None:
            parent_item.removeChild(actual_item)
        else:
            self.ui.treeWidget.takeTopLevelItem(self.ui.treeWidget.indexOfTopLevelItem(actual_item))

        if item_at_position is None:
            item_at_position = self.ui.treeWidget.invisibleRootItem()

        item_at_position.addChild(actual_item)
        event.setDropAction(Qt.IgnoreAction)
        event.accept()
        self.in_dupplicate = False
