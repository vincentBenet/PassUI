import datetime
import os
import sys
import types
import shutil
from tkinter import filedialog, simpledialog
import pyperclip
import PyQt5
import PyQt5.uic
import PyQt5.QtCore
import PyQt5.QtWidgets
from PyQt5 import Qt, QtGui
from PyQt5.QtCore import Qt
from PassUI import utils

"""BUGS"""
# TODO: import key trust level to 5
# TODO: Create key expire set to never

"""TODO"""
# TODO: ALL: Dynamic hide/show tabs

# TODO: passwords: Export CSV folders selected
# TODO: passwords: Import CSV
# TODO: passwords: Edit name mode when new password / new folder created

# TODO: git: commandes: init, remote, add, commit, push, pull
# TODO: git: tableau des logs
# TODO: git: tableau des diff
# TODO: git: editLine remote URL
# TODO: git: bouton push
# TODO: git: bouton pull
# TODO: git: bouton commit
# TODO: git: bouton clone

# TODO: gpg: encrypt/decrypt file/folder

"""Features"""
# TODO: Import windows wifi passwords
# TODO: Import windows chrome passwords
# TODO: Import windows edges passwords
# TODO: Import windows firefox passwords

# TODO: Import MAC chrome passwords
# TODO: Import MAC safari passwords
# TODO: Import MAC wifi passwords


def get_rel_path(item, file=False):
    if file:
        return os.path.join(get_rel_path(item), item.text(0) + ".gpg")
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
        self.load_tree()
        self.load_keys()
        self.load_config()
        self.events()
        self.show()

    def load_config(self):
        self.ui.table_settings.setRowCount(0)
        i = 0
        for section, config_section in self.passpy_obj.config.items():
            for setting, value in config_section.items():
                self.ui.table_settings.insertRow(i)
                self.ui.table_settings.setItem(i, 0, PyQt5.QtWidgets.QTableWidgetItem(section))
                self.ui.table_settings.setItem(i, 1, PyQt5.QtWidgets.QTableWidgetItem(setting))
                self.ui.table_settings.setItem(i, 2, PyQt5.QtWidgets.QTableWidgetItem(str(value)))
        self.ui.table_settings.horizontalHeader().setSectionResizeMode(PyQt5.QtWidgets.QHeaderView.ResizeToContents)

    def load_keys(self):
        self.ui.gpg_keys_table.setRowCount(0)
        keys = self.passpy_obj.list_keys()
        nb_columns = self.ui.gpg_keys_table.columnCount()
        for i, key in enumerate(keys):
            self.ui.gpg_keys_table.insertRow(i)
            self.ui.gpg_keys_table.setItem(i, 0, PyQt5.QtWidgets.QTableWidgetItem(key["mail"]))
            self.ui.gpg_keys_table.setItem(i, 1, PyQt5.QtWidgets.QTableWidgetItem(key["user"]))
            self.ui.gpg_keys_table.setItem(i, 2, PyQt5.QtWidgets.QTableWidgetItem(key["key"]))
            self.ui.gpg_keys_table.setItem(i, 3, PyQt5.QtWidgets.QTableWidgetItem(key["expire"]))
            self.ui.gpg_keys_table.setItem(i, 4, PyQt5.QtWidgets.QTableWidgetItem(key["encryption"]))
            self.ui.gpg_keys_table.setItem(i, 5, PyQt5.QtWidgets.QTableWidgetItem(key["trust"]))
            self.ui.gpg_keys_table.setItem(i, 6, PyQt5.QtWidgets.QTableWidgetItem(key["created"]))
            if key["key"] in self.passpy_obj.config["settings"]["disabled_keys"]:
                for j in range(nb_columns):
                    item = self.ui.gpg_keys_table.item(i, j)
                    f = item.font()
                    f.setStrikeOut(True)
                    item.setFont(f)
        self.ui.gpg_keys_table.horizontalHeader().setSectionResizeMode(PyQt5.QtWidgets.QHeaderView.ResizeToContents)

    def events(self):
        self.event_tree()
        self.event_table()
        self.event_table_keys()
        self.event_table_settings()
        self.ui.button_encrypt_file.clicked.connect(self.encrypt_file)
        self.ui.button_encrypt_directory.clicked.connect(self.encrypt_directory)
        self.ui.button_decrypt_file.clicked.connect(self.decrypt_file)
        self.ui.button_decrypt_directory.clicked.connect(self.decrypt_directory)

    def encrypt_file(self):
        path_abs = filedialog.askopenfilename(
            initialdir=self.passpy_obj.path_store,
            title="Select file to encrypt",
            filetypes=[("Any file type", "*.*")]
        )
        self.confirm(
            lambda: self.passpy_obj.encrypt_file(path_abs, replace=True),
            f"Encrypt File {os.path.basename(path_abs)} at {os.path.dirname(path_abs)}"
        )

    def encrypt_directory(self):
        path_abs = filedialog.askdirectory(
            initialdir=self.passpy_obj.path_store,
            title="Select directory to encrypt",
        )
        self.confirm(
            lambda: self.passpy_obj.encrypt_directory(path_abs, replace=True),
            f"Encrypt Directory {os.path.basename(path_abs)} in {os.path.dirname(path_abs)}"
        )

    def decrypt_file(self):
        self.passpy_obj.decrypt_file(
            filedialog.askopenfilename(
                initialdir=self.passpy_obj.path_store,
                title="Select file to decrypt",
                filetypes=[("Binary GPG file", "*.bgpg")]
            ),
            replace=True
        )

    def decrypt_directory(self):
        self.passpy_obj.decrypt_directory(
            filedialog.askdirectory(
                initialdir=self.passpy_obj.path_store,
                title="Select directory to decrypt",
            ),
            replace=True
        )

    def event_table_settings(self):
        self.ui.table_settings.setContextMenuPolicy(PyQt5.QtCore.Qt.CustomContextMenu)
        self.ui.table_settings.customContextMenuRequested.connect(self.context_menu_table_settings)

    def event_table_keys(self):
        self.ui.gpg_keys_table.setContextMenuPolicy(PyQt5.QtCore.Qt.CustomContextMenu)
        self.ui.gpg_keys_table.customContextMenuRequested.connect(self.context_menu_table_keys)

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

    def change_path_store(self, _):
        if self.passpy_obj.change_path_store(
            filedialog.askdirectory(
                initialdir=self.passpy_obj.path_store,
                title="Select Store directory",
            )
        ):
            self.restart_app()

    def restart_app(self):
        PyQt5.QtCore.QCoreApplication.quit()
        PyQt5.QtCore.QProcess.startDetached(sys.executable, sys.argv)

    def edit_settings(self):
        obj = self.sender()
        key = obj.objectName()
        value = obj.text()
        if not self.passpy_obj.change_config(key, value):
            return
        self.restart_app()

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
                ["Add folder", self.action_add_folder_top],
                ["Add password", self.action_add_password_top],
                ["Change Path Store", self.change_path_store],
            ], self.treeWidget, position)
        if os.path.isfile(self.get_abs_path(item)):
            return self.add_context([
                ["Delete password", self.action_remove],
                ["Copy infos", self.action_copy_clipboard],
                ["Dupplicate file", self.action_dupplicate],
                ["Ignore file", self.action_ignore_file],
            ], item, position)
        else:
            return self.add_context([
                ["Add folder", self.action_add_folder],
                ["Delete folder", self.action_remove_folder],
                ["Add password", self.action_add_password],
                ["Ignore folder", self.action_ignore_folder],
            ], item, position)

    def action_ignore_folder(self, item):
        self.passpy_obj.config["settings"]["ignored_directories"].append(os.path.join(get_rel_path(item), item.text(0)))
        utils.write_config(self.passpy_obj.config)
        parent = item.parent()
        if parent is not None:
            parent.removeChild(item)
        else:
            self.ui.treeWidget.takeTopLevelItem(self.ui.treeWidget.indexOfTopLevelItem(item))

    def action_ignore_file(self, item):
        self.ignore_file(get_rel_path(item, file=True))
        parent = item.parent()
        if parent is not None:
            parent.removeChild(item)
        else:
            self.ui.treeWidget.takeTopLevelItem(self.ui.treeWidget.indexOfTopLevelItem(item))

    def ignore_file(self, rel_path, remove=False):
        if remove:
            self.passpy_obj.config["settings"]["ignored_files"].remove(rel_path)
        else:
            self.passpy_obj.config["settings"]["ignored_files"].append(rel_path)
        utils.write_config(self.passpy_obj.config)
        self.load_config()

    def action_add_password_top(self, _):
        _, key = utils.new_incr(self.passpy_obj.path_store, "password", ".gpg")
        child = PyQt5.QtWidgets.QTreeWidgetItem()
        child.setText(0, key)
        self.ui.treeWidget.invisibleRootItem().addChild(child)
        self.add_password_file(key)

    def action_add_password(self, item):
        self.in_dupplicate = True
        path, key = utils.new_incr(self.get_abs_path(item, folder=True), "password", ".gpg")
        self.add_password_file(utils.abs_to_rel(self.passpy_obj.path_store, path))
        child = PyQt5.QtWidgets.QTreeWidgetItem()
        child.setText(0, key)
        parent = item
        parent.addChild(child)
        child.setFlags(child.flags() | PyQt5.QtCore.Qt.ItemIsEditable)
        self.resize_tree()
        self.in_dupplicate = False

    def add_password_file(self, rel_path):
        self.passpy_obj.write_key(
            rel_path,
            {
                "PASSWORD": "",
                "url": "",
                "user": "",
                "mail": "",
                "date": datetime.datetime.now().strftime('%a %d %b %Y, %I:%M%p')
            }
        )

    def context_menu_table_settings(self, position):
        index = self.ui.gpg_keys_table.indexAt(position)
        menu = PyQt5.QtWidgets.QMenu(self)
        actions = []
        if not index.isValid():
            actions_bind = [
                ["Reset all settings", self.action_reset_all_settings],
            ]
        else:
            actions_bind = [
                ["Reset selected settings", self.action_import_key],
            ]
        for action, func in actions_bind:
            actions.append(menu.addAction(action))
        action = menu.exec_(self.ui.gpg_keys_table.viewport().mapToGlobal(position))
        for i, action_check in enumerate(actions):
            if action == action_check:
                actions_bind[i][1](index)

    def action_reset_all_settings(self, _):
        os.remove(utils.get_config_path())
        self.restart_app()

    def context_menu_table_keys(self, position):
        index = self.ui.gpg_keys_table.indexAt(position)
        menu = PyQt5.QtWidgets.QMenu(self)
        actions = []
        if not index.isValid():
            actions_bind = [
                ["Import", self.action_import_key],
                ["Create", self.action_create_key],
            ]
        else:
            actions_bind = [
                ["Export", self.action_export_key],
                ["Delete", self.action_remove_key],
            ]
            enabled = []
            disabled = []
            items = self.ui.gpg_keys_table.selectedItems()
            for item in items:
                key = self.ui.gpg_keys_table.item(item.row(), 2).text()
                if key in self.passpy_obj.config["settings"]["disabled_keys"]:
                    disabled.append(key)
                else:
                    enabled.append(key)
            if enabled:
                actions_bind.append(["Disable", self.action_disable_key])
            if disabled:
                actions_bind.append(["Enable", self.action_enable_key])
        for action, func in actions_bind:
            actions.append(menu.addAction(action))
        action = menu.exec_(self.ui.gpg_keys_table.viewport().mapToGlobal(position))
        for i, action_check in enumerate(actions):
            if action == action_check:
                actions_bind[i][1](index)

    def action_disable_key(self, _):
        items = self.ui.gpg_keys_table.selectedItems()
        for item in items:
            key = self.ui.gpg_keys_table.item(item.row(), 2).text()
            if key not in self.passpy_obj.config["settings"]["disabled_keys"]:
                self.passpy_obj.config["settings"]["disabled_keys"].append(key)
        utils.write_config(self.passpy_obj.config)
        self.load_keys()
        self.load_config()

    def action_enable_key(self, _):
        items = self.ui.gpg_keys_table.selectedItems()
        for item in items:
            key = self.ui.gpg_keys_table.item(item.row(), 2).text()
            if key in self.passpy_obj.config["settings"]["disabled_keys"]:
                self.passpy_obj.config["settings"]["disabled_keys"].remove(key)
        utils.write_config(self.passpy_obj.config)
        self.load_keys()
        self.load_config()

    def context_menu_table(self, position):
        index = self.ui.tableWidget.indexAt(position)
        menu = PyQt5.QtWidgets.QMenu(self)
        actions = []
        if not index.isValid():
            return
        actions_bind = [
            ["Remove", self.action_remove_field],
            ["Add", self.action_add_field],
        ]
        for action, func in actions_bind:
            actions.append(menu.addAction(action))
        action = menu.exec_(self.ui.tableWidget.viewport().mapToGlobal(position))
        for i, action_check in enumerate(actions):
            if action == action_check:
                actions_bind[i][1](index)

    def action_remove_key(self, _):
        sep = "\n\t- "
        self.confirm(
            lambda: self.remove_key(),
            f"Delete keys {sep}{sep.join([self.ui.gpg_keys_table.item(item.row(), 0).text() for item in self.ui.gpg_keys_table.selectedItems()])}"
        )

    def remove_key(self):
        keys = []
        items = self.ui.gpg_keys_table.selectedItems()
        for item in items:
            keys.append(self.ui.gpg_keys_table.item(item.row(), 2).text())
        self.passpy_obj.remove_key(keys=keys)
        self.load_keys()

    def action_export_key(self, _):
        items = self.ui.gpg_keys_table.selectedItems()
        for item in items:
            key = self.ui.gpg_keys_table.item(item.row(), 2).text()
            filename = f"private_{key}.gpg"
            path = os.path.join(self.passpy_obj.path_store, filename)
            self.passpy_obj.export_key(path, key)
            self.passpy_obj.ignore_file(filename)

    def action_import_key(self, _):
        path_abs_gpg = filedialog.askopenfilename(
            initialdir=self.passpy_obj.path_store,
            title="Select a private key",
            filetypes=[("GPG private key", "*.*")]
        )
        self.passpy_obj.import_key(path_abs_gpg)
        self.load_keys()

    def action_create_key(self, _):
        self.passpy_obj.create_key(
            simpledialog.askstring(title="Key name", prompt="Enter your name:"),
            simpledialog.askstring(title="Key mail", prompt="Enter your mail:"),
            simpledialog.askstring(title="Key passphrase", prompt="Enter your passphrase:", show='*'),
        )
        self.load_keys()

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
        infos = self.passpy_obj.read_key(path)
        for row in rows:
            del infos[self.ui.tableWidget.item(row, 0).text()]
            self.ui.tableWidget.removeRow(row)
        self.passpy_obj.write_key(path, infos)

    def remove_field(self, row):
        item = self.clicked_item
        path = os.path.join(get_rel_path(item), item.text(0))
        infos = self.passpy_obj.read_key(path)
        del infos[self.ui.tableWidget.item(row, 0).text()]
        self.ui.tableWidget.removeRow(row)
        self.passpy_obj.write_key(path, infos)

    def action_add_field(self, index):
        self.edit_table = True
        row = index.row()
        item = self.clicked_item
        path = os.path.join(get_rel_path(item), item.text(0))
        infos = self.passpy_obj.read_key(path)
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
        self.edit_table = False

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
        path, key = utils.new_incr(self.get_abs_path(item, folder=True), "folder")
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
        path, key = utils.new_incr(self.passpy_obj.path_store, "folder")
        os.mkdir(path)
        child = PyQt5.QtWidgets.QTreeWidgetItem()
        child.setText(0, key)
        self.ui.treeWidget.invisibleRootItem().addChild(child)
        child.setFlags(child.flags() | PyQt5.QtCore.Qt.ItemIsEditable)
        self.resize_tree()
        self.in_dupplicate = False

    def action_export_csv_all(self, item):
        raise NotImplementedError

    def action_remove_folder(self, item):
        path = get_rel_path(item)
        if not path:
            path = self.passpy_obj.path_store
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
        pyperclip.copy("\n".join([f"{key}: {value}" for key, value in self.passpy_obj.read_key(
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
        parent = item.parent()
        if parent is not None:
            parent.removeChild(item)
        else:
            self.ui.treeWidget.takeTopLevelItem(self.ui.treeWidget.indexOfTopLevelItem(item))

    def get_abs_path(self, item, folder=False):
        if item is None and folder:
            return self.passpy_obj.path_store
        return os.path.join(self.passpy_obj.path_store, get_rel_path(item), item.text(0)) + (
                ".gpg" * (not folder))

    def on_item_table_clicked(self, row, col):
        value = self.ui.tableWidget.item(row, 1).text()
        if col == 0:
            pyperclip.copy(value)
        elif col == 1:
            info_key = self.ui.tableWidget.item(row, 0).text()

    def on_item_tree_extend(self):
        self.ui.tableWidget.setRowCount(0)
        self.resize_tree()

    def resize_tree(self):
        self.ui.treeWidget.invisibleRootItem().setExpanded(True)
        self.ui.treeWidget.resizeColumnToContents(0)
        self.ui.treeWidget.invisibleRootItem().setExpanded(False)

    def load_tree(self):
        self.ui.treeWidget.clear()
        self.fill_item(
            self.ui.treeWidget.invisibleRootItem(),
            self.passpy_obj.rel_paths_gpg
        )

    def fill_item(self, item, value):
        for key, val in value.items():  # TODO: Sort dict
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
            infos = self.passpy_obj.read_key(os.sep.join(parents))
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


class Logger:
    def __init__(self, ui: PyQt5.QtWidgets.QTextEdit):
        self.txt = ""
        self.ui = ui

    def __enter__(self):
        self.init = sys.stdout
        sys.stdout = self
        return self

    def __exit__(self, type, value, traceback):
        self.ui.setText(self.txt)
        self.ui.moveCursor(QtGui.QTextCursor.End)
        sys.stdout = self.init

    def write(self, message):
        self.txt += message
