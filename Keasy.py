# -*- coding: utf-8 -*-
import sys
from PyQt5.QtWidgets import QApplication
from WindowGUI import WindowGUI

if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    execute = WindowGUI()
    sys.exit(app.exec_())
