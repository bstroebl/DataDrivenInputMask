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
from ddattribute import DdTable
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

    def debug(self,  str):
        '''show str in QgsMessageLog'''
        QgsMessageLog.logMessage(str)

    def initGui(self):
        """Add menu and menu items."""

        self.action = QtGui.QAction(QtGui.QApplication.translate("DdLabel", "Initialize Layer",
                                                                 None, QtGui.QApplication.UnicodeUTF8), self.iface.mainWindow())
        # set a name for the action
        self.action.setObjectName("DdInitializeLayer")
        # connect the action to the run method
        self.action.triggered.connect(self.initializeLayer)

        # Add toolbar button and menu item
        self.menuLabel = QtGui.QApplication.translate("DdLabel", "&Data-driven Input Mask",
                                                                 None, QtGui.QApplication.UnicodeUTF8)

        self.actionSel = QtGui.QAction(QtGui.QApplication.translate("DdLabel", "Show Input Form",
                                                                 None, QtGui.QApplication.UnicodeUTF8), self.iface.mainWindow())
        # set a name for the action
        self.actionSel.setObjectName("DdShowInputForm")
        # connect the action to the run method
        self.actionSel.triggered.connect(self.showInputForm)

        self.actionSearch = QtGui.QAction(QtGui.QApplication.translate("DdLabel", "Show Search Form",
                                                                 None, QtGui.QApplication.UnicodeUTF8), self.iface.mainWindow())
        # set a name for the action
        self.actionSearch.setObjectName("DdShowSearchForm")
        # connect the action to the run method
        self.actionSearch.triggered.connect(self.showSearchForm)

        self.actionConfigure = QtGui.QAction(QtGui.QApplication.translate("DdLabel", "Configure Mask",
                                                                 None, QtGui.QApplication.UnicodeUTF8), self.iface.mainWindow())
        # set a name for the action
        self.actionConfigure.setObjectName("DdConfigureMask")
        # connect the action to the run method
        self.actionConfigure.triggered.connect(self.configureMask)

        # Add actions to menu

        if hasattr(self.iface,  "addPluginToVectorMenu"):
            self.iface.addPluginToVectorMenu(self.menuLabel, self.action)
            self.iface.addPluginToVectorMenu(self.menuLabel, self.actionSel)
            self.iface.addPluginToVectorMenu(self.menuLabel, self.actionSearch)
            self.iface.addPluginToVectorMenu(self.menuLabel, self.actionConfigure)
        else:
            self.iface.addPluginToMenu(self.menuLabel, self.action)
            self.iface.addPluginToMenu(self.menuLabel, self.actionSel)
            self.iface.addPluginToMenu(self.menuLabel, self.actionSearch)
            self.iface.addPluginToMenu(self.menuLabel, self.actionConfigure)

    def unload(self):
        """Remove the plugin menu item and icon"""
        self.app.ddManager.quit()

        if hasattr(self.iface, "removePluginVectorMenu"):
            self.iface.removePluginVectorMenu(self.menuLabel, self.action)
            self.iface.removePluginVectorMenu(self.menuLabel, self.actionSel)
            self.iface.removePluginVectorMenu(self.menuLabel, self.actionSearch)
            self.iface.removePluginVectorMenu(self.menuLabel, self.actionConfigure)
        else:
            self.iface.removePluginMenu(self.menuLabel, self.action)
            self.iface.removePluginMenu(self.menuLabel, self.actionSel)
            self.iface.removePluginMenu(self.menuLabel, self.actionSearch)
            self.iface.removePluginMenu(self.menuLabel, self.actionConfigure)

    def createFeature(self, layer):
        '''create a new QgsFeature for the layer'''
        newFeature = QgsFeature()

        provider = layer.dataProvider()
        fields = layer.pendingFields()
        newFeature.initAttributes(fields.count())

        for i in range(fields.count()):
            newFeature.setAttribute(i,provider.defaultValue(i))

        return newFeature

    def isSuitableLayer(self,  layer):
        '''check if layer is suitable to apply a DataDrivenInputMaskl'''
        if None == layer:
            DdError(QtGui.QApplication.translate("DdError", "Please activate a layer!", None,
                                                               QtGui.QApplication.UnicodeUTF8),  iface = self.iface)
        else:
            if 0 != layer.type():   # not a vector layer
                DdError(QtGui.QApplication.translate("DdError", "Layer is not a vector layer: ", None,
                                                               QtGui.QApplication.UnicodeUTF8) + layer.name(),  iface = self.iface)
            else:
                return True

        return False

    def getConfigFeature(self,  configLayer,  ddTable):
        '''returns the QgsFeature for this ddTable in configLayer (public.dd_table)'''
        configLayer.selectAll()
        forFeature = None

        for feat in configLayer.selectedFeatures():
            if feat["table_schema"] == ddTable.schemaName:
                if feat["table_name"] == ddTable.tableName:
                    forFeature = feat
                    break

        configLayer.removeSelection()
        return forFeature

    #Slots
    def initializeLayer(self):
        """SLOT: Create the mask for the active layer"""
        layer = self.iface.activeLayer()

        if self.isSuitableLayer(layer):
            self.app.ddManager.initLayer(layer, skip = [], labels = {},
                fieldOrder = [], fieldGroups = {}, minMax = {}, noSearchFields = [],
                showParents = True, createAction = True, db = None, inputMask = True,
                searchMask = True, inputUi = None, searchUi = None, helpText = "",
                fieldDisable = []) # set the defaults here because somehow some of the values persist

    def showInputForm(self):
        """SLOT: Show the mask for the first selected feature in the active layer"""
        layer = self.iface.activeLayer()

        if self.isSuitableLayer(layer):
            sel = layer.selectedFeatures()

            if len(sel) > 0:
                feature = sel[0]
                self.app.ddManager.showFeatureForm(layer,  feature)
            else:
                DdError(QtGui.QApplication.translate("DdError", "No selection in layer: ", None,
                    QtGui.QApplication.UnicodeUTF8) + layer.name(), iface = self.iface)

    def showSearchForm(self):
        """SLOT: Show the search form for the active layer"""
        layer = self.iface.activeLayer()

        if self.isSuitableLayer(layer):
            self.app.ddManager.showSearchForm(layer)

    def configureMask(self):
        '''SLOT: configure the mask for the active layer using the config tables in the db'''

        layer = self.iface.activeLayer()

        if self.isSuitableLayer(layer):
            ddLayerTable = self.app.ddManager.makeDdTable(layer)

            if ddLayerTable != None:
                ddConfigTable = DdTable(schemaName = "public",  tableName = "dd_table")
                # is the config layer already loaded?
                db = self.app.ddManager.getDbForLayer(layer)

                if db == None:
                    return None

                configLayer = self.app.ddManager.findPostgresLayer(db,  ddConfigTable)

                if configLayer == None:
                    #check if config tables exist in the db
                    if self.app.ddManager.existsInDb(ddConfigTable,  db):
                        #update the tables if necessary
                        self.app.ddManager.changeConfigTables(db)
                    else:
                        # create config tables
                        if not self.app.ddManager.createConfigTables(db):
                            return None

                    #load the config table into the project
                    configLayer = self.app.ddManager.loadPostGISLayer(db, ddConfigTable, keyColumn = "id")

                    if not configLayer.dataProvider().isValid():
                        return None

                # is the table already configured?
                forFeature = self.getConfigFeature(configLayer,  ddLayerTable)

                if forFeature == None:
                    # create the feature for this table
                    if not configLayer.isEditable():
                        configLayer.startEditing()

                    forFeature = self.createFeature(configLayer)
                    forFeature[configLayer.fieldNameIndex("table_schema")] = ddLayerTable.schemaName
                    forFeature[configLayer.fieldNameIndex("table_name")] = ddLayerTable.tableName
                    configLayer.addFeature(forFeature)

                    if not configLayer.commitChanges():
                        return None

                    configLayer.reload()
                    forFeature = self.getConfigFeature(configLayer,  ddLayerTable)

                self.app.ddManager.showFeatureForm(configLayer,  forFeature)



