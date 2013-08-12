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

from PyQt4 import QtGui
from qgis.core import *

# create the dialog
class DdDialog(QtGui.QDialog):
    '''Each mask is a DdDialog instance, thus a child of QDialog'''
    def __init__(self,  ddManager,  ui,  layer,  feature,  db,  parent = None):
        QtGui.QDialog.__init__(self,  parent)
        # Set up the user interface from Designer.
        self.ddManager = ddManager
        self.ui = ui
        #QtGui.QMessageBox.information(None, "", str(self.ui))
        self.layer = layer
        self.feature = feature
        self.db = db
        self.forEdit = self.layer.isEditable()
        self.ui.setupUi(self,  self.db)
        okBtn = self.ui.buttonBox.button(QtGui.QDialogButtonBox.Ok)
        okBtn.setEnabled(self.forEdit)
        self.setTitle()
        self.initialize()

    def setTitle(self):
        title = self.layer.name()
        title += " - "

        if self.feature.id() < 0:
            title += QtGui.QApplication.translate("DdInfo", "New Feature",
                     None, QtGui.QApplication.UnicodeUTF8)
        else:
            title += QtGui.QApplication.translate("DdInfo", "Feature",
                    None, QtGui.QApplication.UnicodeUTF8) + " " + str(self.feature.id())

        self.setWindowTitle(title)

    def initialize(self):
        self.ui.initialize(self.layer,  self.feature,  self.db)

    def accept(self):
        if self.ui.checkInput():
            hasChanges = self.ui.save(self.layer,  self.feature,  self.db)

            if hasChanges:
                self.done(1)
            else:
                self.done(0)

    def reject(self):
        self.ui.discard()
        self.done(0)

class DdSearchDialog(QtGui.QDialog):
    '''Each searchDialog is a child of QDialog'''
    def __init__(self,  ddManager,  ui,  layer,  db,  parent = None):
        QtGui.QDialog.__init__(self,  parent)
        # Set up the user interface from Designer.
        self.ddManager = ddManager
        self.ui = ui
        #QtGui.QMessageBox.information(None, "", str(self.ui))
        self.layer = layer
        self.db = db
        self.feature = QgsFeature(-3333)
        fields = self.layer.pendingFields()
        self.feature.initAttributes(fields.count())
        self.ui.setupUi(self,  self.db)
        okBtn = self.ui.buttonBox.button(QtGui.QDialogButtonBox.Ok)
        okBtn.setEnabled(True)
        self.setTitle()
        self.initialize()

    def setTitle(self):
        title = self.layer.name()
        title += " - "

        title += QtGui.QApplication.translate("DdInfo", "Search",
                 None, QtGui.QApplication.UnicodeUTF8)

        self.setWindowTitle(title)

    def initialize(self):
        self.ui.initialize(self.layer,  self.feature,  self.db)

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
            self.layer.setSubsetString(oldSubsetString)
            self.layer.reload()

            if self.layer.selectedFeatureCount() == 0:
                QtGui.QMessageBox.information(None,  "", QtGui.QApplication.translate("DdInfo", "No matches found", None,
                                                                   QtGui.QApplication.UnicodeUTF8))
                return None
            else:
                if self.layer.geometryType() != 4: # layer with geometry
                    self.ddManager.iface.mapCanvas().zoomToSelected(self.layer)

            if self.layer.geometryType() != 4:
                self.ddManager.iface.mapCanvas().refresh()

            self.done(1)
        else:
            self.done(0)

    def reject(self):
        self.ui.discard()
        self.done(0)
