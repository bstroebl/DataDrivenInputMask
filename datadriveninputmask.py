# -*- coding: utf-8 -*-
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

from ddui import DdManager
import os.path, sys

class DataDrivenInputMask:

    def __init__(self, iface):
        # Save reference to the QGIS interface
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = QtCore.QFileInfo(QgsApplication.qgisUserDbFilePath()).path() + "/python/plugins/datadriveninputmask"
        ddManager = DdManager(self.iface)
        self.app = QgsApplication.instance()
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
        # Create action that will start plugin configuration
        self.action = QtGui.QAction(u"Initialize Layer", self.iface.mainWindow())
        # connect the action to the run method
        QtCore.QObject.connect(self.action, QtCore.SIGNAL("triggered()"), self.run)

        # Add toolbar button and menu item
        self.iface.addPluginToMenu(u"&Data-dirven Input Mask", self.action)

         # Create action that will start plugin configuration
        self.actionSel = QtGui.QAction(u"Show Input Form", self.iface.mainWindow())
        # connect the action to the run method
        QtCore.QObject.connect(self.actionSel, QtCore.SIGNAL("triggered()"), self.runSel)

        # Add toolbar button and menu item
        self.iface.addPluginToMenu(u"&Data-dirven Input Mask", self.actionSel)

    def unload(self):
        # Remove the plugin menu item and icon
        self.app.ddManager.quit()
        #QtGui.QMessageBox.information(None, "", "unload")
        self.iface.removePluginMenu(u"&Data-dirven Input Mask",self.action)
        self.iface.removePluginMenu(u"&Data-dirven Input Mask",self.actionSel)

    # run method that performs all the real work
    def run(self):
        layer = self.iface.activeLayer()
        if 0 != layer.type():   # not a vector layer
            DdError(str(QtGui.QApplication.translate("DdError", "Layer is not a vector layer:", None,
                                                           QtGui.QApplication.UnicodeUTF8) + " %s"% layer.name()))
        else:
            self.app.ddManager.initLayer(layer)

    def runSel(self):
        layer = self.iface.activeLayer()
        if 0 != layer.type():   # not a vector layer
            DdError(str(QtGui.QApplication.translate("DdError", "Layer is not a vector layer:", None,
                                                           QtGui.QApplication.UnicodeUTF8) + " %s"% layer.name()))
        else:
            sel = layer.selectedFeatures()

            if len(sel) > 0:
                feature = sel[0]
                self.app.ddManager.showFeatureForm(layer,  feature)
            else:
                DdError(unicode(QtGui.QApplication.translate("DdError", "No selection in layer:", None,
                                                               QtGui.QApplication.UnicodeUTF8) + " %s"% layer.name()))
