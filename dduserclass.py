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
from qgis.core import *
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
        #inputWidget.setEditTriggers(QtGui.QAbstractItemView.DoubleClicked)
        inputWidget.setEditTriggers(QtGui.QAbstractItemView.NoEditTriggers)
        inputWidget.cellDoubleClicked.connect(self.doubleClick)
        inputWidget.cellClicked.connect(self.click)
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

    def getDefaultValues(self):
        defaultValues = []

        for anAttr in self.attribute.attributes:
            if anAttr.hasDefault:
                defaultValues.append(anAttr.default)
            else:
                defaultValues.append("NULL")

        return defaultValues

    def getFeatureValues(self,  thisFeature):
        values = []
        for anAttr in self.attribute.attributes:
            values.append(thisFeature[self.tableLayer.fieldNameIndex(anAttr.name)])

        return values

    def fill(self):
        relatedValues = []
        checkedRelatedValues = []
        valueDict = {}
        defaultValues = self.getDefaultValues()

        for relatedFeature in self.relatedLayer.getFeatures(QgsFeatureRequest().setFlags(QgsFeatureRequest.NoGeometry)):
            relatedId = relatedFeature.id()
            relatedValue = relatedFeature[self.relatedLayer.fieldNameIndex(self.attribute.relatedDisplayField)]
            isChecked = False

            for thisFeature in self.tableLayer.getFeatures(QgsFeatureRequest().setFlags(QgsFeatureRequest.NoGeometry)):
                if relatedId == thisFeature[self.tableLayer.fieldNameIndex(self.attribute.relationRelatedIdField)]:
                    isChecked = True
                    values = self.getFeatureValues(thisFeature)
                    break

            if isChecked:
                checkedRelatedValues.append(relatedValue)
                valueDict[relatedValue] = [relatedId,  values,  thisFeature]
            else:
                relatedValues.append(relatedValue)
                #defaultValues[] = relatedId
                valueDict[relatedValue] = [relatedId, defaultValues]

        checkedRelatedValues.sort()
        relatedValues.sort()

        for val in checkedRelatedValues:
            self.appendRow(valueDict[val], val)

        for val in relatedValues:
            self.appendRow(valueDict[val], val)

    def fillRow(self, thisRow, passedValues, thisValue):
        '''fill thisRow with values
        values is an array with the realted feature id, all values for self.attribute.attributes
        and (optional) the feature of self.table layer to be represented in this row'''

        relatedId = values = passedValues[0]
        values = passedValues[1]
        chkItem = QtGui.QTableWidgetItem("")

        if len(passedValues) == 3:
            chkItem.setCheckState(QtCore.Qt.Checked)
            thisFeature = passedValues[2]
            chkItem.feature = thisFeature
        else:
            chkItem.setCheckState(QtCore.Qt.Unchecked)
            chkItem.feature = None

        self.inputWidget.setItem(thisRow, 0, chkItem)

        for i in range(len(values)):
            aValue = values[i]

            if i == self.relationRelatedIdIndex:
                item = QtGui.QTableWidgetItem(thisValue)
                item.id = relatedId
            else:
                item = QtGui.QTableWidgetItem(unicode(aValue))

            self.inputWidget.setItem(thisRow, i+1, item)

    def appendRow(self, passedValues, thisValue):
        '''add a new row to the QTableWidget'''
        thisRow = self.inputWidget.rowCount() # identical with index of row to be appended as row indices are 0 based
        self.inputWidget.setRowCount(thisRow + 1) # append a row
        self.fillRow(thisRow, passedValues, thisValue)

    # Slots
    def doubleClick(self,  thisRow,  thisColumn):
        chkItem = self.inputWidget.item(thisRow,  0)
        thisFeature = chkItem.feature
        relatedItem = self.inputWidget.item(thisRow,  self.relationRelatedIdIndex + 1)
        relatedId = relatedItem.id
        thisValue = relatedItem.text()
        doAddFeature = False

        if thisFeature == None:
            doAddFeature = True
            thisFeature = self.createFeature()
            thisFeature[self.tableLayer.fieldNameIndex(self.attribute.relationFeatureIdField)] = self.featureId
            thisFeature[self.tableLayer.fieldNameIndex(self.attribute.relationRelatedIdField)] = relatedId

            if not self.tableLayer.addFeature(thisFeature,  False):
                return None

        result = self.parentDialog.ddManager.showFeatureForm(self.tableLayer,  thisFeature,  showParents = self.attribute.showParents,  title = thisValue)

        if result == 1: # user clicked OK
            if doAddFeature:
                chkItem.setCheckState(QtCore.Qt.Checked)
                # find the feature again
                for aFeat in self.tableLayer.getFeatures(QgsFeatureRequest().setFlags(QgsFeatureRequest.NoGeometry)):
                    if aFeat[self.tableLayer.fieldNameIndex(self.attribute.relationFeatureIdField)] == self.featureId and \
                        aFeat[self.tableLayer.fieldNameIndex(self.attribute.relationRelatedIdField)] == relatedId:
                        thisFeature = aFeat
                        break
            # make sure user did not change parentFeatureId
            self.tableLayer.changeAttributeValue(thisFeature.id(),  self.tableLayer.fieldNameIndex(self.attribute.relationFeatureIdField),  self.featureId)
            self.tableLayer.changeAttributeValue(thisFeature.id(),  self.tableLayer.fieldNameIndex(self.attribute.relationRelatedIdField),  relatedId)
            # refresh thisFeature with the new values
            self.tableLayer.getFeatures(QgsFeatureRequest().setFilterFid(thisFeature.id()).setFlags(QgsFeatureRequest.NoGeometry)).nextFeature(thisFeature)
            values = self.getFeatureValues(thisFeature)
            self.fillRow(thisRow,  [relatedId,  values,  thisFeature],  thisValue)
            self.hasChanges = True
        else:
            if doAddFeature:
                self.tableLayer.deleteFeature(thisFeature.id())

    def click(self,  thisRow,  thisColumn):
        if thisColumn == 0:
            chkItem = self.inputWidget.item(thisRow,  0)
            thisFeature = chkItem.feature

            if thisFeature != None: #chkItem.checkState == QtCore.Qt.Checked:
                chkItem.setCheckState(QtCore.Qt.Unchecked)
                thisFeature = chkItem.feature
                self.tableLayer.deleteFeature(thisFeature.id())
                self.hasChanges = True
                relatedItem = self.inputWidget.item(thisRow,  self.relationRelatedIdIndex + 1)
                relatedId = relatedItem.id
                thisValue = relatedItem.text()
                values = self.getDefaultValues()
                self.fillRow(thisRow, [relatedId,  values], thisValue)
            else:
                self.doubleClick(thisRow,  thisColumn)
