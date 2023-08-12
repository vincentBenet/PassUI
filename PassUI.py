import shutil

from PyQt5 import QtWidgets, uic, QtCore, QtGui
import os
import sys
import yaml
import pyperclip
from pathlib import Path
import passpy
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QTreeWidgetItem, QTableWidgetItem, QMenu, QAction, QTreeWidget, QAbstractItemView, \
    QTableWidget, QVBoxLayout, QMessageBox
from pyqtgraph import TreeWidget


class PassUI(QtWidgets.QMainWindow):
    def __init__(self, passpy_obj):
        super().__init__()
        self.passpy_obj = passpy_obj
        self.ui = uic.loadUi(os.path.join(os.path.dirname(__file__), "PassUI.ui"), self)
        self.edit_table = False
        self.load_tree()
        self.events()
        self.show()

    def events(self):
        self.event_tree()
        self.event_table()

    def event_tree(self):
        self.ui.treeWidget.itemClicked.connect(self.on_item_tree_clicked)
        self.ui.treeWidget.itemExpanded.connect(self.on_item_tree_extend)
        self.ui.treeWidget.itemCollapsed.connect(self.on_item_tree_extend)

        self.ui.treeWidget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.ui.treeWidget.customContextMenuRequested.connect(self.context_menu_tree)

    def event_table(self):
        self.ui.tableWidget.cellChanged.connect(self.on_item_table_changed)
        self.ui.tableWidget.cellClicked.connect(self.on_item_table_clicked)

    def context_menu_tree(self, position):
        item = self.treeWidget.itemAt(position)
        if item.childCount() == 0:
            self.context_menu_tree_file(item, position)
        else:
            self.context_menu_tree_folder(item, position)

    def context_menu_tree_folder(self, item, position):
        print("context_menu_tree_folder")

    def context_menu_tree_file(self, item, position):
        menu = QMenu(self)
        actions = []
        actions_bind = [
            ["Remove", self.action_remove],
            ["Copy to clipboard", self.action_copy_clipboard],
            ["Dupplicate", self.action_dupplicate],
        ]
        for action, func in actions_bind:
            actions.append(menu.addAction(action))
        action = menu.exec_(self.ui.treeWidget.viewport().mapToGlobal(position))
        for i, action_check in enumerate(actions):
            if action == action_check:
                actions_bind[i][1](item)
        else:
            print("Forgive")

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
                path_dest = "_".join(path[:-len(".gpg")].split("_")[:-1]) + f"_{i}.gpg"
            else:
                path_dest = path[:-len(".gpg")] + f"_{i}.gpg"
            if not (os.path.isdir(path_dest) or os.path.isfile(path_dest)):
                break
            i += 1
        shutil.copy(path, path_dest)
        if is_copied:
            item.parent().addChild(QTreeWidgetItem(["_".join(item.text(0).split("_")[:-1]) + f"_{i}"], 0))
        else:
            item.parent().addChild(QTreeWidgetItem([item.text(0) + f"_{i}"], 0))
        self.resize_tree()

    def confirm(self, func, txt):
        if QMessageBox.question(self, '', txt + " ?", QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
            return func()

    def remove_password(self, item):
        path_to_remove = self.get_abs_path(item)
        print(f"Remove password {path_to_remove}")
        os.remove(path_to_remove)
        item.parent().removeChild(item)

    def get_abs_path(self, item):
        return os.path.join(self.passpy_obj.PYPASS_STORE_DIR, self.get_rel_path(item), item.text(0)) + ".gpg"

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

    @QtCore.pyqtSlot(QtWidgets.QTreeWidgetItem, int)
    def on_item_tree_clicked(self, it, col):
        key = it.text(0)
        if not it.childCount():
            parents = [key]
            current_it = it
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
        key = self.passwidget.item(row, 0).text()
        value = self.passwidget.item(row, 1).text()
        print(f"{key}: {value}")

    def fill_table(self, key, infos):
        self.edit_table = True
        self.ui.tableWidget.setRowCount(0)
        [self.ui.tableWidget.insertRow(0) for _ in range(len(infos)+1)]
        self.ui.tableWidget.setItem(0, 0, QTableWidgetItem("FILE"))
        self.ui.tableWidget.setItem(0, 1, QTableWidgetItem(key))
        for line, info_key in enumerate(infos):
            value = infos[info_key]
            self.ui.tableWidget.setItem(line+1, 0, QTableWidgetItem(info_key))
            self.ui.tableWidget.setItem(line+1, 1, QTableWidgetItem(value))
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
        self.GIT_DIR = os.path.join(self.PYPASS_STORE_DIR, self.config['settings']['git_folder_name'])
        super().__init__(
            gpg_bin=self.PYPASS_GPG_BIN, 
            git_bin=self.PYPASS_GIT_BIN, 
            store_dir=self.PYPASS_STORE_DIR, 
            use_agent=True, 
            interactive=False, 
            verbose=False
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


if __name__ == "__main__":
    Passpy_obj = PassPy()
    app = QtWidgets.QApplication(sys.argv)  # Create an instance of QtWidgets.QApplication
    window = PassUI(Passpy_obj)  # Create an instance of our class
    app.exec_()  # Start the application
