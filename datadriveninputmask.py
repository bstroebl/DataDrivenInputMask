# -*- coding: utf-8 -*-
"""
datadriveninputmask
-----------------------------------
"""
"""
/***************************************************************************
DataDrivenInputMask
A QGIS plugin
Applies a data-driven input mask to any PostGIS-Layer
                              -------------------
        begin                : 2012-06-21
        copyright            : (C) 2012 by Bernhard Ströbl / Kommunale Immobilien Jena
        email                : bernhard.stroebl@jena.de
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
# Import the PyQt and QGIS libraries
from PyQt4 import QtCore,  QtGui
from qgis.core import *
from dderror import DdError
from ddmanager import DdManager
import os.path, sys

class DataDrivenInputMask:
    """Main class for the QGIS plugin"""
    def __init__(self, iface):
        # Save reference to the QGIS interface
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = QtCore.QFileInfo(QgsApplication.qgisUserDbFilePath()).path() + "/python/plugins/DataDrivenInputMask"
        self.app = QgsApplication.instance()
        try:
            self.app.ddManager
        except AttributeError:
            ddManager = DdManager(self.iface)
            self.app.ddManager = ddManager
        # initialize locale
        localePath = ""
        locale = QtCore.QSettings().value("locale/userLocale")[0:2]

        libPath = os.path.dirname(__file__)
        libPathFound = False

        for p in sys.path:
            if p == libPath:
                libPathFound = True
                break

        if not libPathFound:
            sys.path.append(libPath)

        if QtCore.QFileInfo(self.plugin_dir).exists():
            localePath = self.plugin_dir + "/i18n/datadriveninputmask_" + locale + ".qm"

        if QtCore.QFileInfo(localePath).exists():
            self.translator = QtCore.QTranslator()
            self.translator.load(localePath)

            if QtCore.qVersion() > '4.3.3':
                QtCore.QCoreApplication.installTranslator(self.translator)

    def initGui(self):
        """Add menu and menu items."""
        # Create action that will start plugin configuration
        self.action = QtGui.QAction(QtGui.QApplication.translate("DdLabel", "Initialize Layer",
                                                                 None, QtGui.QApplication.UnicodeUTF8), self.iface.mainWindow())
        # set a name for the action
        self.action.setObjectName("DdInitializeLayer")
        # connect the action to the run method
        self.action.triggered.connect(self.initializeLayer)

        # Add toolbar button and menu item
        self.menuLabel = QtGui.QApplication.translate("DdLabel", "&Data-driven Input Mask",
                                                                 None, QtGui.QApplication.UnicodeUTF8)

        # Create action that will start plugin configuration
        self.actionSel = QtGui.QAction(QtGui.QApplication.translate("DdLabel", "Show Input Form",
                                                                 None, QtGui.QApplication.UnicodeUTF8), self.iface.mainWindow())
        # set a name for the action
        self.actionSel.setObjectName("DdShowInputForm")
        # connect the action to the run method
        self.actionSel.triggered.connect(self.showInputForm)


        # Create action that will start plugin configuration
        self.actionSearch = QtGui.QAction(QtGui.QApplication.translate("DdLabel", "Show Search Form",
                                                                 None, QtGui.QApplication.UnicodeUTF8), self.iface.mainWindow())
        # set a name for the action
        self.actionSearch.setObjectName("DdShowSearchForm")
        # connect the action to the run method
        self.actionSearch.triggered.connect(self.showSearchForm)

        # Add actions to menu

        if hasattr(self.iface,  "addPluginToVectorMenu"):
            self.iface.addPluginToVectorMenu(self.menuLabel, self.action)
            self.iface.addPluginToVectorMenu(self.menuLabel, self.actionSel)
            self.iface.addPluginToVectorMenu(self.menuLabel, self.actionSearch)
        else:
            self.iface.addPluginToMenu(self.menuLabel, self.action)
            self.iface.addPluginToMenu(self.menuLabel, self.actionSel)
            self.iface.addPluginToMenu(self.menuLabel, self.actionSearch)

    def unload(self):
        """Remove the plugin menu item and icon"""
        self.app.ddManager.quit()

        if hasattr(self.iface, "removePluginVectorMenu"):
            self.iface.removePluginVectorMenu(self.menuLabel, self.action)
            self.iface.removePluginVectorMenu(self.menuLabel, self.actionSel)
            self.iface.removePluginVectorMenu(self.menuLabel, self.actionSearch)
        else:
            self.iface.removePluginMenu(self.menuLabel, self.action)
            self.iface.removePluginMenu(self.menuLabel, self.actionSel)
            self.iface.removePluginMenu(self.menuLabel, self.actionSearch)

    def initializeLayer(self):
        """Create the mask for the active layer"""
        layer = self.iface.activeLayer()

        if None == layer:
            DdError(QtGui.QApplication.translate("DdError", "Please activate a layer!", None,
                                                               QtGui.QApplication.UnicodeUTF8),  iface = self.iface)
        else:
            if 0 != layer.type():   # not a vector layer
                DdError(QtGui.QApplication.translate("DdError", "Layer is not a vector layer: ", None,
                                                               QtGui.QApplication.UnicodeUTF8) + layer.name(),  iface = self.iface)
            else:
                self.app.ddManager.initLayer(layer,  skip = [])

    def showInputForm(self):
        """Show the mask for the first selected feature in the active layer"""
        layer = self.iface.activeLayer()

        if None == layer:
            DdError(QtGui.QApplication.translate("DdError", "Please activate a layer!", None,
                                                               QtGui.QApplication.UnicodeUTF8),  iface = self.iface)
        else:
            if 0 != layer.type():   # not a vector layer
                DdError(QtGui.QApplication.translate("DdError", "Layer is not a vector layer: ", None,
                                                               QtGui.QApplication.UnicodeUTF8) + layer.name(),  iface = self.iface)
            else:
                sel = layer.selectedFeatures()

                if len(sel) > 0:
                    feature = sel[0]
                    self.app.ddManager.showFeatureForm(layer,  feature)
                else:
                    DdError(QtGui.QApplication.translate("DdError", "No selection in layer: ", None,
                                                                   QtGui.QApplication.UnicodeUTF8) + layer.name(),  iface = self.iface)

    def showSearchForm(self):
        """Show the search form for the active layer"""
        layer = self.iface.activeLayer()

        if None == layer:
            DdError(QtGui.QApplication.translate("DdError", "Please activate a layer!", None,
                                                               QtGui.QApplication.UnicodeUTF8),  iface = self.iface)
        else:
            if 0 != layer.type():   # not a vector layer
                DdError(QtGui.QApplication.translate("DdError", "Layer is not a vector layer: ", None,
                                                               QtGui.QApplication.UnicodeUTF8) + layer.name(),  iface = self.iface)
            else:
                self.app.ddManager.showSearchForm(layer)
