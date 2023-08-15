from PyQt5 import QtWidgets
import PassUI

app = QtWidgets.QApplication([])  # Create an instance of QtWidgets.QApplication
passpy_obj = PassUI.PassPy()  # Init of backend
PassUI.PassUI(passpy_obj)  # Init of frontend
app.exec_()  # Start the application
