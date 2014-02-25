# -*- coding: utf-8 -*-
"""
userClass
--------
user classes are not instantiated by the plugin but are
to be used in subclasses of DataDrivenUi
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


from ddui import DdInputWidget,  DdN2mWidget
from dderror import DdError,  DbError
from PyQt4 import QtCore,  QtGui,  QtSql

class DdPushButton(DdInputWidget):
    '''abstract class needs subclassing'''

    def __init__(self,  attribute):
        DdInputWidget.__init__(self,  attribute)

    def __str__(self):
        return "<ddui.DdPushButton %s>" % str(self.attribute.label)

    def setupUi(self,  parent,  db):
        self.label = self.getLabel()
        self.inputWidget = QtGui.QPushButton(self.label,  parent)
        self.inputWidget.setToolTip(self.attribute.comment)
        self.inputWidget.clicked.connect(self.clicked)
        hLayout = QtGui.QHBoxLayout()
        hLayout.addStretch()
        hLayout.addWidget(self.inputWidget)
        hLayout.addStretch()
        parent.layout().addRow(hLayout)

    def clicked(self):
        QtGui.QMessageBox.information(None,  "",  self.label + " has been clicked")

    def initialize(self,  layer,  feature,  db):
        '''must be implemented in child class'''
        pass

    def save(self,  layer,  feature,  db):
        return False

class DdN2mCheckableTableWidget(DdN2mWidget):
    '''a table widget for a n2m relation with more than the
    pk fields in the relation table but with checkboxes to assign a value
    to the feature, values to fields in the relation table are assigned
    in the table wiget with doubleClick
    attribute is a DdCheckableTableAttribute'''

    def __init__(self,  attribute):
        DdN2mWidget.__init__(self,  attribute)

    def __str__(self):
        return "<ddui.DdN2mCheckableTableWidget %s>" % str(self.attribute.label)

    def createInputWidget(self,  parent):
        inputWidget = QtGui.QTableWidget(parent)
        inputWidget.setColumnCount(len(self.attribute.attributes) + 1)
        horizontalHeaders =  [""]

        for anAtt in self.attribute.attributes:
            horizontalHeaders.append(anAtt.name)

        inputWidget.setHorizontalHeaderLabels(horizontalHeaders)
        inputWidget.setSelectionMode(QtGui.QAbstractItemView.SingleSelection)
        inputWidget.setSelectionBehavior(QtGui.QAbstractItemView.SelectRows)
        inputWidget.setEditTriggers(QtGui.QAbstractItemView.DoubleClicked)
        inputWidget.setSortingEnabled(True)
        inputWidget.setObjectName("tbl" + parent.objectName() + self.attribute.name)
        return inputWidget

    def loadRelatedLayer(self , db):
        self.relatedLayer = self.parentDialog.ddManager.findPostgresLayer(db,  self.attribute.relatedTable)

        if not self.relatedLayer:
            # load the layer into the project
            self.relatedLayer = self.parentDialog.ddManager.loadPostGISLayer(db,  self.attribute.relatedTable)

    def initialize(self,  layer,  feature,  db):
        if feature != None:
            self.initializeLayer(layer,  feature,  db,  doShowParents = False,  withMask = True,  skip = [self.attribute.relationRelatedIdField])
            self.loadRelatedLayer(db)

            for i in range(len(self.attribute.attributes)):
                anAttr = self.attribute.attributes[i]

                if anAttr.name == self.attribute.relationRelatedIdField:
                    self.relationRelatedIdIndex = i
                    break

            self.fill()

    def fill(self):
        self.relatedLayer.removeSelection()
        self.relatedLayer.invertSelection()
        self.tableLayer.removeSelection()
        self.tableLayer.invertSelection()
        relatedValues = []
        checkedRelatedValues = []
        valueDict = {}
        defaultValues = []

        for anAttr in self.attribute.attributes:
            if anAttr.hasDefault:
                defaultValues.append(anAttr.default)
            else:
                defaultValues.append("NULL")

        for relatedFeature in self.relatedLayer.selectedFeatures():
            relatedId = relatedFeature.id()
            relatedValue = relatedFeature[self.relatedLayer.fieldNameIndex(self.attribute.relatedDisplayField)]

            isChecked = False
            for thisFeature in self.tableLayer.selectedFeatures():
                if relatedId == thisFeature[self.tableLayer.fieldNameIndex(self.attribute.relationRelatedIdField)]:
                    isChecked = True
                    values = []

                    for anAttr in self.attribute.attributes:
                        values.append(thisFeature[self.tableLayer.fieldNameIndex(anAttr.name)])

                    break

            if isChecked:
                checkedRelatedValues.append(relatedValue)
                valueDict[relatedValue] = values
            else:
                relatedValues.append(relatedValue)
                valueDict[relatedValue] = defaultValues

        self.relatedLayer.removeSelection()
        self.tableLayer.removeSelection()

        checkedRelatedValues.sort()
        relatedValues.sort()

        for val in checkedRelatedValues:
            self.appendRow(valueDict[val], val,  True)

        for val in relatedValues:
            self.appendRow(valueDict[val], val, False)

    def fillRow(self, thisRow, values, thisValue, checked):
        '''fill thisRow with values from thisFeature'''

        chkItem = QtGui.QTableWidgetItem("")

        if not self.forEdit:
            chkItem.setFlags(QtCore.Qt.NoItemFlags)

        if checked:
            chkItem.setCheckState(QtCore.Qt.Checked)
        else:
            chkItem.setCheckState(QtCore.Qt.Unchecked)

        self.inputWidget.setItem(thisRow, 0, chkItem)

        for i in range(len(values)):
            aValue = values[i]

            if i == self.relationRelatedIdIndex:
                item = QtGui.QTableWidgetItem(thisValue)
                item.id = aValue
                item.setFlags(QtCore.Qt.NoItemFlags)
            else:
                item = QtGui.QTableWidgetItem(unicode(aValue))

            self.inputWidget.setItem(thisRow, i+1, item)

    def appendRow(self, values, thisValue, checked):
        '''add a new row to the QTableWidget'''
        thisRow = self.inputWidget.rowCount() # identical with index of row to be appended as row indices are 0 based
        self.inputWidget.setRowCount(thisRow + 1) # append a row
        self.fillRow(thisRow, values, thisValue, checked)

