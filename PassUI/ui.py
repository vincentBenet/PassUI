"""ui.py - User interface module for PassUI

This module provides the user interface for the PassUI password manager application.
It handles the GUI using PyQt5.
"""

import datetime
import os
import sys
import types
import shutil
from tkinter import filedialog
import pyperclip
import yaml
from pathlib import Path
import PyQt5
import PyQt5.uic
import PyQt5.QtCore
import PyQt5.QtWidgets
from PyQt5 import Qt, QtGui
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PassUI import utils


# Thread class for background operations
class WorkerThread(QThread):
    """Worker thread for background tasks to avoid UI freezing"""
    result_signal = pyqtSignal(bool, str)

    def __init__(self, function, *args, **kwargs):
        super().__init__()
        self.function = function
        self.args = args
        self.kwargs = kwargs

    def run(self):
        try:
            result = self.function(*self.args, **self.kwargs)
            self.result_signal.emit(True, "Operation completed successfully" if result else "Operation failed")
        except Exception as e:
            self.result_signal.emit(False, str(e))


def get_rel_path(item, file=False):
    """Get the relative path for a tree item

    Args:
        item: The tree widget item
        file: Whether the item is a file or directory

    Returns:
        str: The relative path
    """
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


def get_parent_path(item):
    """Get the parent path for a tree item

    Args:
        item: Tree widget item

    Returns:
        str: Parent path, empty string if root
    """
    path_parts = []
    parent = item.parent()

    while parent is not None:
        path_parts.insert(0, parent.text(0))
        parent = parent.parent()

    return os.path.join(*path_parts) if path_parts else ""


def get_full_tree_path(item):
    """Get the full path of a tree item by traversing parents

    Args:
        item: The tree widget item

    Returns:
        str: Full path with separators
    """
    if item is None:
        return ""

    parts = [item.text(0)]
    parent = item.parent()

    while parent is not None:
        parts.insert(0, parent.text(0))
        parent = parent.parent()

    return os.sep.join(parts)


class PassUI(PyQt5.QtWidgets.QMainWindow):
    """Main UI class for PassUI password manager"""

    def __init__(self, passpy_obj):
        """Initialize the UI

        Args:
            passpy_obj: The PassStore object
        """
        super().__init__()

        # Initialize core variables first
        self.clicked_item = None
        self.clicked_key = None
        self.edit_table = False
        self.in_dupplicate = False
        self.worker_threads = []
        self.passpy_obj = passpy_obj

        try:
            self.setWindowTitle("PassUI")

            # Load UI from file
            ui_path = os.path.join(os.path.dirname(__file__), "data", "PassUI.ui")
            if not os.path.exists(ui_path):
                self.show_error("UI file not found", f"Cannot find UI file at {ui_path}")
                sys.exit(1)

            self.ui = PyQt5.uic.loadUi(ui_path, self)

            # Validate that essential UI components exist
            if not hasattr(self.ui, "treeWidget"):
                self.show_error("UI Error", "treeWidget component missing from UI file")
                sys.exit(1)

            # Setup drag and drop
            self.ui.treeWidget.dragMoveEvent = types.MethodType(PassUI.dragMoveEvent, self)
            self.ui.treeWidget.dropEvent = types.MethodType(PassUI.dropEvent, self)

            # Set up event handlers
            self.setup_events()

            # Load data with proper sequence and error handling
            self.load_config()
            self.load_keys()
            self.load_tree()

            self.show()
        except Exception as e:
            # Show the specific exception and stack trace
            import traceback
            error_message = f"{str(e)}\n\nStack trace:\n{traceback.format_exc()}"
            self.show_error("Initialization Error", error_message)

    def action_rename_item(self, item):
        """Rename a password or folder with a simpler, more robust approach

        Args:
            item: Tree widget item to rename
        """
        try:
            # Store the current item and name for reference
            self.clicked_item = item
            self.clicked_key = item.text(0)

            # Store the full path
            self.clicked_full_path = get_full_tree_path(item)

            # Get current name and path
            current_name = item.text(0)
            parent_path = get_parent_path(item)

            # Log full paths for debugging
            source_file_path = os.path.join(self.passpy_obj.path_store, parent_path, f"{current_name}.gpg")
            source_dir_path = os.path.join(self.passpy_obj.path_store, parent_path, current_name)

            print(f"Debug - Rename operation:")
            print(f"  Current name: {current_name}")
            print(f"  Parent path: {parent_path}")
            print(f"  Full path: {self.clicked_full_path}")
            print(f"  Source file path: {source_file_path} (exists: {os.path.isfile(source_file_path)})")
            print(f"  Source dir path: {source_dir_path} (exists: {os.path.isdir(source_dir_path)})")

            # Determine if item is file or folder
            is_file = os.path.isfile(source_file_path)
            is_folder = os.path.isdir(source_dir_path)

            if not is_file and not is_folder:
                self.show_error("Item Not Found",
                                f"Cannot find the item '{current_name}' in the password store.\n"
                                f"Checked file path: {source_file_path}\n"
                                f"Checked folder path: {source_dir_path}")
                return

            item_type = "password" if is_file else "folder"

            # Get new name from user
            new_name, ok = PyQt5.QtWidgets.QInputDialog.getText(
                self, f'Rename {item_type}', f'Enter new name for {current_name}:',
                text=current_name
            )

            if not ok or not new_name or new_name == current_name:
                return  # User cancelled or didn't change name

            # Build source and target paths
            source_path = source_file_path if is_file else source_dir_path
            target_path = os.path.join(self.passpy_obj.path_store, parent_path,
                                       f"{new_name}.gpg" if is_file else new_name)

            # Log target paths for debugging
            print(f"  Target path: {target_path} (exists: {os.path.exists(target_path)})")

            # Check if target already exists
            if os.path.exists(target_path):
                # If we're trying to rename to a name that already exists
                self.show_error("Cannot Rename",
                                f"A {item_type} with name '{new_name}' already exists at {os.path.dirname(target_path)}.")
                return

            # Double check source exists before attempting rename
            if not os.path.exists(source_path):
                self.show_error("Source Not Found",
                                f"Cannot find the source {item_type} at {source_path}.")
                return

            try:
                # Perform the rename with explicit error handling
                print(f"  Renaming from {source_path} to {target_path}")
                os.rename(source_path, target_path)
            except PermissionError:
                self.show_error("Permission Denied",
                                f"You don't have permission to rename this {item_type}. "
                                f"Check if the file is in use by another program.")
                return
            except FileNotFoundError:
                self.show_error("File Not Found",
                                f"The source {item_type} no longer exists at {source_path}.")
                return
            except FileExistsError:
                self.show_error("File Exists",
                                f"A {item_type} with name '{new_name}' already exists.")
                return
            except OSError as e:
                self.show_error("Operating System Error",
                                f"Failed to rename: {str(e)}")
                return

            # Update the tree item
            self.in_dupplicate = True  # Prevent triggering rename handler
            item.setText(0, new_name)
            self.in_dupplicate = False

            # Store updated values
            self.clicked_item = item
            self.clicked_key = new_name

            # Update the full path
            if self.clicked_full_path:
                parts = self.clicked_full_path.split(os.sep)
                if parts:
                    parts[-1] = new_name
                    self.clicked_full_path = os.sep.join(parts)

            # Successfully renamed
            self.show_info("Renamed", f"{item_type.capitalize()} successfully renamed to '{new_name}'")

        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            self.show_error("Error renaming item", f"{str(e)}\n\nDetails:\n{error_details}")

    def action_add_password(self, item):
        """Add a new password to a folder with simplified approach

        Args:
            item: Parent folder tree item
        """
        try:
            # Get folder path
            parent_path = get_parent_path(item)
            folder_name = item.text(0)
            folder_path = os.path.join(self.passpy_obj.path_store, parent_path, folder_name)

            # Verify it's a folder
            if not os.path.isdir(folder_path):
                self.show_error("Invalid Location", "Selected item is not a folder.")
                return

            # Get password name from user
            name, ok = PyQt5.QtWidgets.QInputDialog.getText(
                self, 'New Password', f'Enter name for new password in {folder_name}:',
                text="password"
            )

            if not ok or not name:
                return  # User cancelled or entered empty name

            # Check if password already exists
            password_path = os.path.join(folder_path, f"{name}.gpg")
            if os.path.exists(password_path):
                # Find unique name by adding number
                base_name = name
                counter = 1
                while os.path.exists(password_path):
                    name = f"{base_name}_{counter}"
                    password_path = os.path.join(folder_path, f"{name}.gpg")
                    counter += 1

                self.show_info("Name Modified",
                               f"A password named '{base_name}' already exists. Creating '{name}' instead.")

            # Create relative path for the password store
            rel_path = os.path.join(parent_path, folder_name, name) if parent_path else os.path.join(folder_name, name)

            # Create password entry
            password_data = {
                "PASSWORD": "",
                "url": "",
                "user": "",
                "mail": "",
                "date": datetime.datetime.now().strftime('%a %d %b %Y, %I:%M%p')
            }

            # Write password to store
            if not self.passpy_obj.write_key(rel_path, password_data):
                self.show_error("Error", "Failed to create password file.")
                return

            # Create tree item
            child = PyQt5.QtWidgets.QTreeWidgetItem()
            child.setText(0, name)
            child.setFlags(child.flags() | PyQt5.QtCore.Qt.ItemIsEditable)

            # Add to parent
            item.addChild(child)

            # Expand parent and select new item
            item.setExpanded(True)
            self.ui.treeWidget.setCurrentItem(child)
            self.clicked_item = child
            self.clicked_key = name

        except Exception as e:
            self.show_error("Error adding password", str(e))

    def action_add_password_top(self, _):
        """Add a new password at the root level

        Args:
            _: Unused parameter (sender)
        """
        try:
            # Get password name from user
            name, ok = PyQt5.QtWidgets.QInputDialog.getText(
                self, 'New Password', 'Enter name for the new password:',
                text="password"
            )

            if not ok or not name:
                return  # User cancelled or entered empty name

            # Check if password already exists
            password_path = os.path.join(self.passpy_obj.path_store, f"{name}.gpg")
            if os.path.exists(password_path):
                self.show_error("Cannot Create", f"A password named '{name}' already exists at root level.")
                return

            # Create password entry
            password_data = {
                "PASSWORD": "",
                "url": "",
                "user": "",
                "mail": "",
                "date": datetime.datetime.now().strftime('%a %d %b %Y, %I:%M%p')
            }

            # Write password to store
            if not self.passpy_obj.write_key(name, password_data):
                self.show_error("Error", "Failed to create password file.")
                return

            # Create tree item
            child = PyQt5.QtWidgets.QTreeWidgetItem()
            child.setText(0, name)
            child.setFlags(child.flags() | PyQt5.QtCore.Qt.ItemIsEditable)

            # Add to root
            self.ui.treeWidget.invisibleRootItem().addChild(child)

            # Select new item
            self.ui.treeWidget.setCurrentItem(child)
            self.clicked_item = child
            self.clicked_key = name

        except Exception as e:
            self.show_error("Error adding password", str(e))

    def action_add_folder(self, item):
        """Add a new subfolder with simpler implementation

        Args:
            item: Parent folder tree item
        """
        try:
            # Get folder path
            parent_path = get_parent_path(item)
            folder_name = item.text(0)
            folder_path = os.path.join(self.passpy_obj.path_store, parent_path, folder_name)

            # Verify it's a folder
            if not os.path.isdir(folder_path):
                self.show_error("Invalid Location", "Selected item is not a folder.")
                return

            # Get subfolder name from user
            name, ok = PyQt5.QtWidgets.QInputDialog.getText(
                self, 'New Folder', f'Enter name for new folder in {folder_name}:',
                text="folder"
            )

            if not ok or not name:
                return  # User cancelled or entered empty name

            # Check if folder already exists
            new_folder_path = os.path.join(folder_path, name)
            if os.path.exists(new_folder_path):
                self.show_error("Cannot Create", f"A folder named '{name}' already exists in this location.")
                return

            # Create folder
            os.makedirs(new_folder_path, exist_ok=False)

            # Create tree item
            child = PyQt5.QtWidgets.QTreeWidgetItem()
            child.setText(0, name)
            child.setFlags(child.flags() | PyQt5.QtCore.Qt.ItemIsEditable)

            # Add to parent
            item.addChild(child)

            # Expand parent and select new item
            item.setExpanded(True)
            self.ui.treeWidget.setCurrentItem(child)

        except Exception as e:
            self.show_error("Error adding folder", str(e))

    def action_add_folder_top(self, _):
        """Add a new folder at the root level

        Args:
            _: Unused parameter (sender)
        """
        try:
            # Get folder name from user
            name, ok = PyQt5.QtWidgets.QInputDialog.getText(
                self, 'New Folder', 'Enter name for the new folder:',
                text="folder"
            )

            if not ok or not name:
                return  # User cancelled or entered empty name

            # Check if folder already exists
            folder_path = os.path.join(self.passpy_obj.path_store, name)
            if os.path.exists(folder_path):
                self.show_error("Cannot Create", f"A folder named '{name}' already exists at root level.")
                return

            # Create folder
            os.makedirs(folder_path, exist_ok=False)

            # Create tree item
            child = PyQt5.QtWidgets.QTreeWidgetItem()
            child.setText(0, name)
            child.setFlags(child.flags() | PyQt5.QtCore.Qt.ItemIsEditable)

            # Add to root
            self.ui.treeWidget.invisibleRootItem().addChild(child)

            # Select new item
            self.ui.treeWidget.setCurrentItem(child)

        except Exception as e:
            self.show_error("Error adding folder", str(e))

    def action_dupplicate(self, item):
        """Duplicate a password file with simplified implementation

        Args:
            item: Password tree item to duplicate
        """
        try:
            # Get source file path
            parent_path = get_parent_path(item)
            file_name = item.text(0)
            source_path = os.path.join(self.passpy_obj.path_store, parent_path, f"{file_name}.gpg")

            # Verify it's a file
            if not os.path.isfile(source_path):
                self.show_error("Invalid Item", "Selected item is not a password file.")
                return

            # Generate new name
            base_name = file_name
            # Check if name already has a numeric suffix
            if "_" in file_name:
                parts = file_name.split("_")
                if parts[-1].isdigit():
                    base_name = "_".join(parts[:-1])

            # Find unique name
            counter = 1
            while True:
                new_name = f"{base_name}_{counter}"
                target_path = os.path.join(self.passpy_obj.path_store, parent_path, f"{new_name}.gpg")

                if not os.path.exists(target_path):
                    break

                counter += 1

            # Copy the file
            shutil.copy(source_path, target_path)

            # Create tree item
            child = PyQt5.QtWidgets.QTreeWidgetItem()
            child.setText(0, new_name)
            child.setFlags(child.flags() | PyQt5.QtCore.Qt.ItemIsEditable)

            # Add to parent (same as original)
            parent = item.parent()
            if parent is None:
                self.ui.treeWidget.invisibleRootItem().addChild(child)
            else:
                parent.addChild(child)

            # Select new item
            self.ui.treeWidget.setCurrentItem(child)
            self.clicked_item = child
            self.clicked_key = new_name

        except Exception as e:
            self.show_error("Error duplicating password", str(e))

    def on_item_tree_changed(self, item, column):
        """Handle rename operations when tree item text is edited

        Args:
            item: Tree item being changed
            column: Column index (always 0 for our tree)
        """
        try:
            # Skip processing if we're programmatically changing items
            if self.in_dupplicate:
                return

            # Get current and new names
            new_name = item.text(0)
            if not hasattr(self, 'clicked_key') or self.clicked_key is None:
                # If we don't have a previous key stored, nothing to rename
                print("Warning: No clicked_key stored, can't perform rename operation")
                return

            old_name = self.clicked_key

            # Don't proceed if name hasn't changed
            if old_name == new_name:
                return

            # Get parent path
            parent_path = get_parent_path(item)

            # Log debug info
            print(f"Debug - Tree item changed:")
            print(f"  Old name: {old_name}")
            print(f"  New name: {new_name}")
            print(f"  Parent path: {parent_path}")

            # Build source and target paths for both file and folder scenarios
            source_file_path = os.path.join(self.passpy_obj.path_store, parent_path, f"{old_name}.gpg")
            source_folder_path = os.path.join(self.passpy_obj.path_store, parent_path, old_name)

            target_file_path = os.path.join(self.passpy_obj.path_store, parent_path, f"{new_name}.gpg")
            target_folder_path = os.path.join(self.passpy_obj.path_store, parent_path, new_name)

            # Additional debug info
            print(f"  Source file path: {source_file_path} (exists: {os.path.isfile(source_file_path)})")
            print(f"  Source folder path: {source_folder_path} (exists: {os.path.isdir(source_folder_path)})")
            print(f"  Target file path: {target_file_path} (exists: {os.path.exists(target_file_path)})")
            print(f"  Target folder path: {target_folder_path} (exists: {os.path.exists(target_folder_path)})")

            # Check if target already exists
            if os.path.exists(target_file_path) or os.path.exists(target_folder_path):
                # Revert name change
                self.in_dupplicate = True
                item.setText(0, old_name)
                self.in_dupplicate = False

                self.show_error("Cannot Rename",
                                f"An item named '{new_name}' already exists in this location. "
                                f"Please choose a different name.")
                return

            try:
                # Perform rename based on item type
                if os.path.isfile(source_file_path):
                    # It's a password file
                    print(f"  Renaming file from {source_file_path} to {target_file_path}")
                    os.rename(source_file_path, target_file_path)

                    # CRITICAL: Update the clicked_key to match the new name
                    self.clicked_key = new_name

                    # If we're tracking the full path, update that too
                    if hasattr(self, 'clicked_full_path') and self.clicked_full_path:
                        parts = self.clicked_full_path.split(os.sep)
                        if parts:
                            parts[-1] = new_name
                            self.clicked_full_path = os.sep.join(parts)

                    print(f"  File renamed successfully")

                elif os.path.isdir(source_folder_path):
                    # It's a folder
                    print(f"  Renaming folder from {source_folder_path} to {target_folder_path}")
                    os.rename(source_folder_path, target_folder_path)

                    # CRITICAL: Update the clicked_key to match the new name
                    self.clicked_key = new_name

                    # If we're tracking the full path, update that too
                    if hasattr(self, 'clicked_full_path') and self.clicked_full_path:
                        parts = self.clicked_full_path.split(os.sep)
                        if parts:
                            parts[-1] = new_name
                            self.clicked_full_path = os.sep.join(parts)

                    print(f"  Folder renamed successfully")

                else:
                    # Item doesn't exist in filesystem
                    self.show_error("Item Not Found",
                                    f"Could not find {old_name} in the password store.\n"
                                    f"Checked file: {source_file_path}\n"
                                    f"Checked folder: {source_folder_path}")

                    # Revert name change
                    self.in_dupplicate = True
                    item.setText(0, old_name)
                    self.in_dupplicate = False
                    return

            except PermissionError:
                # Revert name change
                self.in_dupplicate = True
                item.setText(0, old_name)
                self.in_dupplicate = False

                self.show_error("Permission Denied",
                                "You don't have permission to rename this item. "
                                "Check if the file is in use by another program.")
                return
            except FileNotFoundError:
                # Revert name change
                self.in_dupplicate = True
                item.setText(0, old_name)
                self.in_dupplicate = False

                self.show_error("File Not Found",
                                f"The source item no longer exists at {source_file_path} or {source_folder_path}.")
                return
            except OSError as e:
                # Revert name change
                self.in_dupplicate = True
                item.setText(0, old_name)
                self.in_dupplicate = False

                self.show_error("Operating System Error", f"Failed to rename: {str(e)}")
                return

        except Exception as e:
            # Revert name change on error
            self.in_dupplicate = True
            item.setText(0, self.clicked_key if hasattr(self, 'clicked_key') else item.text(0))
            self.in_dupplicate = False

            import traceback
            error_details = traceback.format_exc()
            self.show_error("Error renaming item", f"{str(e)}\n\nDetails:\n{error_details}")

    def dropEvent(self, event):
        """Handle moving items via drag and drop

        Args:
            event: Drop event
        """
        try:
            # Prevent recursive change events
            self.in_dupplicate = True

            # Get drop target
            position = event.pos()
            target_item = self.ui.treeWidget.itemAt(position)

            # Get source item
            source_item = self.ui.treeWidget.currentItem()
            if source_item is None:
                self.in_dupplicate = False
                event.ignore()
                return

            # Get source and target paths
            source_name = source_item.text(0)
            source_parent_path = get_parent_path(source_item)

            # For target, use target item if it's a folder, otherwise use its parent
            if target_item is None:
                # Dropping at root level
                target_path = ""
            else:
                target_folder = os.path.join(self.passpy_obj.path_store, get_parent_path(target_item),
                                             target_item.text(0))
                if os.path.isdir(target_folder):
                    # Target is a folder
                    target_path = os.path.join(get_parent_path(target_item), target_item.text(0))
                else:
                    # Target is a file, move to its parent folder
                    target_path = get_parent_path(target_item)
                    target_item = target_item.parent()

            # Build source and destination file paths
            source_file_path = os.path.join(self.passpy_obj.path_store, source_parent_path, f"{source_name}.gpg")
            dest_file_path = os.path.join(self.passpy_obj.path_store, target_path, f"{source_name}.gpg")

            # Verify source exists and is a file
            if not os.path.isfile(source_file_path):
                self.show_error("Invalid Item", "Only password files can be moved.")
                self.in_dupplicate = False
                event.ignore()
                return

            # Check if destination already exists
            if os.path.exists(dest_file_path):
                # Generate unique name
                base_name = source_name
                counter = 1

                new_name = f"{base_name}_{counter}"
                while os.path.exists(dest_file_path):
                    new_name = f"{base_name}_{counter}"
                    dest_file_path = os.path.join(self.passpy_obj.path_store, target_path, f"{new_name}.gpg")
                    counter += 1

                # Update item name
                source_name = new_name
                source_item.setText(0, source_name)

            # Create destination directory if needed
            os.makedirs(os.path.dirname(dest_file_path), exist_ok=True)

            # Move the file
            shutil.move(source_file_path, dest_file_path)

            # Remove from old parent in tree
            old_parent = source_item.parent()
            if old_parent is None:
                self.ui.treeWidget.takeTopLevelItem(self.ui.treeWidget.indexOfTopLevelItem(source_item))
            else:
                old_parent.removeChild(source_item)

            # Add to new parent in tree
            if target_item is None:
                self.ui.treeWidget.invisibleRootItem().addChild(source_item)
            else:
                target_item.addChild(source_item)
                target_item.setExpanded(True)

            # Accept the event
            event.accept()

        except Exception as e:
            self.show_error("Error moving item", str(e))
            event.ignore()
        finally:
            self.in_dupplicate = False

    def setup_events(self):
        """Set up all event handlers with explicit error handling"""
        try:
            # Tree events
            self.ui.treeWidget.itemChanged.connect(self.on_item_tree_changed)
            self.ui.treeWidget.itemClicked.connect(self.on_item_tree_clicked)
            self.ui.treeWidget.itemExpanded.connect(self.on_item_tree_extend)
            self.ui.treeWidget.itemCollapsed.connect(self.on_item_tree_extend)
            self.ui.treeWidget.setContextMenuPolicy(PyQt5.QtCore.Qt.CustomContextMenu)
            self.ui.treeWidget.customContextMenuRequested.connect(self.context_menu_tree)

            # Table events
            self.ui.tableWidget.cellChanged.connect(self.on_item_table_changed)
            self.ui.tableWidget.cellClicked.connect(self.on_item_table_clicked)
            self.ui.tableWidget.setContextMenuPolicy(PyQt5.QtCore.Qt.CustomContextMenu)
            self.ui.tableWidget.customContextMenuRequested.connect(self.context_menu_table)

            # Table settings events
            self.ui.table_settings.setContextMenuPolicy(PyQt5.QtCore.Qt.CustomContextMenu)
            self.ui.table_settings.customContextMenuRequested.connect(self.context_menu_table_settings)

            # Keys table events
            self.ui.gpg_keys_table.setContextMenuPolicy(PyQt5.QtCore.Qt.CustomContextMenu)
            self.ui.gpg_keys_table.customContextMenuRequested.connect(self.context_menu_table_keys)

            # Button events
            if hasattr(self.ui, "button_encrypt_file"):
                self.ui.button_encrypt_file.clicked.connect(self.encrypt_file)
            if hasattr(self.ui, "button_encrypt_directory"):
                self.ui.button_encrypt_directory.clicked.connect(self.encrypt_directory)
            if hasattr(self.ui, "button_decrypt_file"):
                self.ui.button_decrypt_file.clicked.connect(self.decrypt_file)
            if hasattr(self.ui, "button_decrypt_directory"):
                self.ui.button_decrypt_directory.clicked.connect(self.decrypt_directory)
        except Exception as e:
            self.show_error("Error setting up events", str(e))

    def show_error(self, title, message):
        """Show error dialog with enhanced error information

        Args:
            title: Dialog title
            message: Error message
        """
        # Print to console for debugging
        print(f"ERROR: {title} - {message}")

        # Only show dialog if UI is initialized
        if hasattr(self, 'ui'):
            PyQt5.QtWidgets.QMessageBox.critical(self, title, message)
        else:
            # Fall back to console if UI isn't ready
            print("UI not initialized, showing error in console only")

    def show_info(self, title, message):
        """Show information dialog

        Args:
            title: Dialog title
            message: Information message
        """
        PyQt5.QtWidgets.QMessageBox.information(self, title, message)

    def handle_worker_result(self, success, message):
        """Handle results from worker threads

        Args:
            success: Whether the operation was successful
            message: Result message
        """
        if success:
            self.show_info("Success", message)
        else:
            self.show_error("Error", message)

    def start_worker(self, function, *args, **kwargs):
        """Start a background worker thread for long operations

        Args:
            function: The function to run
            *args: Function arguments
            **kwargs: Function keyword arguments
        """
        worker = WorkerThread(function, *args, **kwargs)
        worker.result_signal.connect(self.handle_worker_result)
        self.worker_threads.append(worker)
        worker.finished.connect(lambda: self.worker_threads.remove(worker) if worker in self.worker_threads else None)
        worker.start()

    def load_config(self):
        """Load configuration into the settings table"""
        try:
            # Clear existing table
            self.ui.table_settings.setRowCount(0)

            # Check if config exists
            if not hasattr(self.passpy_obj, 'config') or not self.passpy_obj.config:
                self.show_error("Configuration Error", "Configuration data not available")
                return

            i = 0
            for section, config_section in self.passpy_obj.config.items():
                if not isinstance(config_section, dict):
                    continue

                for setting, value in config_section.items():
                    self.ui.table_settings.insertRow(i)
                    self.ui.table_settings.setItem(i, 0, PyQt5.QtWidgets.QTableWidgetItem(str(section)))
                    self.ui.table_settings.setItem(i, 1, PyQt5.QtWidgets.QTableWidgetItem(str(setting)))
                    self.ui.table_settings.setItem(i, 2, PyQt5.QtWidgets.QTableWidgetItem(str(value)))
                    i += 1

            # Adjust column widths
            self.ui.table_settings.horizontalHeader().setSectionResizeMode(PyQt5.QtWidgets.QHeaderView.ResizeToContents)
        except Exception as e:
            self.show_error("Error loading configuration", str(e))

    def load_keys(self):
        """Load GPG keys into the keys table"""
        try:
            # Clear existing table
            self.ui.gpg_keys_table.setRowCount(0)

            # Get keys from PassStore
            keys = self.passpy_obj.list_keys()
            if not keys:
                # No keys available, but this isn't an error
                return

            nb_columns = self.ui.gpg_keys_table.columnCount()
            for i, key in enumerate(keys):
                self.ui.gpg_keys_table.insertRow(i)

                # Set key data with safe defaults
                self.ui.gpg_keys_table.setItem(i, 0, PyQt5.QtWidgets.QTableWidgetItem(key.get("mail", "")))
                self.ui.gpg_keys_table.setItem(i, 1, PyQt5.QtWidgets.QTableWidgetItem(key.get("user", "")))
                self.ui.gpg_keys_table.setItem(i, 2, PyQt5.QtWidgets.QTableWidgetItem(key.get("key", "")))
                self.ui.gpg_keys_table.setItem(i, 3, PyQt5.QtWidgets.QTableWidgetItem(key.get("expire", "")))
                self.ui.gpg_keys_table.setItem(i, 4, PyQt5.QtWidgets.QTableWidgetItem(key.get("encryption", "")))
                self.ui.gpg_keys_table.setItem(i, 5, PyQt5.QtWidgets.QTableWidgetItem(key.get("trust", "")))
                self.ui.gpg_keys_table.setItem(i, 6, PyQt5.QtWidgets.QTableWidgetItem(key.get("created", "")))

                # Check for disabled keys and strike them out
                disabled_keys = self.passpy_obj.config.get("settings", {}).get("disabled_keys", [])
                if key.get("key", "") in disabled_keys:
                    for j in range(nb_columns):
                        item = self.ui.gpg_keys_table.item(i, j)
                        if item:
                            f = item.font()
                            f.setStrikeOut(True)
                            item.setFont(f)

            # Adjust column widths
            self.ui.gpg_keys_table.horizontalHeader().setSectionResizeMode(PyQt5.QtWidgets.QHeaderView.ResizeToContents)
        except Exception as e:
            self.show_error("Error loading keys", str(e))

    def events(self):
        """Set up event handlers"""
        try:
            self.event_tree()
            self.event_table()
            self.event_table_keys()
            self.event_table_settings()

            # Connect button events
            if hasattr(self.ui, "button_encrypt_file"):
                self.ui.button_encrypt_file.clicked.connect(self.encrypt_file)
            if hasattr(self.ui, "button_encrypt_directory"):
                self.ui.button_encrypt_directory.clicked.connect(self.encrypt_directory)
            if hasattr(self.ui, "button_decrypt_file"):
                self.ui.button_decrypt_file.clicked.connect(self.decrypt_file)
            if hasattr(self.ui, "button_decrypt_directory"):
                self.ui.button_decrypt_directory.clicked.connect(self.decrypt_directory)
        except Exception as e:
            self.show_error("Error setting up events", str(e))

    def encrypt_file(self):
        """Encrypt file button handler"""
        try:
            path_abs = filedialog.askopenfilename(
                initialdir=self.passpy_obj.path_store,
                title="Select file to encrypt",
                filetypes=[("Any file type", "*.*")]
            )

            if not path_abs:
                return  # User cancelled dialog

            # Confirm operation
            self.confirm(
                lambda: self.start_worker(self.passpy_obj.encrypt_file, path_abs, replace=True),
                f"Encrypt File {os.path.basename(path_abs)} at {os.path.dirname(path_abs)}"
            )
        except Exception as e:
            self.show_error("Error encrypting file", str(e))

    def encrypt_directory(self):
        """Encrypt directory button handler"""
        try:
            path_abs = filedialog.askdirectory(
                initialdir=self.passpy_obj.path_store,
                title="Select directory to encrypt",
            )

            if not path_abs:
                return  # User cancelled dialog

            # Ask if the user wants to create a zip archive
            zip_option = PyQt5.QtWidgets.QMessageBox.question(
                self, 'Encryption Option',
                'Do you want to create a zip archive before encryption?',
                PyQt5.QtWidgets.QMessageBox.Yes | PyQt5.QtWidgets.QMessageBox.No
            )

            use_zip = (zip_option == PyQt5.QtWidgets.QMessageBox.Yes)

            # Confirm operation
            self.confirm(
                lambda: self.start_worker(self.passpy_obj.encrypt_directory, path_abs, replace=True, zip=use_zip),
                f"Encrypt Directory {os.path.basename(path_abs)} in {os.path.dirname(path_abs)}"
            )
        except Exception as e:
            self.show_error("Error encrypting directory", str(e))

    def decrypt_file(self):
        """Decrypt file button handler"""
        try:
            path_abs = filedialog.askopenfilename(
                initialdir=self.passpy_obj.path_store,
                title="Select file to decrypt",
                filetypes=[("Binary GPG file", "*.bgpg")]
            )

            if not path_abs:
                return  # User cancelled dialog

            # Confirm operation
            self.confirm(
                lambda: self.start_worker(self.passpy_obj.decrypt_file, path_abs, replace=True),
                f"Decrypt File {os.path.basename(path_abs)}"
            )
        except Exception as e:
            self.show_error("Error decrypting file", str(e))

    def decrypt_directory(self):
        """Decrypt directory button handler"""
        try:
            path_abs = filedialog.askdirectory(
                initialdir=self.passpy_obj.path_store,
                title="Select directory to decrypt",
            )

            if not path_abs:
                return  # User cancelled dialog

            # Ask if the directory contains a zip archive
            zip_option = PyQt5.QtWidgets.QMessageBox.question(
                self, 'Decryption Option',
                'Does this directory contain encrypted zip archives?',
                PyQt5.QtWidgets.QMessageBox.Yes | PyQt5.QtWidgets.QMessageBox.No
            )

            use_zip = (zip_option == PyQt5.QtWidgets.QMessageBox.Yes)

            # Confirm operation
            self.confirm(
                lambda: self.start_worker(self.passpy_obj.decrypt_directory, path_abs, replace=True, zip=use_zip),
                f"Decrypt Directory {os.path.basename(path_abs)}"
            )
        except Exception as e:
            self.show_error("Error decrypting directory", str(e))

    def event_table_settings(self):
        """Setup table settings event handlers"""
        try:
            self.ui.table_settings.setContextMenuPolicy(PyQt5.QtCore.Qt.CustomContextMenu)
            self.ui.table_settings.customContextMenuRequested.connect(self.context_menu_table_settings)
        except Exception as e:
            self.show_error("Error setting up table settings events", str(e))

    def event_table_keys(self):
        """Setup table keys event handlers"""
        try:
            self.ui.gpg_keys_table.setContextMenuPolicy(PyQt5.QtCore.Qt.CustomContextMenu)
            self.ui.gpg_keys_table.customContextMenuRequested.connect(self.context_menu_table_keys)
        except Exception as e:
            self.show_error("Error setting up table keys events", str(e))

    def event_tree(self):
        """Setup tree event handlers"""
        try:
            self.ui.treeWidget.itemChanged.connect(self.on_item_tree_changed)
            self.ui.treeWidget.itemClicked.connect(self.on_item_tree_clicked)
            self.ui.treeWidget.itemExpanded.connect(self.on_item_tree_extend)
            self.ui.treeWidget.itemCollapsed.connect(self.on_item_tree_extend)
            self.ui.treeWidget.setContextMenuPolicy(PyQt5.QtCore.Qt.CustomContextMenu)
            self.ui.treeWidget.customContextMenuRequested.connect(self.context_menu_tree)
        except Exception as e:
            self.show_error("Error setting up tree events", str(e))

    def event_table(self):
        """Setup table event handlers"""
        try:
            self.ui.tableWidget.cellChanged.connect(self.on_item_table_changed)
            self.ui.tableWidget.cellClicked.connect(self.on_item_table_clicked)
            self.ui.tableWidget.setContextMenuPolicy(PyQt5.QtCore.Qt.CustomContextMenu)
            self.ui.tableWidget.customContextMenuRequested.connect(self.context_menu_table)
        except Exception as e:
            self.show_error("Error setting up table events", str(e))

    def change_path_store(self, _):
        """Change password store location"""
        try:
            new_path = filedialog.askdirectory(
                initialdir=self.passpy_obj.path_store,
                title="Select Store directory",
            )

            if not new_path:
                return  # User cancelled dialog

            if self.passpy_obj.change_path_store(new_path):
                self.restart_app()
        except Exception as e:
            self.show_error("Error changing path store", str(e))

    def restart_app(self):
        """Restart the application"""
        try:
            PyQt5.QtCore.QCoreApplication.quit()
            PyQt5.QtCore.QProcess.startDetached(sys.executable, sys.argv)
        except Exception as e:
            self.show_error("Error restarting application", str(e))
            # Fallback: just quit and let the user restart manually
            PyQt5.QtCore.QCoreApplication.quit()

    def edit_settings(self):
        """Edit settings event handler"""
        try:
            obj = self.sender()
            if not obj:
                return

            key = obj.objectName()
            value = obj.text()

            if not self.passpy_obj.change_config(key, value):
                return

            self.restart_app()
        except Exception as e:
            self.show_error("Error editing settings", str(e))

    @PyQt5.QtCore.pyqtSlot(PyQt5.QtWidgets.QTreeWidgetItem, int)
    def on_item_tree_changed(self, item, _):
        """Tree item changed event handler with full path support"""
        try:
            # Skip if in duplicate mode
            if self.in_dupplicate:
                return

            # Get the new name from the item
            new_name = item.text(0)

            # If no clicked item or key, nothing to do
            if self.clicked_item is None or self.clicked_key is None:
                print("Warning: No clicked item or key when handling tree item change")
                return

            # Don't do anything if the name hasn't changed
            if new_name == self.clicked_key:
                return

            # Use the stored full path instead of just the item name
            if not hasattr(self, 'clicked_full_path') or not self.clicked_full_path:
                print("Warning: No full path stored for this item")
                self.clicked_full_path = get_full_tree_path(item)

            # Get the parent path by removing the last component
            parent_path = os.path.dirname(self.clicked_full_path)

            # Build source and target paths using the parent path
            if parent_path:
                source_file_path = os.path.join(self.passpy_obj.path_store, parent_path, f"{self.clicked_key}.gpg")
                source_dir_path = os.path.join(self.passpy_obj.path_store, parent_path, self.clicked_key)
                target_file_path = os.path.join(self.passpy_obj.path_store, parent_path, f"{new_name}.gpg")
                target_dir_path = os.path.join(self.passpy_obj.path_store, parent_path, new_name)
            else:
                # Root level
                source_file_path = os.path.join(self.passpy_obj.path_store, f"{self.clicked_key}.gpg")
                source_dir_path = os.path.join(self.passpy_obj.path_store, self.clicked_key)
                target_file_path = os.path.join(self.passpy_obj.path_store, f"{new_name}.gpg")
                target_dir_path = os.path.join(self.passpy_obj.path_store, new_name)

            # Print debug information
            print(f"Rename operation:")
            print(f"  Clicked key: {self.clicked_key}")
            print(f"  Full path: {self.clicked_full_path}")
            print(f"  Parent path: {parent_path}")
            print(f"  New name: {new_name}")
            print(f"  Source file path: {source_file_path} (exists: {os.path.isfile(source_file_path)})")
            print(f"  Source dir path: {source_dir_path} (exists: {os.path.isdir(source_dir_path)})")
            print(f"  Target file path: {target_file_path} (exists: {os.path.exists(target_file_path)})")
            print(f"  Target dir path: {target_dir_path} (exists: {os.path.exists(target_dir_path)})")

            renamed = False

            # Check if destination already exists
            if os.path.exists(target_file_path) or os.path.exists(target_dir_path):
                # Revert the rename in the UI
                self.in_dupplicate = True
                item.setText(0, self.clicked_key)
                self.in_dupplicate = False

                # Show error
                item_type = "file" if os.path.isfile(source_file_path) else "folder"
                self.show_error("Rename Error",
                                f"A {item_type} with the name '{new_name}' already exists.")
                return

            # First check if we're dealing with a file
            if os.path.isfile(source_file_path):
                # It's a file
                os.rename(source_file_path, target_file_path)
                # Update the stored path
                if parent_path:
                    self.clicked_full_path = os.path.join(parent_path, new_name)
                else:
                    self.clicked_full_path = new_name
                self.clicked_key = new_name
                renamed = True

            # Then check if it's a directory
            elif os.path.isdir(source_dir_path):
                # It's a directory
                os.rename(source_dir_path, target_dir_path)
                # Update the stored path
                if parent_path:
                    self.clicked_full_path = os.path.join(parent_path, new_name)
                else:
                    self.clicked_full_path = new_name
                self.clicked_key = new_name
                renamed = True

            # If we got here and nothing was renamed, handle the error
            if not renamed:
                print(f"WARNING: Could not find item '{self.clicked_key}' at path '{self.clicked_full_path}' to rename")

                # Revert the item text to the original clicked key
                self.in_dupplicate = True  # Prevent triggering this handler again
                item.setText(0, self.clicked_key)
                self.in_dupplicate = False

        except Exception as e:
            print(f"Error in on_item_tree_changed: {str(e)}")

            # Revert the item text
            self.in_dupplicate = True
            item.setText(0, self.clicked_key)
            self.in_dupplicate = False

            # Show error dialog
            self.show_error("Rename Error", str(e))

    def context_menu_tree(self, position):
        """Tree context menu handler"""
        try:
            item = self.ui.treeWidget.itemAt(position)
            if item is None:
                return self.add_context([
                    ["Add folder", self.action_add_folder_top],
                    ["Add password", self.action_add_password_top],
                    ["Change Path Store", self.change_path_store],
                ], self.treeWidget, position)

            if os.path.isfile(self.get_abs_path(item)):
                return self.add_context([
                    ["Rename password", self.action_rename_item],
                    ["Delete password", self.action_remove],
                    ["Copy infos", self.action_copy_clipboard],
                    ["Dupplicate file", self.action_dupplicate],
                    ["Ignore file", self.action_ignore_file],
                ], item, position)
            else:
                return self.add_context([
                    ["Rename folder", self.action_rename_item],
                    ["Add folder", self.action_add_folder],
                    ["Delete folder", self.action_remove_folder],
                    ["Add password", self.action_add_password],
                    ["Ignore folder", self.action_ignore_folder],
                ], item, position)
        except Exception as e:
            self.show_error("Error showing context menu", str(e))

    def action_ignore_folder(self, item):
        """Ignore folder action handler"""
        try:
            # Safely get folder path
            folder_path = os.path.join(get_rel_path(item), item.text(0))

            # Ensure config paths exist
            if "settings" not in self.passpy_obj.config:
                self.passpy_obj.config["settings"] = {}
            if "ignored_directories" not in self.passpy_obj.config["settings"]:
                self.passpy_obj.config["settings"]["ignored_directories"] = []

            # Add to ignored directories
            self.passpy_obj.config["settings"]["ignored_directories"].append(folder_path)
            utils.write_config(self.passpy_obj.config)

            # Remove from tree
            parent = item.parent()
            if parent is not None:
                parent.removeChild(item)
            else:
                self.ui.treeWidget.takeTopLevelItem(self.ui.treeWidget.indexOfTopLevelItem(item))

            # Refresh config display
            self.load_config()
        except Exception as e:
            self.show_error("Error ignoring folder", str(e))

    def action_ignore_file(self, item):
        """Ignore file action handler"""
        try:
            self.ignore_file(get_rel_path(item, file=True))

            # Remove from tree
            parent = item.parent()
            if parent is not None:
                parent.removeChild(item)
            else:
                self.ui.treeWidget.takeTopLevelItem(self.ui.treeWidget.indexOfTopLevelItem(item))
        except Exception as e:
            self.show_error("Error ignoring file", str(e))

    def ignore_file(self, rel_path, remove=False):
        """Add or remove file from ignored files list"""
        try:
            # Ensure config paths exist
            if "settings" not in self.passpy_obj.config:
                self.passpy_obj.config["settings"] = {}
            if "ignored_files" not in self.passpy_obj.config["settings"]:
                self.passpy_obj.config["settings"]["ignored_files"] = []

            # Add or remove from ignored files
            if remove:
                if rel_path in self.passpy_obj.config["settings"]["ignored_files"]:
                    self.passpy_obj.config["settings"]["ignored_files"].remove(rel_path)
            else:
                if rel_path not in self.passpy_obj.config["settings"]["ignored_files"]:
                    self.passpy_obj.config["settings"]["ignored_files"].append(rel_path)

            utils.write_config(self.passpy_obj.config)
            self.load_config()
        except Exception as e:
            self.show_error("Error updating ignored files", str(e))

    # You should also fix the add_password_file method:
    def add_password_file(self, rel_path):
        """Create a new password file"""
        print(f"Create password at {rel_path}")
        try:
            return self.passpy_obj.write_key(
                rel_path,
                {
                    "PASSWORD": "",
                    "url": "",
                    "user": "",
                    "mail": "",
                    "date": datetime.datetime.now().strftime('%a %d %b %Y, %I:%M%p')
                }
            )
        except Exception as e:
            self.show_error("Error creating password file", str(e))
            return False

    def context_menu_table_settings(self, position):
        """Context menu for settings table"""
        try:
            index = self.ui.table_settings.indexAt(position)
            menu = PyQt5.QtWidgets.QMenu(self)
            actions = []
            if not index.isValid():
                actions_bind = [
                    ["Reset all settings", self.action_reset_all_settings],
                ]
            else:
                actions_bind = [
                    ["Reset selected setting", self.action_reset_selected_setting],
                ]
            for action, func in actions_bind:
                actions.append(menu.addAction(action))
            action = menu.exec_(self.ui.table_settings.viewport().mapToGlobal(position))
            for i, action_check in enumerate(actions):
                if action == action_check:
                    actions_bind[i][1](index)
        except Exception as e:
            self.show_error("Error showing settings menu", str(e))

    def action_reset_all_settings(self, _):
        """Reset all settings to default"""
        try:
            config_path = utils.get_config_path()
            if os.path.exists(config_path):
                os.remove(config_path)
            self.restart_app()
        except Exception as e:
            self.show_error("Error resetting settings", str(e))

    def action_reset_selected_setting(self, index):
        """Reset selected setting to default"""
        try:
            if not index.isValid():
                return

            # Get setting section and key
            row = index.row()
            section = self.ui.table_settings.item(row, 0).text()
            key = self.ui.table_settings.item(row, 1).text()

            # Confirm reset
            if not self.confirm(
                    lambda: None,
                    f"Reset setting '{section}.{key}' to default value?",
                    execute=False
            ):
                return

            # Load default config
            default_config = yaml.safe_load(Path(os.path.join(
                os.path.dirname(__file__), "data", "PassUI.yml")).read_text())

            # Check if setting exists in default config
            if section in default_config and key in default_config[section]:
                default_value = default_config[section][key]

                # Update config
                if section in self.passpy_obj.config:
                    self.passpy_obj.config[section][key] = default_value

                    # Save config
                    utils.write_config(self.passpy_obj.config)

                    # Update UI
                    self.load_config()

                    self.show_info("Setting Reset", f"Setting '{section}.{key}' reset to default value.")
            else:
                self.show_error("Reset Error", f"No default value found for '{section}.{key}'.")
        except Exception as e:
            self.show_error("Error resetting setting", str(e))

    def context_menu_table_keys(self, position):
        """Context menu for keys table"""
        try:
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
                    if key in self.passpy_obj.config.get("settings", {}).get("disabled_keys", []):
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
        except Exception as e:
            self.show_error("Error showing keys menu", str(e))

    def action_disable_key(self, _):
        """Disable selected keys"""
        try:
            items = self.ui.gpg_keys_table.selectedItems()

            # Ensure config paths exist
            if "settings" not in self.passpy_obj.config:
                self.passpy_obj.config["settings"] = {}
            if "disabled_keys" not in self.passpy_obj.config["settings"]:
                self.passpy_obj.config["settings"]["disabled_keys"] = []

            for item in items:
                key = self.ui.gpg_keys_table.item(item.row(), 2).text()
                if key not in self.passpy_obj.config["settings"]["disabled_keys"]:
                    self.passpy_obj.config["settings"]["disabled_keys"].append(key)

            utils.write_config(self.passpy_obj.config)
            self.load_keys()
            self.load_config()
        except Exception as e:
            self.show_error("Error disabling keys", str(e))

    def action_enable_key(self, _):
        """Enable selected keys"""
        try:
            items = self.ui.gpg_keys_table.selectedItems()

            # Ensure config paths exist
            if "settings" not in self.passpy_obj.config:
                self.passpy_obj.config["settings"] = {}
            if "disabled_keys" not in self.passpy_obj.config["settings"]:
                self.passpy_obj.config["settings"]["disabled_keys"] = []

            for item in items:
                key = self.ui.gpg_keys_table.item(item.row(), 2).text()
                if key in self.passpy_obj.config["settings"]["disabled_keys"]:
                    self.passpy_obj.config["settings"]["disabled_keys"].remove(key)

            utils.write_config(self.passpy_obj.config)
            self.load_keys()
            self.load_config()
        except Exception as e:
            self.show_error("Error enabling keys", str(e))

    def context_menu_table(self, position):
        """Context menu for password table"""
        try:
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
        except Exception as e:
            self.show_error("Error showing password table menu", str(e))

    def action_remove_key(self, _):
        """Remove selected GPG keys"""
        try:
            # Get selected keys
            selected_keys = []
            keys_info = []
            items = self.ui.gpg_keys_table.selectedItems()

            # Group by row (to avoid duplicates from multiple cells in same row)
            rows = set()
            for item in items:
                rows.add(item.row())

            # Get key information for confirmation
            for row in rows:
                key = self.ui.gpg_keys_table.item(row, 2).text()
                mail = self.ui.gpg_keys_table.item(row, 0).text()
                selected_keys.append(key)
                keys_info.append(f"{mail} ({key})")

            if not selected_keys:
                return

            # Confirmation message
            sep = "\n\t- "
            self.confirm(
                lambda: self.remove_key(selected_keys),
                f"Delete keys: {sep}{sep.join(keys_info)}"
            )
        except Exception as e:
            self.show_error("Error removing keys", str(e))

    def remove_key(self, keys):
        """Remove keys from GPG keystore"""
        try:
            self.passpy_obj.remove_key(keys=keys)
            self.load_keys()
        except Exception as e:
            self.show_error("Error removing keys", str(e))

    def action_export_key(self, _):
        """Export selected GPG keys"""
        try:
            items = self.ui.gpg_keys_table.selectedItems()

            # Group by row (to avoid duplicates from multiple cells in same row)
            rows = set()
            for item in items:
                rows.add(item.row())

            for row in rows:
                key = self.ui.gpg_keys_table.item(row, 2).text()
                mail = self.ui.gpg_keys_table.item(row, 0).text()

                # Create a filename based on the key ID
                suggested_filename = f"private_{key}.gpg"

                # Ask for export location
                export_path = filedialog.asksaveasfilename(
                    initialdir=self.passpy_obj.path_store,
                    title=f"Export key for {mail}",
                    initialfile=suggested_filename,
                    filetypes=[("GPG key files", "*.gpg")]
                )

                if export_path:
                    self.passpy_obj.export_key(export_path, key)
                    self.show_info("Key Exported", f"Key for {mail} exported to {export_path}")
        except Exception as e:
            self.show_error("Error exporting keys", str(e))

    def action_import_key(self, _):
        """Import GPG key from file"""
        try:
            path_abs_gpg = filedialog.askopenfilename(
                initialdir=self.passpy_obj.path_store,
                title="Select a key file",
                filetypes=[("GPG key files", "*.*")]
            )

            if not path_abs_gpg:
                return  # User cancelled dialog

            # Ask for passphrase if needed
            passphrase = None
            if PyQt5.QtWidgets.QMessageBox.question(
                    self, 'Key Import',
                    'Does this key require a passphrase?',
                    PyQt5.QtWidgets.QMessageBox.Yes | PyQt5.QtWidgets.QMessageBox.No
            ) == PyQt5.QtWidgets.QMessageBox.Yes:
                passphrase, ok = PyQt5.QtWidgets.QInputDialog.getText(
                    self,
                    'Key Passphrase',
                    'Enter the passphrase for this key:',
                    PyQt5.QtWidgets.QLineEdit.Password
                )
                if not ok:
                    return  # User cancelled passphrase dialog

            key_id = self.passpy_obj.import_key(path_abs_gpg, passphrase)
            self.load_keys()
            self.show_info("Key Imported", f"Successfully imported key: {key_id}")
        except Exception as e:
            self.show_error("Error importing key", str(e))

    def action_create_key(self, _):
        """Create a new GPG key"""
        try:
            # Get name
            name, ok = PyQt5.QtWidgets.QInputDialog.getText(
                self,
                'Create Key',
                'Enter your name:'
            )
            if not ok or not name:
                return

            # Get email
            mail, ok = PyQt5.QtWidgets.QInputDialog.getText(
                self,
                'Create Key',
                'Enter your email:'
            )
            if not ok or not mail:
                return

            # Get passphrase
            passphrase, ok = PyQt5.QtWidgets.QInputDialog.getText(
                self,
                'Create Key',
                'Enter a passphrase (leave empty for no passphrase):',
                PyQt5.QtWidgets.QLineEdit.Password
            )
            if not ok:
                return

            # Create key
            self.start_worker(
                lambda: self.create_key_worker(name, mail, passphrase),
                f"Creating key for {name} <{mail}>..."
            )
        except Exception as e:
            self.show_error("Error creating key", str(e))

    def create_key_worker(self, name, mail, passphrase):
        """Background worker for key creation"""
        try:
            key_id = self.passpy_obj.create_key(name, mail, passphrase)
            self.load_keys()
            return True
        except Exception as e:
            return False

    def action_remove_field(self, _):
        """Remove selected field from password"""
        try:
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
        except Exception as e:
            self.show_error("Error removing field", str(e))

    def remove_fields(self, rows):
        """Remove multiple fields from password"""
        try:
            if self.clicked_item is None:
                return

            item = self.clicked_item
            path = os.path.join(get_rel_path(item), item.text(0))
            infos = self.passpy_obj.read_key(path)

            for row in rows:
                field_name = self.ui.tableWidget.item(row, 0).text()
                if field_name in infos:
                    del infos[field_name]
                self.ui.tableWidget.removeRow(row)

            self.passpy_obj.write_key(path, infos)
        except Exception as e:
            self.show_error("Error removing fields", str(e))

    def remove_field(self, row):
        """Remove a single field from password"""
        try:
            if self.clicked_item is None:
                return

            item = self.clicked_item
            path = os.path.join(get_rel_path(item), item.text(0))
            infos = self.passpy_obj.read_key(path)

            field_name = self.ui.tableWidget.item(row, 0).text()
            if field_name in infos:
                del infos[field_name]

            self.ui.tableWidget.removeRow(row)
            self.passpy_obj.write_key(path, infos)
        except Exception as e:
            self.show_error("Error removing field", str(e))

    def action_add_field(self, index):
        """Add a new field to password"""
        try:
            self.edit_table = True
            row = index.row()

            if self.clicked_item is None:
                self.edit_table = False
                return

            item = self.clicked_item
            path = os.path.join(get_rel_path(item), item.text(0))
            infos = self.passpy_obj.read_key(path)

            # Create a new dictionary with fields in the right order
            new_infos = {}

            # Find a unique field name
            field_name = "field"
            i = 0
            while field_name in infos:
                i += 1
                field_name = f"field_{i}"

            # Insert the new field at the specified position
            field_names = list(infos.keys())
            for i, key in enumerate(field_names):
                if i == row:
                    new_infos[field_name] = ""
                new_infos[key] = infos[key]

            # If adding at the end, ensure new field is added
            if row >= len(field_names):
                new_infos[field_name] = ""

            # Update the UI
            self.ui.tableWidget.insertRow(row + 1)
            self.ui.tableWidget.setItem(row + 1, 0, PyQt5.QtWidgets.QTableWidgetItem(field_name))
            self.ui.tableWidget.setItem(row + 1, 1, PyQt5.QtWidgets.QTableWidgetItem(""))

            # Save changes
            self.passpy_obj.write_key(path, new_infos)
            self.edit_table = False
        except Exception as e:
            self.edit_table = False
            self.show_error("Error adding field", str(e))

    def add_context(self, actions_bind, item, position):
        """Create and show a context menu

        Args:
            actions_bind: List of [label, function] pairs
            item: The item the menu is for
            position: The position to show the menu
        """
        try:
            menu = PyQt5.QtWidgets.QMenu(self)
            actions = []

            for action, func in actions_bind:
                actions.append(menu.addAction(action))

            action = menu.exec_(self.ui.treeWidget.viewport().mapToGlobal(position))

            for i, action_check in enumerate(actions):
                if action == action_check:
                    actions_bind[i][1](item)
        except Exception as e:
            self.show_error("Error showing context menu", str(e))

    def action_remove_folder(self, item):
        """Remove a folder and its contents"""
        try:
            path = get_rel_path(item)
            abs_path = os.path.join(self.passpy_obj.path_store, path, item.text(0))

            # Don't allow removing the store root
            if not path and abs_path == self.passpy_obj.path_store:
                self.show_error("Cannot Remove Root", "Cannot remove the root folder of the password store.")
                return

            self.confirm(
                lambda: self.remove_folder(item),
                f"Delete folder '{item.text(0)}' in '{path if path else 'root'}' and all its contents?"
            )
        except Exception as e:
            self.show_error("Error removing folder", str(e))

    def remove_folder(self, item):
        """Remove folder implementation"""
        try:
            path_to_remove = self.get_abs_path(item, folder=True)
            shutil.rmtree(path_to_remove)

            # Remove from tree
            parent = item.parent()
            if parent is None:
                index = self.ui.treeWidget.indexOfTopLevelItem(item)
                self.ui.treeWidget.takeTopLevelItem(index)
            else:
                parent.removeChild(item)
        except Exception as e:
            self.show_error("Error removing folder", str(e))

    def action_remove(self, item):
        """Remove a password file"""
        try:
            self.confirm(
                lambda: self.remove_password(item),
                f"Delete password '{item.text(0)}' in '{get_rel_path(item)}'"
            )
        except Exception as e:
            self.show_error("Error removing password", str(e))

    def action_copy_clipboard(self, item):
        """Copy password information to clipboard"""
        try:
            info = self.passpy_obj.read_key(os.path.join(get_rel_path(item), item.text(0)))

            # Format as plain text
            formatted_info = "\n".join([f"{key}: {value}" for key, value in info.items()])

            # Copy to clipboard
            pyperclip.copy(formatted_info)

            # Notify user
            self.show_info("Copied", "Password information copied to clipboard")

            # TODO: Implement a secure clipboard clear after timeout
        except Exception as e:
            self.show_error("Error copying to clipboard", str(e))

    def confirm(self, func, txt, execute=True):
        """Show a confirmation dialog

        Args:
            func: Function to execute if confirmed
            txt: Message to display
            execute: Whether to execute the function or just return the result

        Returns:
            bool: True if confirmed, False otherwise
        """
        try:
            result = PyQt5.QtWidgets.QMessageBox.question(
                self, 'Confirm', txt,
                PyQt5.QtWidgets.QMessageBox.Yes | PyQt5.QtWidgets.QMessageBox.No
            ) == PyQt5.QtWidgets.QMessageBox.Yes

            if result and execute:
                return func()

            return result
        except Exception as e:
            self.show_error("Error in confirmation dialog", str(e))
            return False

    def remove_password(self, item):
        """Remove a password file"""
        try:
            path_to_remove = self.get_abs_path(item)
            os.remove(path_to_remove)

            # Remove from tree
            parent = item.parent()
            if parent is not None:
                parent.removeChild(item)
            else:
                self.ui.treeWidget.takeTopLevelItem(self.ui.treeWidget.indexOfTopLevelItem(item))

            # Clear password details table
            self.ui.tableWidget.setRowCount(0)
        except Exception as e:
            self.show_error("Error removing password", str(e))

    def get_abs_path(self, item, folder=False):
        """Get absolute path for an item with improved tracking

        Args:
            item: Tree widget item
            folder: Whether the item is a folder

        Returns:
            str: Absolute path
        """
        if item is None:
            if folder:
                return self.passpy_obj.path_store
            return None

        # Build the full path by traversing up the tree
        parts = [item.text(0)]
        parent = item.parent()

        while parent is not None:
            parts.insert(0, parent.text(0))
            parent = parent.parent()

        # Construct the path
        rel_path = os.path.join(*parts) if parts else ""

        if folder:
            return os.path.join(self.passpy_obj.path_store, rel_path)
        else:
            return os.path.join(self.passpy_obj.path_store, rel_path + ".gpg")

    def on_item_table_clicked(self, row, col):
        """Handle click in password table"""
        try:
            item = self.ui.tableWidget.item(row, col)
            if item is None:
                return

            value = item.text()
            field_name = self.ui.tableWidget.item(row, 0).text()

            if col == 1:  # Value column
                # Copy to clipboard
                pyperclip.copy(value)
                self.show_info("Copied", f"Value of '{field_name}' copied to clipboard")
        except Exception as e:
            self.show_error("Error handling table click", str(e))

    def on_item_tree_extend(self):
        """Handle tree item expand/collapse"""
        try:
            self.ui.tableWidget.setRowCount(0)
            self.resize_tree()
        except Exception as e:
            self.show_error("Error handling tree expansion", str(e))

    def resize_tree(self):
        """Resize tree columns to fit content"""
        try:
            self.ui.treeWidget.invisibleRootItem().setExpanded(True)
            self.ui.treeWidget.resizeColumnToContents(0)
            self.ui.treeWidget.invisibleRootItem().setExpanded(False)
        except Exception as e:
            print(f"Error resizing tree: {e}")  # Don't show error dialog to avoid loops

    def load_tree(self):
        """Load the password store into the tree view"""
        try:
            self.ui.treeWidget.clear()

            # Get the password store structure
            rel_paths = self.passpy_obj.rel_paths_gpg

            # Check that we have a valid dictionary
            if not isinstance(rel_paths, dict):
                self.show_error("Invalid Password Store Structure",
                                f"Expected dictionary but got {type(rel_paths).__name__}")
                return

            # Fill the tree
            self.fill_item(
                self.ui.treeWidget.invisibleRootItem(),
                rel_paths
            )

            # Reset clicked item and key when loading the tree
            self.clicked_item = None
            self.clicked_key = None

            # Debug the entire tree structure
            self.debug_tree_structure()

        except Exception as e:
            import traceback
            error_message = f"{str(e)}\n\nStack trace:\n{traceback.format_exc()}"
            self.show_error("Error loading password store", error_message)

    def debug_tree_structure(self):
        """Print the entire tree structure for debugging"""
        try:
            print("\n--- TREE STRUCTURE DEBUG ---")

            def _print_item(item, indent=0):
                # Print current item
                name = item.text(0)
                print(f"{'  ' * indent}{name}")

                # Print all children
                for i in range(item.childCount()):
                    _print_item(item.child(i), indent + 1)

            # Print all top-level items
            root = self.ui.treeWidget.invisibleRootItem()
            for i in range(root.childCount()):
                _print_item(root.child(i))

            print("--- END TREE STRUCTURE DEBUG ---\n")
        except Exception as e:
            print(f"Error in debug_tree_structure: {e}")

    def fill_item(self, item, value):
        """Recursively fill tree with items

        Args:
            item: Parent tree item
            value: Dictionary of items to add
        """
        try:
            # Ensure we're working with a dictionary
            if not isinstance(value, dict):
                print(f"Warning: Expected dictionary in fill_item but got {type(value).__name__}")
                return

            # Sort items by name
            for key in sorted(value.keys()):
                val = value[key]

                child = PyQt5.QtWidgets.QTreeWidgetItem()
                child.setText(0, key)
                item.addChild(child)

                if isinstance(val, dict):
                    self.fill_item(child, val)
                elif isinstance(val, str) and val:
                    # If it's a string value (like a path), don't try to iterate it
                    pass

                child.setFlags(child.flags() | PyQt5.QtCore.Qt.ItemIsEditable)

            self.resize_tree()
        except Exception as e:
            print(f"Error filling tree item: {e}")  # Don't show error dialog to avoid loops

    # @PyQt5.QtCore.pyqtSlot(PyQt5.QtWidgets.QTreeWidgetItem, int)
    def on_item_tree_clicked(self, item, _):
        """Handle tree item click with full path tracking"""
        try:
            key = item.text(0)
            self.clicked_item = item
            self.clicked_key = key

            # Store the full path for this item
            self.clicked_full_path = get_full_tree_path(item)
            print(f"Clicked on: {key}")
            print(f"Full path: {self.clicked_full_path}")

            # Check if this is a password file
            abs_path = self.get_abs_path(item)
            if os.path.isfile(abs_path):
                print(f"Loading password file: {abs_path}")

                # Try to load the password
                try:
                    # Use the full path for reading the key
                    rel_path = os.path.join(get_rel_path(item), item.text(0))
                    infos = self.passpy_obj.read_key(rel_path)

                    # Copy password to clipboard if available
                    if "PASSWORD" in infos:
                        pyperclip.copy(infos["PASSWORD"])

                    # Fill the table with password details
                    self.fill_table(infos)
                except Exception as e:
                    self.show_error("Error loading password", str(e))
        except Exception as e:
            self.show_error("Error handling tree click", str(e))

    def on_item_table_changed(self):
        """Handle password details table changes"""
        try:
            # Skip if we're programmatically changing the table
            if self.edit_table:
                return

            # Make sure we have a password selected
            if self.clicked_item is None:
                return

            # Build a new password dictionary
            new_data = {}
            for row in range(self.ui.tableWidget.rowCount()):
                key_item = self.ui.tableWidget.item(row, 0)
                value_item = self.ui.tableWidget.item(row, 1)

                if key_item is None or value_item is None:
                    continue

                key = key_item.text()
                value = value_item.text()

                # Handle duplicate keys by adding an index
                i = 0
                original_key = key
                while key in new_data:
                    i += 1
                    if i == 1:
                        key = f"{original_key}_1"
                    else:
                        # Extract base name if already indexed
                        parts = original_key.split('_')
                        if parts[-1].isdigit():
                            base = '_'.join(parts[:-1])
                        else:
                            base = original_key
                        key = f"{base}_{i}"

                # Update UI if key was changed
                if i > 0:
                    self.ui.tableWidget.setItem(row, 0, PyQt5.QtWidgets.QTableWidgetItem(key))

                # Add to dictionary
                new_data[key] = value

            # Save changes
            item = self.clicked_item
            path = os.path.join(get_rel_path(item), item.text(0))
            self.passpy_obj.write_key(path, new_data)
        except Exception as e:
            self.show_error("Error saving password changes", str(e))

    def fill_table(self, infos):
        """Fill table with password details

        Args:
            infos: Dictionary of password details
        """
        try:
            # Prevent triggering change events
            self.edit_table = True

            # Clear table
            self.ui.tableWidget.setRowCount(0)

            # Add rows for each field
            for line, info_key in enumerate(infos):
                value = infos[info_key]

                # Add a new row
                self.ui.tableWidget.insertRow(line)

                # Set field name and value
                self.ui.tableWidget.setItem(line, 0, PyQt5.QtWidgets.QTableWidgetItem(info_key))
                self.ui.tableWidget.setItem(line, 1, PyQt5.QtWidgets.QTableWidgetItem(value))

            # Re-enable change events
            self.edit_table = False

            # Adjust column widths
            header = self.ui.tableWidget.horizontalHeader()
            header.setSectionResizeMode(0, PyQt5.QtWidgets.QHeaderView.ResizeToContents)
            header.setSectionResizeMode(1, PyQt5.QtWidgets.QHeaderView.Stretch)
        except Exception as e:
            self.edit_table = False
            self.show_error("Error filling password details", str(e))

    def dragMoveEvent(self, event):
        """Handle drag move events for tree items"""
        try:
            position = event.pos()
            item_at_position = self.ui.treeWidget.itemAt(position)

            # If dragging to empty space, accept
            if item_at_position is None:
                return event.accept()

            # Get the item being dragged
            current_item = self.ui.treeWidget.currentItem()
            if current_item is None:
                return event.ignore()

            # Get parent of current item
            parent_current = current_item.parent()

            # Check if the drop target is a directory
            path_dir_dest = self.get_abs_path(item_at_position, folder=True)

            # Don't allow dropping on parent (no-op)
            if item_at_position == parent_current:
                return event.ignore()
            # Allow dropping in directories
            elif os.path.isdir(path_dir_dest):
                return event.accept()
            # Don't allow dropping on non-directories
            else:
                return event.ignore()
        except Exception as e:
            print(f"Error in dragMoveEvent: {e}")
            return event.ignore()



class Logger:
    """Simple logger class to redirect stdout to a text widget"""

    def __init__(self, ui: PyQt5.QtWidgets.QTextEdit):
        """Initialize logger

        Args:
            ui: Text edit widget to log to
        """
        self.txt = ""
        self.ui = ui

    def __enter__(self):
        """Context manager entry point"""
        self.init = sys.stdout
        sys.stdout = self
        return self

    def __exit__(self, type, value, traceback):
        """Context manager exit point"""
        self.ui.setText(self.txt)
        self.ui.moveCursor(QtGui.QTextCursor.End)
        sys.stdout = self.init

    def write(self, message):
        """Write message to log"""
        self.txt += message

    def flush(self):
        """Flush the output"""
        # Required for compatibility with sys.stdout
        pass
