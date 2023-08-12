# TODO: Multiple field remove
# TODO: Move password drag n drop
# TODO: git pull
# TODO: git push
# TODO: git init
# TODO: passpy init
# TODO: link git remote url


import shutil
from PyQt5 import QtWidgets, uic, QtCore
import os
import sys
import yaml
import pyperclip
from pathlib import Path
import passpy
import passpy_gpg
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QTreeWidgetItem, QTableWidgetItem, QMenu, QMessageBox


class PassUI(QtWidgets.QMainWindow):
    def __init__(self, passpy_obj):
        super().__init__()
        self.setWindowTitle("PassUI")
        self.passpy_obj = passpy_obj
        self.ui = uic.loadUi(os.path.join(os.path.dirname(__file__), "PassUI.ui"), self)
        self.setWindowTitle("PassUI")
        self.edit_table = False
        self.in_dupplicate = False
        self.ui.PYPASS_GPG_BIN.setText(passpy_obj.PYPASS_GPG_BIN)
        self.ui.PYPASS_GIT_BIN.setText(passpy_obj.PYPASS_GIT_BIN)
        self.ui.GIT_DIR.setText(passpy_obj.git_folder_name)
        self.load_tree()
        self.events()
        self.show()

    def events(self):
        self.event_tree()
        self.event_table()

    def event_tree(self):
        self.ui.treeWidget.itemChanged.connect(self.on_item_tree_changed)
        self.ui.treeWidget.itemClicked.connect(self.on_item_tree_clicked)
        self.ui.treeWidget.itemExpanded.connect(self.on_item_tree_extend)
        self.ui.treeWidget.itemCollapsed.connect(self.on_item_tree_extend)
        self.ui.treeWidget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.ui.treeWidget.customContextMenuRequested.connect(self.context_menu_tree)

    def event_table(self):
        self.ui.tableWidget.cellChanged.connect(self.on_item_table_changed)
        self.ui.tableWidget.cellClicked.connect(self.on_item_table_clicked)
        self.ui.tableWidget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.ui.tableWidget.customContextMenuRequested.connect(self.context_menu_table)

    @QtCore.pyqtSlot(QtWidgets.QTreeWidgetItem, int)
    def on_item_tree_changed(self, item, col):
        if self.in_dupplicate:
            return
        path = self.get_abs_path(item)
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
                ["Export all to CSV", self.action_export_csv_all],
                ["Change directory", self.action_change_directory],
                ["GIT PULL", self.action_git_pull],
                ["GIT PUSH", self.action_git_push],
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
                ["Export to CSV", self.action_export_csv],
            ], item, position)

    def context_menu_table(self, position):
        index = self.ui.tableWidget.indexAt(position)
        menu = QMenu(self)
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

    def action_remove_field(self, index):
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
        path = os.path.join(self.get_rel_path(item), item.text(0))
        infos = self.passpy_obj.get_infos(path)
        for row in rows:
            del infos[self.ui.tableWidget.item(row, 0).text()]
            self.ui.tableWidget.removeRow(row)
        self.passpy_obj.write_key(path, infos)

    def remove_field(self, row):
        item = self.clicked_item
        path = os.path.join(self.get_rel_path(item), item.text(0))
        infos = self.passpy_obj.get_infos(path)
        del infos[self.ui.tableWidget.item(row, 0).text()]
        self.ui.tableWidget.removeRow(row)
        self.passpy_obj.write_key(path, infos)

    def action_add_field(self, index):
        row = index.row()
        item = self.clicked_item
        path = os.path.join(self.get_rel_path(item), item.text(0))
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
                self.ui.tableWidget.setItem(row + 1, 0, QTableWidgetItem(keyadd))
                self.ui.tableWidget.setItem(row + 1, 1, QTableWidgetItem(res[keyadd]))
            res[key] = infos[key]
        self.passpy_obj.write_key(path, res)

    def add_context(self, actions_bind, item, position):
        menu = QMenu(self)
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
        child = QTreeWidgetItem()
        child.setText(0, key)
        parent = item.parent()
        if parent is None:
            index = self.ui.treeWidget.indexOfTopLevelItem(item)
            parent = self.ui.treeWidget.topLevelItem(index)
        else:
            parent = item
        parent.addChild(child)
        child.setFlags(child.flags() | Qt.ItemIsEditable)
        self.resize_tree()
        self.in_dupplicate = False

    def action_add_folder_top(self, item):
        self.in_dupplicate = True
        key = "new_folder"
        path = os.path.join(self.passpy_obj.PYPASS_STORE_DIR, key)
        i = 0
        while os.path.isdir(path):
            i += 1
            key = f"new_folder_{i}"
            path = os.path.join(self.passpy_obj.PYPASS_STORE_DIR, key)
        os.mkdir(path)
        child = QTreeWidgetItem()
        child.setText(0, key)
        self.ui.treeWidget.invisibleRootItem().addChild(child)
        child.setFlags(child.flags() | Qt.ItemIsEditable)
        self.resize_tree()
        self.in_dupplicate = False

    def action_export_csv_all(self, item):
        pass

    def action_git_pull(self, item):
        pass

    def action_git_push(self, item):
        pass

    def action_remove_folder(self, item):
        path = self.get_rel_path(item)
        if not path:
            path = self.passpy_obj.PYPASS_STORE_DIR
        self.confirm(
            lambda: self.remove_folder(item),
            f"Delete folder '{item.text(0)}' in '{path}' ?"
        )

    def remove_folder(self, item):
        path_to_remove = self.get_abs_path(item, folder=True)
        print(f"Remove folder {path_to_remove}")
        shutil.rmtree(path_to_remove)
        parent = item.parent()
        if parent is None:
            index = self.ui.treeWidget.indexOfTopLevelItem(item)
            self.ui.treeWidget.takeTopLevelItem(index)
        else:
            parent.removeChild(item)

    def action_export_csv(self, item):
        pass

    def action_change_directory(self, item):
        pass

    def action_remove(self, item):
        self.confirm(
            lambda: self.remove_password(item),
            f"Delete file '{item.text(0)}.gpg' in '{self.get_rel_path(item)}'"
        )

    def action_copy_clipboard(self, item):
        pyperclip.copy("\n".join([f"{key}: {value}" for key, value in self.passpy_obj.get_infos(
            os.path.join(self.get_rel_path(item), item.text(0))).items()]))

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
        print(f"Dupplicate {path} -> {path_dest}")
        shutil.copy(path, path_dest)
        self.in_dupplicate = True
        child = QTreeWidgetItem([key], 0)
        item.parent().addChild(child)
        self.clicked_key = key
        self.resize_tree()
        child.setFlags(child.flags() | Qt.ItemIsEditable)
        self.in_dupplicate = False

    def confirm(self, func, txt):
        if QMessageBox.question(self, '', txt + " ?", QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
            return func()

    def remove_password(self, item):
        path_to_remove = self.get_abs_path(item)
        print(f"Remove password {path_to_remove}")
        os.remove(path_to_remove)
        item.parent().removeChild(item)

    def get_abs_path(self, item, folder=False):

        return os.path.join(self.passpy_obj.PYPASS_STORE_DIR, self.get_rel_path(item), item.text(0)) + (".gpg" * (not folder))

    def get_rel_path(self, item):
        parents = []
        current = item
        while True:
            parent = current.parent()
            if parent is None:
                break
            parents.append(parent)
            current = parent
        parents.reverse()
        return os.sep.join([parent.text(0) for parent in parents])

    def on_item_table_clicked(self, row, col):
        pyperclip.copy(self.ui.tableWidget.item(row, 1).text())

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
            child = QTreeWidgetItem()
            child.setText(0, key)
            item.addChild(child)
            if type(val) is dict:
                self.fill_item(child, val)
            child.setFlags(child.flags() | Qt.ItemIsEditable)
        self.resize_tree()

    @QtCore.pyqtSlot(QtWidgets.QTreeWidgetItem, int)
    def on_item_tree_clicked(self, item, col):
        key = item.text(0)
        self.clicked_item = item
        self.clicked_key = key
        if os.path.isfile(self.get_abs_path(item)):
            parents = [key]
            current_it = item
            while True:
                parent = current_it.parent()
                if not isinstance(parent, QTreeWidgetItem):
                    break
                parent_key = parent.text(0)
                parents.append(parent_key)
                current_it = parent
            parents.reverse()
            infos = self.passpy_obj.get_infos(os.sep.join(parents))
            if "PASSWORD" in infos:
                pyperclip.copy(infos["PASSWORD"])
            self.fill_table(key, infos)

    def on_item_table_changed(self, row, col):
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
                self.ui.tableWidget.setItem(row, 0, QTableWidgetItem(key))
            res[key] = value
        item = self.clicked_item
        path = os.path.join(self.get_rel_path(item), item.text(0))
        self.passpy_obj.write_key(path, res)

    def fill_table(self, key, infos):
        self.edit_table = True
        self.ui.tableWidget.setRowCount(0)
        [self.ui.tableWidget.insertRow(0) for _ in range(len(infos))]
        for line, info_key in enumerate(infos):
            value = infos[info_key]
            self.ui.tableWidget.setItem(line, 0, QTableWidgetItem(info_key))
            self.ui.tableWidget.setItem(line, 1, QTableWidgetItem(value))
        self.edit_table = False
        header = self.ui.tableWidget.horizontalHeader()
        header.setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)


class PassPy(passpy.store.Store):
    def __init__(self):
        self.config = yaml.safe_load(Path(os.path.join(os.path.dirname(__file__), "PassUI.yml")).read_text())
        self.PYPASS_STORE_DIR = self.config['variables']['PYPASS_STORE_DIR']
        self.PYPASS_GIT_BIN = self.config['variables']['PYPASS_GIT_BIN']
        self.PYPASS_GPG_BIN = self.config['variables']['PYPASS_GPG_BIN']
        self.git_folder_name = self.config['settings']['git_folder_name']
        self.GIT_DIR = os.path.join(self.PYPASS_STORE_DIR, self.git_folder_name)
        super().__init__(
            gpg_bin=self.PYPASS_GPG_BIN, 
            git_bin=self.PYPASS_GIT_BIN, 
            store_dir=self.PYPASS_STORE_DIR, 
            use_agent=True, 
            interactive=False, 
            verbose=True
        )
        
    @property
    def keys(self):
        print(f"{self.GIT_DIR = }")
        res = {}
        for root, dirs, files in os.walk(self.PYPASS_STORE_DIR):
            condition = root.startswith(os.path.abspath(self.GIT_DIR))
            if condition:
                continue
            rel_path = root[len(self.PYPASS_STORE_DIR)+1:]
            if not len(rel_path):
                continue
            dico = res
            for key in rel_path.split(os.sep):
                if key not in dico:
                    dico[key] = {}
                dico = dico[key]
            for file in files:
                if not file.endswith(".gpg"):
                    continue
                passkey = file[:-len(".gpg")]
                key_rel_path = os.path.join(rel_path, passkey)
                dico[passkey] = key_rel_path
        print(f"{res = }")
        return res

    def get_infos(self, key_rel_path):
        dico = {}
        infos = self.get_key(key_rel_path)
        splits = infos.split("\n")
        dico["PASSWORD"] = splits[0]
        seps = [": ", ":", "| ", "|"]
        for i, info in enumerate(splits[1:]):
            if not len(info):
                continue
            for sep in seps:
                if sep in info:
                    split = info.split(sep)
                    dico[split[0]] = sep.join(split[1:])
                    break
            else:
                print(f"ERROR ON {key_rel_path}: No separator for line {i}: {info}")
        return dico

    def write_key(self, path, infos):
        key_data = ""
        if "PASSWORD" in infos:
            key_data += infos["PASSWORD"] + "\n"
        for key, value in infos.items():
            if key == "PASSWORD":
                continue
            key_data += f"{key}: {value}\n"
        print(key_data)
        passpy_gpg.write_key(
            os.path.join(self.PYPASS_STORE_DIR, path + ".gpg"),
            key_data,
            self.PYPASS_GPG_BIN,
            os.path.join(self.PYPASS_STORE_DIR, '.gpg-id')
        )


if __name__ == "__main__":
    Passpy_obj = PassPy()
    app = QtWidgets.QApplication(sys.argv)  # Create an instance of QtWidgets.QApplication
    window = PassUI(Passpy_obj)  # Create an instance of our class
    app.exec_()  # Start the application
