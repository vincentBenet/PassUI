from PyQt5 import QtWidgets
from . import PassPy, PassUI
import sys


def run():
    app = QtWidgets.QApplication([])  # Create an instance of QtWidgets.QApplication
    passpy_obj = PassPy()  # Init of backend
    PassUI(passpy_obj)  # Init of frontend
    sys.exit(app.exec_())  # Start the application


if __name__ == "__main__":
    run()
