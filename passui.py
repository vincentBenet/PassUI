
def main():
    from PyQt5 import QtWidgets
    import PassUI

    app = QtWidgets.QApplication([])  # Create an instance of QtWidgets.QApplication
    passpy_obj = PassUI.passpy_api.PassPy()  # Init of backend
    PassUI.pyqt5_api.PassUI(passpy_obj)  # Init of frontend
    app.exec_()  # Start the application


if __name__ == "__main__":
    main()
