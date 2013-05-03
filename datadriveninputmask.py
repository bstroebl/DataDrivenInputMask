# -*- coding: utf-8 -*-
"""
DataDrivenInputMask
"""
"""
/***************************************************************************
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

from ddui import DdManager
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
        locale = QtCore.QSettings().value("locale/userLocale").toString()[0:2]

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
        # connect the action to the run method
        QtCore.QObject.connect(self.action, QtCore.SIGNAL("triggered()"), self.initializeLayer)

        # Add toolbar button and menu item
        self.menuLabel = QtGui.QApplication.translate("DdLabel", "&Data-driven Input Mask",
                                                                 None, QtGui.QApplication.UnicodeUTF8)
        self.iface.addPluginToMenu(self.menuLabel, self.action)

         # Create action that will start plugin configuration
        self.actionSel = QtGui.QAction(QtGui.QApplication.translate("DdLabel", "Show Input Form",
                                                                 None, QtGui.QApplication.UnicodeUTF8), self.iface.mainWindow())
        # connect the action to the run method
        QtCore.QObject.connect(self.actionSel, QtCore.SIGNAL("triggered()"), self.showInputForm)

        # Add toolbar button and menu item
        self.iface.addPluginToMenu(self.menuLabel, self.actionSel)

    def unload(self):
        """Remove the plugin menu item and icon"""
        self.app.ddManager.quit()
        #QtGui.QMessageBox.information(None, "", "unload")
        self.iface.removePluginMenu(self.menuLabel, self.action)
        self.iface.removePluginMenu(self.menuLabel, self.actionSel)

    def initializeLayer(self):
        """Create the mask for the active layer"""
        layer = self.iface.activeLayer()
        if 0 != layer.type():   # not a vector layer
            DdError(QtGui.QApplication.translate("DdError", "Layer is not a vector layer: ", None,
                                                           QtGui.QApplication.UnicodeUTF8).append(layer.name()))
        else:
            self.app.ddManager.initLayer(layer,  skip = [])

    def showInputForm(self):
        """Show the mask for the first selected feature in the active layer"""
        layer = self.iface.activeLayer()
        if 0 != layer.type():   # not a vector layer
            DdError(QtGui.QApplication.translate("DdError", "Layer is not a vector layer: ", None,
                                                           QtGui.QApplication.UnicodeUTF8).append(layer.name()))
        else:
            sel = layer.selectedFeatures()

            if len(sel) > 0:
                feature = sel[0]
                self.app.ddManager.showFeatureForm(layer,  feature)
            else:
                DdError(QtGui.QApplication.translate("DdError", "No selection in layer: ", None,
                                                               QtGui.QApplication.UnicodeUTF8).append(layer.name()))
