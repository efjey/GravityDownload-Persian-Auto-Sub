import sys

from PySide6.QtWidgets import QApplication

from app.ui.main_window import MainWindow


APP_NAME = "GravityDownload Persian Auto Sub"
APP_VERSION = "0.1.0"


def main():
    app = QApplication(sys.argv)

    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setOrganizationName("GravityDownload")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()