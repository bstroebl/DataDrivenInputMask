# -*- coding: utf-8 -*-
"""
dddialog
-----------------------------------
"""
"""
/***************************************************************************
 DataDrivenDialog
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

from builtins import str

from qgis.PyQt import QtGui, QtCore, QtWidgets
from qgis.core import *
from qgis.gui import *
import xml.etree.ElementTree as ET
import os

# create the dialog
class DdDialog(QtWidgets.QDialog):
    '''Each mask is a DdDialog instance, thus a child of QDialog'''
    def __init__(self, ddManager, ui, layer, feature, db, multiEdit = False,
            parent = None, title = None):
        super().__init__(parent)
        # Set up the user interface from Designer.
        self.ddManager = ddManager
        self.ui = ui
        self.layer = layer
        self.feature = feature
        self.db = db
        self.forwardReturn = True # use return pressed to accept self

        if multiEdit:
            self.mode = 2
        else:
            self.mode = 0

        self.forEdit = self.layer.isEditable()
        self.ui.setupUi(self,  self.db)
        okBtn = self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok)
        okBtn.setEnabled(self.forEdit)
        okBtn.setVisible(self.forEdit)
        self.setTitle(title)
        self.initialize()

    def debug(self, str):
        QgsMessageLog.logMessage(str)

    def setTitle(self,  title = None):
        if title == None:
            title = self.layer.name()
            title += " - "

            if self.mode == 2:
                title += QtWidgets.QApplication.translate("DdInfo", "%s selected features") % str(self.layer.selectedFeatureCount())
            else:
                if self.feature.id() < 0:
                    title += QtWidgets.QApplication.translate("DdInfo", "New Feature")
                else:
                    title += QtWidgets.QApplication.translate("DdInfo", "Feature" )  + str(self.feature.id())

        self.setWindowTitle(title)

    def initialize(self):
        self.ui.initialize(self.layer, self.feature, self.db, self.mode)

    def setForwardReturn(self, doForward = True):
        self.forwardReturn = doForward

    def accept(self):
        if self.forwardReturn:
            if self.ui.checkInput(self.layer, self.feature):
                hasChanges = self.ui.save(self.layer, self.feature, self.db)

                if hasChanges:
                    self.done(1)
                else:
                    self.done(2)

    def reject(self):
        self.ui.discard()
        self.done(0)

    def helpRequested(self):
        dlg = QtWidgets.QDialog(None)
        layout = QtWidgets.QVBoxLayout(dlg)
        layout.setObjectName("layout")
        dlg.setObjectName("Help")
        dlg.setWindowModality(QtCore.Qt.ApplicationModal)
        textBrowser = QtWidgets.QTextBrowser(dlg)
        textBrowser.setReadOnly(True)
        textBrowser.setText(self.ui.helpText)
        textBrowser.setTextInteractionFlags(QtCore.Qt.TextBrowserInteraction)
        textBrowser.setOpenExternalLinks(True)
        layout.addWidget(textBrowser)
        buttonBox = QtWidgets.QDialogButtonBox(dlg)
        buttonBox.setOrientation(QtCore.Qt.Horizontal)
        buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.Close)
        buttonBox.setObjectName("buttonBox")
        layout.addWidget(buttonBox)
        buttonBox.rejected.connect(dlg.reject)
        dlg.setLayout(layout)
        dlg.setWindowTitle(QtWidgets.QApplication.translate("DdInfo", "Help"))
        dlg.exec_()

class DdSearchDialog(QtWidgets.QDialog):
    '''Each searchDialog is a child of QDialog'''
    def __init__(self, ui, layer, db, parent = None,  root = None):
        super().__init__(parent)
        self.ddManager = QgsApplication.instance().ddManager
        self.ui = ui
        self.layer = layer
        self.db = db
        self.mode = 1
        self.feature = QgsFeature(-3333)
        fields = self.layer.pendingFields()
        self.feature.initAttributes(fields.count())
        self.ui.setupUi(self,  self.db)
        self.ui.buttonBox.accepted.disconnect(self.accept)
        self.ui.buttonBox.rejected.disconnect(self.reject)
        self.ui.buttonBox.clicked.connect(self.clicked)
        self.ui.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.Cancel| \
                                             QtWidgets.QDialogButtonBox.Ok|QtWidgets.QDialogButtonBox.Save| \
                                             QtWidgets.QDialogButtonBox.Open|QtWidgets.QDialogButtonBox.Reset)
        okBtn = self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok)
        okBtn.setEnabled(True)
        self.forwardReturn = True # use return pressed to accept self
        self.setTitle()
        self.initialize()

        if root == None:
            root = self.ddManager.ddLayers[self.layer.id()][6]

            if root == None:
                root = self.createSearch()

        self.applySearch(root)

    def debug(self,  str):
        QgsMessageLog.logMessage(str)

    def setTitle(self):
        title = self.layer.name()
        title += " - "

        title += QtWidgets.QApplication.translate("DdInfo", "Search")

        self.setWindowTitle(title)

    def initialize(self):
        self.ui.initialize(self.layer, self.feature, self.db, self.mode)

    def setForwardReturn(self, doForward = True):
        self.forwardReturn = doForward

    def clicked(self,  thisButton):
        if thisButton == self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok):
            if self.forwardReturn:
                root = self.createSearch()

                if self.ddManager.setLastSearch(self.layer,  root):
                    self.accept()
        elif thisButton == self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Cancel):
            self.reject()
        elif thisButton == self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Save):
            self.saveSearch()
        elif thisButton == self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Open):
            root = self.loadSearch()
            self.applySearch(root)
        elif thisButton == self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Reset):
            self.initialize()

    def accept(self):
        searchString = self.ui.search(self.layer)

        if searchString != "":
            oldSubsetString = self.layer.subsetString()

            if oldSubsetString == "":
                newSubsetString = searchString
            else:
                newSubsetString = "(" + oldSubsetString + ") AND (" + searchString + ")"

            self.layer.setSubsetString(newSubsetString)
            self.layer.reload()
            self.layer.selectAll()
            selFids = self.layer.selectedFeaturesIds()

            if self.layer.selectedFeatureCount() == 0:
                QtWidgets.QMessageBox.information(None,  "",
                    QtWidgets.QApplication.translate("DdInfo", "No matches found"))
                return None
            else:
                if self.layer.geometryType() != 4: # layer with geometry
                    self.ddManager.iface.mapCanvas().zoomToSelected(self.layer)

            if self.layer.geometryType() != 4:
                self.ddManager.iface.mapCanvas().refresh()

            self.layer.setSubsetString(oldSubsetString)
            self.layer.reload()
            self.layer.setSelectedFeatures(selFids)
            self.done(1)
        else:
            self.done(0)

    def createSearch(self):
        root = ET.Element('DdSearch')
        self.ui.createSearch(root)
        return root

    def saveSearch(self):
        path = self.ddManager.getSearchPath()
        title = QtWidgets.QApplication.translate("DdLabel", "Save search as")
        filter = "DdXML (*.ddsx)"

        if os.name == "posix":
            fd = QtWidgets.QFileDialog(None,  title,  path,  filter)
            fd.setDefaultSuffix("ddsx")
            fd.setAcceptMode(QtWidgets.QFileDialog.AcceptSave)

            if fd.exec_() == 1:
                saveAs = fd.selectedFiles()[0]
            else:
                saveAs = ""

        else:
            saveAs = QtWidgets.QFileDialog.getSaveFileName(None,  title,  path, filter)

        if saveAs != "":
            root = self.createSearch()
            tree = ET.ElementTree()
            tree._setroot(root)
            tree.write(saveAs,encoding = "utf-8",  xml_declaration = True)
            path = os.path.abspath(os.path.dirname(saveAs))
            self.ddManager.saveSearchPath(path)

    def applySearch(self,  root):
        self.ui.applySearch(root)

    def loadSearch(self):
        path = self.ddManager.getSearchPath()
        loadThis = QtWidgets.QFileDialog.getOpenFileName(None,
            QtWidgets.QApplication.translate("DdLabel", "Load search"),
            path, "DdXML (*.ddsx)")

        if loadThis != u"":
            tree = ET.parse(loadThis)
            root = tree.getroot()
        else:
            root = ET.Element('DdSearch')

        return root

    def reject(self):
        self.ui.discard()
        self.done(0)
