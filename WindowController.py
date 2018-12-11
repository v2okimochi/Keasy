# -*- coding: utf-8 -*-
def controlWindow(gui):
    # =================================
    # Windowsの場合
    # =================================
    from WinWindow import ControlWindowForWindows
    windowController = ControlWindowForWindows(gui)
    # =================================
    # Macの場合
    # =================================
    # from MacWindow import ControlWindowForMac
    # windowController = ControlWindowForMac(gui)
    return windowController
