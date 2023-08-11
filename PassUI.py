from PyQt5 import QtWidgets, uic, QtCore
import os
import sys
import yaml
from pathlib import Path
import passpy
from PyQt5.QtWidgets import QTreeWidgetItem, QTableWidgetItem, QHeaderView


class PassUI(QtWidgets.QMainWindow):
    def __init__(self, Passpy_obj):
        super().__init__()
        self.Passpy_obj = Passpy_obj
        self.ui = uic.loadUi(os.path.join(os.path.dirname(__file__), "PassUI.ui"), self)
        widget = self.ui.treeWidget
        self.passwidget = self.ui.tableWidget
        print(type(self.passwidget))
        self.load_tree(widget)
        widget.itemClicked.connect(self.onItemClicked)
        widget.itemExpanded.connect(self.onItemExtend)
        widget.itemCollapsed.connect(self.onItemExtend)
        self.passwidget.cellChanged.connect(self.onItemChanged)
        self.show()

    def onItemExtend(self):
        self.passwidget.setRowCount(0)
        self.ui.treeWidget.invisibleRootItem().setExpanded(True)
        self.ui.treeWidget.resizeColumnToContents(0)
        self.ui.treeWidget.invisibleRootItem().setExpanded(False)
    
    def load_tree(self, widget):
        widget.clear()
        self.fill_item(widget.invisibleRootItem(), self.Passpy_obj.keys, widget)

    def fill_item(self, item, value, widget):
        for key, val in sorted(value.items()):
            child = QTreeWidgetItem()
            child.setText(0, key)
            item.addChild(child)
            if type(val) is dict:
                self.fill_item(child, val, widget)

    @QtCore.pyqtSlot(QtWidgets.QTreeWidgetItem, int)
    def onItemClicked(self, it, col):
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
            infos = self.Passpy_obj.get_infos(os.sep.join(parents))
            self.fill_table(self.passwidget, key, infos)

    def onItemChanged(self, row, col):
        if self.edit_table:
            return
        key = self.passwidget.item(row, 0).text()
        value = self.passwidget.item(row, 1).text()
        print(f"{key}: {value}")

    def fill_table(self, widget, key, infos):
        self.edit_table = True
        widget.setRowCount(0)
        [widget.insertRow(0) for _ in range(len(infos)+1)]
        widget.setItem(0, 0, QTableWidgetItem("FILE"))
        widget.setItem(0, 1, QTableWidgetItem(key))
        for line, info_key in enumerate(infos):
            value = infos[info_key]
            widget.setItem(line+1, 0, QTableWidgetItem(info_key))
            widget.setItem(line+1, 1, QTableWidgetItem(value))
        self.edit_table = False
        header = widget.horizontalHeader()
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
        for info in infos.split("\n"):
            if not len(info):
                continue
            split = info.split(": ")
            if len(split) == 1:
                dico["PASSWORD"] = info
            elif len(split) > 1:
                dico[split[0]] = ": ".join(split[1:])
        return dico


if __name__ == "__main__":
    Passpy_obj = PassPy()
    app = QtWidgets.QApplication(sys.argv)  # Create an instance of QtWidgets.QApplication
    window = PassUI(Passpy_obj)  # Create an instance of our class
    app.exec_()  # Start the application
