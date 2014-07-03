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


from ddui import DdInputWidget,  DdN2mWidget,  DdLineEdit
from dderror import DdError
from qgis.core import *
from PyQt4 import QtCore,  QtGui
from dddialog import DdDialog,  DdSearchDialog

class DdPushButton(DdInputWidget):
    '''abstract class needs subclassing'''

    def __init__(self,  attribute):
        DdInputWidget.__init__(self,  attribute)

    def __str__(self):
        return "<dduserclass.DdPushButton %s>" % str(self.attribute.label)

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

        pParent = parent

        while (True):
            pParent = pParent.parentWidget()

            if isinstance(pParent,  DdDialog) or isinstance(pParent,  DdSearchDialog):
                self.parentDialog = pParent
                break

    def clicked(self):
        QtGui.QMessageBox.information(None,  "",  self.label + " has been clicked")

    def initialize(self,  layer,  feature,  db):
        '''must be implemented in child class'''
        pass

    def save(self,  layer,  feature,  db):
        return False

class DdLineEditSlider(DdLineEdit):
    '''a slider in a QGroupBox used for integer values, needs min and max (defaults to 0 and 10)
    optionally a dict with labels for each slider value can be parsed on initialization'''

    def __init__(self,  attribute,  valueLabels = {}):
        DdLineEdit.__init__(self,  attribute)
        self.valueLabels = valueLabels

    def __str__(self):
        return "<dduserclass.DdLineEditSlider %s>" % str(self.attribute.name)

    def createInputWidget(self,  parent):
        inputWidget = QtGui.QSlider(parent) # defaultInputWidget
        inputWidget.setObjectName("slid" + parent.objectName() + self.attribute.name)
        min = self.attribute.min
        max = self.attribute.max

        # default settings by ddattibute.DdAttribute
        if min <= -32768:
            min = 0

        if max >= 32767:
            max = 10

        inputWidget.setMinimum(min)
        inputWidget.setMaximum(max)
        inputWidget.setOrientation(QtCore.Qt.Horizontal)
        inputWidget.setTickPosition(QtGui.QSlider.TicksAbove)
        inputWidget.setTickInterval(1)
        inputWidget.valueChanged.connect(self.onValueChanged)

        return inputWidget

    def setValue(self,  thisValue):
        '''sets the slider to thisValue'''

        if isinstance(thisValue,  unicode) or isinstance(thisValue,  str):
            try:
                thisValue = int(thisValue)
            except ValueError:
                thisValue = None

        if thisValue == None:
            thisValue = self.attribute.min

        self.inputWidget.setValue(thisValue)
        self.updateLabel(thisValue)

    def setSearchValue(self,  thisValue):
        self.setValue(thisValue)
        self.updateLabel(thisValue)

    def getValue(self):
        if self.chk.isChecked():
            thisValue = None
        else:
            thisValue = self.inputWidget.value()

        return thisValue

    def setupUi(self,  parent,  db):
        '''setup the group box and add it to the parent's formLayout'''
        self.gbx = QtGui.QGroupBox(parent)
        self.gbx.setTitle(self.getLabel())
        self.gbx.setObjectName("gbx" + parent.objectName() + self.attribute.name)
        hLayout = QtGui.QHBoxLayout(self.gbx)
        self.searchCbx = QtGui.QComboBox(self.gbx)
        searchItems = ["=",  "!=", ">",  "<",  ">=",  "<="]

        if not self.attribute.notNull:
            searchItems += ["IS NULL"]

        self.searchCbx.addItems(searchItems)
        hLayout.addWidget(self.searchCbx)
        self.inputWidget = self.createInputWidget(self.gbx)
        self.inputWidget.setToolTip(self.attribute.comment)
        hLayout.addWidget(self.inputWidget)
        self.chk = QtGui.QCheckBox(QtGui.QApplication.translate("DdInfo", "Null", None,
                                                           QtGui.QApplication.UnicodeUTF8),  parent)
        self.chk.setObjectName("chk" + parent.objectName() + self.attribute.name)
        self.chk.setToolTip(QtGui.QApplication.translate("DdInfo", "Check if you want to save an empty (or null) value.", None,
                                                           QtGui.QApplication.UnicodeUTF8))
        self.chk.stateChanged.connect(self.chkStateChanged)
        self.chk.setVisible(not self.attribute.notNull)
        hLayout.addWidget(self.chk)

        parent.layout().addRow(self.gbx)

    def setNull(self,  setnull):
        '''Set this inputWidget to NULL'''
        if setnull:
            thisValue = None
        else:
            if self.attribute.hasDefault:
                thisValue = self.getDefault()
            else:
                thisValue = None

        self.setValue(thisValue)

    def checkMinMax(self,  thisValue):
        '''the slider value is always within min/max range by design'''
        return True

    def onValueChanged(self,  sliderValue):
        '''Slot to be called when the slider value changes'''
        self.registerChange(sliderValue)
        self.updateLabel(sliderValue)

    def updateLabel(self,  thisValue):
        newLabel = self.getLabel()

        if self.chk.isChecked():
            thisValue = None

        if thisValue == None:
            newLabel += ": " + QtGui.QApplication.translate("DdInfo", "Null", None,
                                                           QtGui.QApplication.UnicodeUTF8)
        else:
            try:
                valueLabel = self.valueLabels[thisValue]
            except KeyError:
                valueLabel = str(thisValue)
            newLabel += ": " + valueLabel

        self.gbx.setTitle(newLabel)

class DdN2mCheckableTableWidget(DdN2mWidget):
    '''a table widget for a n2m relation with more than the
    pk fields in the relation table but with checkboxes to assign a value
    to the feature, values to fields in the relation table are assigned
    in the table wiget with doubleClick
    attribute is a DdCheckableTableAttribute
    if the attribute has catalog properties a ComboBox allows to choose
    only from related features being in this catalog'''

    def __init__(self,  attribute):
        DdN2mWidget.__init__(self,  attribute)
        self.catalogCbx = None
        self.catalogLayer = None

    def __str__(self):
        return "<dduserclass.DdN2mCheckableTableWidget %s>" % str(self.attribute.label)

    def hasCatalog(self):
        return (self.attribute.catalogTable != None and self.attribute.relatedCatalogIdField != None and
            self.attribute.catalogIdField != None and self.attribute.catalogDisplayField != None)

    def createInputWidget(self,  parent):
        inputWidget = QtGui.QTableWidget(parent)
        inputWidget.setColumnCount(len(self.attribute.attributes) + 1)
        horizontalHeaders =  [""]

        for anAtt in self.attribute.attributes:
            horizontalHeaders.append(anAtt.getLabel())

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

    def loadAdditionalLayer(self , db,  ddTable):
        layer = self.parentDialog.ddManager.findPostgresLayer(db, ddTable)

        if not layer:
            # load the layer into the project
            layer = self.parentDialog.ddManager.loadPostGISLayer(db,  ddTable)

        return layer

    def initialize(self,  layer,  feature,  db):
        if feature != None:
            self.initializeLayer(layer,  feature,  db,  doShowParents = False,  withMask = True,  skip = [self.attribute.relationRelatedIdField])
            self.relatedLayer = self.loadAdditionalLayer(db,  self.attribute.relatedTable)

            for i in range(len(self.attribute.attributes)):
                anAttr = self.attribute.attributes[i]

                if anAttr.name == self.attribute.relationRelatedIdField:
                    self.relationRelatedIdIndex = i
                    break

            if self.hasCatalog():
                self.catalogLayer = self.loadAdditionalLayer(db,  self.attribute.catalogTable)
                self.fillCatalog()
            else:
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

    def fillCatalog(self):
        '''fill the QComboBox with the catalog values'''
        self.catalogCbx.clear()
        idField = self.catalogLayer.fieldNameIndex(self.attribute.catalogIdField)
        displayField = self.catalogLayer.fieldNameIndex(self.attribute.catalogDisplayField)

        for catalogFeature in self.catalogLayer.getFeatures(QgsFeatureRequest().setFlags(QgsFeatureRequest.NoGeometry)):
            sValue = catalogFeature[displayField]
            keyValue = catalogFeature[idField]
            self.catalogCbx.addItem(sValue, keyValue)

        #sort the comboBox
        model = self.catalogCbx.model()
        proxy = QtGui.QSortFilterProxyModel(self.catalogCbx)
        proxy.setSourceModel(model)
        model.setParent(proxy)
        model.sort(0)

        # add the empty item
        self.catalogCbx.insertItem(0, QtGui.QApplication.translate("DdLabel", "Show all", None,
                                                       QtGui.QApplication.UnicodeUTF8) ,  None)
        self.catalogCbx.setCurrentIndex(0)

    def fill(self,  catalogId = None):
        self.inputWidget.setRowCount(0)
        relatedValues = []
        checkedRelatedValues = []
        valueDict = {}
        defaultValues = self.getDefaultValues()
        subsetString = ""

        if self.hasCatalog():
            if catalogId != None:
                subsetString = "\"" + self.attribute.relatedCatalogIdField + "\" = "+ str(catalogId)

        if self.relatedLayer.setSubsetString(subsetString):
            self.relatedLayer.reload()

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
        passedValues is an array with the related feature id, all values for self.attribute.attributes
        and (optional) the feature of self.table layer to be represented in this row'''

        relatedId = passedValues[0]
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

    def setupUi(self,  parent,  db):
        if self.hasCatalog():
            frame = QtGui.QFrame(parent)
            frame.setFrameShape(QtGui.QFrame.StyledPanel)
            frame.setFrameShadow(QtGui.QFrame.Raised)
            frame.setObjectName("frame" + parent.objectName() + self.attribute.name)
            label = self.createLabel(frame)
            self.inputWidget = self.createInputWidget(frame)
            self.setSizeMax(frame)
            self.inputWidget.setToolTip(self.attribute.comment)
            verticalLayout = QtGui.QVBoxLayout(frame)
            verticalLayout.setObjectName("vlayout" + parent.objectName() + self.attribute.name)
            verticalLayout.addWidget(label)
            formLayout = QtGui.QFormLayout( )
            formLayout.setObjectName("formlayout" + parent.objectName() + self.attribute.name)
            #spacerItem = QtGui.QSpacerItem(40, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
            self.catalogCbx = QtGui.QComboBox(frame)
            self.catalogCbx.setObjectName("cbx" + parent.objectName() + self.attribute.catalogTable.tableName)
            self.catalogCbx.setToolTip(self.attribute.catalogTable.comment)
            #self.catalogCbx.setEditable(True)
            self.catalogCbx.currentIndexChanged.connect(self.catalogChanged)
            cbxLabel = QtGui.QLabel(self.attribute.catalogLabel,  frame)
            cbxLabel.setObjectName("lbl" + parent.objectName() + self.attribute.catalogTable.tableName)
            formLayout.addRow(cbxLabel,  self.catalogCbx)
            verticalLayout.addLayout(formLayout)
            verticalLayout.addWidget(self.inputWidget)
            parent.layout().addRow(frame)
            pParent = parent

            while (True):
                pParent = pParent.parentWidget()

                if isinstance(pParent,  DdDialog) or isinstance(pParent,  DdSearchDialog):
                    self.parentDialog = pParent
                    break
        else:
            DdN2mWidget.setupUi(self,  parent,  db)

    # Slots
    @QtCore.pyqtSlot(int)
    def catalogChanged(self,  thisIndex):
        catalogId = self.catalogCbx.itemData(thisIndex)
        self.fill(catalogId)

    def doubleClick(self,  thisRow,  thisColumn):
        if self.forEdit:
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

                if not self.tableLayer.addFeature(thisFeature):
                    DdError(QtGui.QApplication.translate("DdError", "Could not add feature to layer:", None,
                                           QtGui.QApplication.UnicodeUTF8) + " " + aLayer.name())
                    return None

            result = self.parentDialog.ddManager.showFeatureForm(self.tableLayer,  thisFeature,  \
                showParents = self.attribute.showParents,  title = thisValue,  askForSave = (not doAddFeature))

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
            self.saveChanges()
        else:
            if doAddFeature:
                chkItem.setCheckState(QtCore.Qt.Unchecked)

    def saveChanges(self):
        if not self.tableLayer.commitChanges():
            DdError(QtGui.QApplication.translate("DdError", "Could not save changes for layer:", None,
                                               QtGui.QApplication.UnicodeUTF8) + " " + self.tableLayer.name())
        else:
            self.tableLayer.startEditing()

    def click(self,  thisRow,  thisColumn):
        if thisColumn == 0:
            if self.forEdit:
                chkItem = self.inputWidget.item(thisRow,  0)
                thisFeature = chkItem.feature

                if thisFeature != None: #chkItem.checkState == QtCore.Qt.Checked:
                    chkItem.setCheckState(QtCore.Qt.Unchecked)
                    thisFeature = chkItem.feature
                    self.tableLayer.deleteFeature(thisFeature.id())
                    self.saveChanges()
                    relatedItem = self.inputWidget.item(thisRow,  self.relationRelatedIdIndex + 1)
                    relatedId = relatedItem.id
                    thisValue = relatedItem.text()
                    values = self.getDefaultValues()
                    self.fillRow(thisRow, [relatedId,  values], thisValue)
                else:
                    self.doubleClick(thisRow,  thisColumn)
