
def main():
    from PyQt5 import QtWidgets
    import PassUI

    app = QtWidgets.QApplication([])  # Create an instance of QtWidgets.QApplication
    passpy_obj = PassUI.passstore.PassPy()  # Init of backend
    PassUI.ui.PassUI(passpy_obj)  # Init of frontend
    app.exec_()  # Start the application


if __name__ == "__main__":
    main()
