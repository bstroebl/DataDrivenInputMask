# -*- coding: utf-8 -*-
"""
userClass
--------
user classes are not instantiated by the plugin but are
to be used in subclasses of DataDrivenUi
"""
from __future__ import absolute_import
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
from builtins import str
from builtins import range
from .ddui import DdInputWidget, DdN2mWidget, DdN2mTableWidget, DdLineEdit, DdComboBox
from .dderror import DdError, DbError
from qgis.core import *
from qgis.PyQt import QtCore, QtSql, QtWidgets
from .dddialog import DdDialog,  DdSearchDialog
from .ddattribute import DdDateLayerAttribute

class DdPushButton(DdInputWidget):
    '''abstract class needs subclassing'''

    def __init__(self,  attribute):
        super().__init__(attribute)

    def __str__(self):
        return "<dduserclass.DdPushButton %s>" % str(self.attribute.name)

    def setupUi(self,  parent,  db):
        self.label = self.getLabel()
        self.inputWidget = QtWidgets.QPushButton(self.label,  parent)
        self.inputWidget.setToolTip(self.attribute.comment)
        self.inputWidget.clicked.connect(self.clicked)
        hLayout = QtWidgets.QHBoxLayout()
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
        QtWidgets.QMessageBox.information(None,  "",  self.label + " has been clicked")

    def initialize(self, layer, feature, db, mode = 0):
        '''must be implemented in child class'''
        pass

    def save(self,  layer,  feature,  db):
        return False

class DdLineEditSlider(DdLineEdit):
    '''a slider in a QGroupBox used for integer values, needs min and max (defaults to 0 and 10)
    optionally a dict with labels for each slider value can be parsed on initialization'''

    def __init__(self,  attribute,  valueLabels = {}):
        super().__init__(attribute)
        self.valueLabels = valueLabels

    def __str__(self):
        return "<dduserclass.DdLineEditSlider %s>" % str(self.attribute.name)

    def createInputWidget(self,  parent):
        inputWidget = QtWidgets.QSlider(parent) # defaultInputWidget
        inputWidget.setObjectName("slid" + parent.objectName() + self.attribute.name)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(inputWidget.sizePolicy().hasHeightForWidth())
        inputWidget.setSizePolicy(sizePolicy)
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
        inputWidget.setTickPosition(QtWidgets.QSlider.TicksAbove)
        inputWidget.setTickInterval(1)
        inputWidget.valueChanged.connect(self.onValueChanged)

        return inputWidget

    def setValue(self,  thisValue):
        '''sets the slider to thisValue'''

        if isinstance(thisValue,  str):
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
        self.gbx = QtWidgets.QGroupBox(parent)
        self.gbx.setTitle(self.getLabel())
        self.gbx.setObjectName("gbx" + parent.objectName() + self.attribute.name)
        hLayout = QtWidgets.QHBoxLayout(self.gbx)
        self.searchCbx = QtWidgets.QComboBox(self.gbx)
        searchItems = ["=",  "!=", ">",  "<",  ">=",  "<="]

        if not self.attribute.notNull:
            searchItems += ["IS NULL"]

        self.searchCbx.addItems(searchItems)
        hLayout.addWidget(self.searchCbx)
        self.inputWidget = self.createInputWidget(self.gbx)
        self.inputWidget.setToolTip(self.attribute.comment)
        hLayout.addWidget(self.inputWidget)
        self.chk = QtWidgets.QCheckBox(QtWidgets.QApplication.translate("DdInfo", "Null"),  parent)
        self.chk.setObjectName("chk" + parent.objectName() + self.attribute.name)
        self.chk.setToolTip(QtWidgets.QApplication.translate("DdInfo",
            "Check if you want to save an empty (or null) value."))
        self.chk.stateChanged.connect(self.chkStateChanged)
        self.chk.setVisible(not self.attribute.notNull)
        hLayout.addWidget(self.chk)
        newRow = parent.layout().rowCount() + 1
        parent.layout().setWidget(newRow, QtWidgets.QFormLayout.SpanningRole, self.gbx)

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
            newLabel += ": " + QtWidgets.QApplication.translate("DdInfo", "Null")
        else:
            try:
                valueLabel = self.valueLabels[thisValue]
            except KeyError:
                valueLabel = str(thisValue)
            newLabel += ": " + valueLabel

        self.gbx.setTitle(newLabel)

class DdN2mCheckableTableWidget(DdN2mTableWidget):
    '''a table widget for a n2m relation with more than the
    pk fields in the relation table but with checkboxes to assign a value
    to the feature, values to fields in the relation table are assigned
    in the table wiget with doubleClick
    attribute is a DdCheckableTableAttribute
    if the attribute has catalog properties a ComboBox allows to choose
    only from related features being in this catalog'''

    def __init__(self,  attribute):
        super().__init__(attribute)
        self.catalogCbx = None
        self.catalogLayer = None
        self.catalogIndex = 0

    def __str__(self):
        return "<dduserclass.DdN2mCheckableTableWidget %s>" % str(self.attribute.name)

    def hasCatalog(self):
        return (self.attribute.catalogTable != None and self.attribute.relatedCatalogIdField != None and
            self.attribute.catalogIdField != None and self.attribute.catalogDisplayField != None)

    def createInputWidget(self,  parent):
        inputWidget = QtWidgets.QTableWidget(parent)
        inputWidget.setColumnCount(len(self.attribute.attributes) + 1)
        horizontalHeaders =  [""]

        for anAtt in self.attribute.attributes:
            horizontalHeaders.append(anAtt.getLabel())

        inputWidget.setHorizontalHeaderLabels(horizontalHeaders)
        inputWidget.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        inputWidget.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        #inputWidget.setEditTriggers(QtWidgets.QAbstractItemView.DoubleClicked)
        inputWidget.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
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

    def initialize(self, layer, feature, db, mode = 0, onlyInitializeN2m = False):
        DdN2mWidget.initialize(self, layer, feature, db, mode)

        if feature != None and not onlyInitializeN2m:
            self.initializeTableLayer(db, doShowParents = False,
                withMask = True, skip = [self.attribute.relationRelatedIdField])
            self.relatedLayer = self.loadAdditionalLayer(db,  self.attribute.relatedTable)
            self.getFkValues(db)

            for i in range(len(self.attribute.attributes)):
                anAttr = self.attribute.attributes[i]

                if anAttr.name == self.attribute.relationRelatedIdField:
                    self.relationRelatedIdIndex = i
                    break

            if self.hasCatalog():
                self.catalogLayer = self.loadAdditionalLayer(db,  self.attribute.catalogTable)
                self.fillCatalog(self.catalogIndex)
            else:
                self.fill()

            for i in range(len(self.columnWidths)):
                thisWidth = self.columnWidths[i]

                if thisWidth != None:
                    self.inputWidget.setColumnWidth(i, thisWidth)

    def getDefaultValues(self):
        defaultValues = []

        for anAttr in self.attribute.attributes:
            if anAttr.hasDefault and not isinstance(anAttr, DdDateLayerAttribute):
                defaultValues.append(anAttr.default)
            else:
                defaultValues.append("NULL")

        return defaultValues

    def fillCatalog(self, initialIndex = 0):
        '''
        fill the QComboBox with the catalog values
        use catalogId as initial value
        '''
        self.catalogCbx.clear()
        idField = self.catalogLayer.fields().lookupField(self.attribute.catalogIdField)
        displayField = self.catalogLayer.fields().lookupField(self.attribute.catalogDisplayField)

        for catalogFeature in self.catalogLayer.getFeatures(QgsFeatureRequest().setFlags(QgsFeatureRequest.NoGeometry)):
            sValue = catalogFeature[displayField]
            keyValue = catalogFeature[idField]
            self.catalogCbx.addItem(sValue, keyValue)

        #sort the comboBox
        model = self.catalogCbx.model()
        proxy = QtCore.QSortFilterProxyModel(self.catalogCbx)
        proxy.setSourceModel(model)
        model.setParent(proxy)
        model.sort(0)

        # add the empty item
        self.catalogCbx.insertItem(0, QtWidgets.QApplication.translate("DdLabel", "Show all") ,  None)
        self.catalogCbx.setCurrentIndex(initialIndex)

    def fill(self,  catalogId = None):
        self.inputWidget.setRowCount(0)
        relatedValues = {}
        checkedRelatedValues = {}
        valueDict = {}
        defaultValues = self.getDefaultValues()
        subsetString = ""
        oldSubsetString = self.relatedLayer.subsetString()

        if self.hasCatalog():
            if catalogId != None:
                subsetString = "\"" + self.attribute.relatedCatalogIdField + "\" = "+ str(catalogId)

        if self.relatedLayer.setSubsetString(subsetString):
            self.relatedLayer.reload()

        self.applySubsetString(False)

        for relatedFeature in self.relatedLayer.getFeatures(
                QgsFeatureRequest().setFlags(
                QgsFeatureRequest.NoGeometry)):
            relatedId = self.getPk(relatedFeature, self.relatedLayer)
            relatedValue = relatedFeature[self.relatedLayer.fields().lookupField(
                self.attribute.relatedDisplayField)]
            isChecked = False

            for thisFeature in self.tableLayer.getFeatures(
                    QgsFeatureRequest().setFlags(
                    QgsFeatureRequest.NoGeometry)):
                if relatedId == thisFeature[self.tableLayer.fields().lookupField(
                        self.attribute.relationRelatedIdField)]:
                    isChecked = True
                    break

            if isChecked:
                checkedRelatedValues[relatedId] = relatedValue
                values = self.getFeatureValues(thisFeature)
                valueDict[relatedId] = [relatedId,  values,  thisFeature]
            else:
                relatedValues[relatedId] = relatedValue
                valueDict[relatedId] = [relatedId, defaultValues]

        self.applySubsetString(True)

        if self.relatedLayer.setSubsetString(oldSubsetString):
            self.relatedLayer.reload()

        for key, val in list(checkedRelatedValues.items()):
            self.appendRow(valueDict[key], val)

        for key, val in list(relatedValues.items()):
            self.appendRow(valueDict[key], val)

    def fillRow(self, thisRow, passedValues, thisValue):
        '''fill thisRow with values
        passedValues is an array with the related feature id, all values for self.attribute.attributes
        and (optional) the feature of self.table layer to be represented in this row'''

        relatedId = passedValues[0]
        values = passedValues[1]
        chkItem = QtWidgets.QTableWidgetItem("")

        if len(passedValues) == 3:
            chkItem.setCheckState(QtCore.Qt.Checked)
            thisFeature = passedValues[2]
            chkItem.feature = thisFeature
        else:
            chkItem.setCheckState(QtCore.Qt.Unchecked)
            chkItem.feature = None

        self.inputWidget.setItem(thisRow, 0, chkItem)

        for i in range(len(values)):
            if i == self.relationRelatedIdIndex:
                item = self.createTableWidgetItem(thisValue)
                item.id = relatedId
            else:
                aValue = values[i]
                item = self.createTableWidgetItem(aValue)

            self.inputWidget.setItem(thisRow, i+1, item)

    def appendRow(self, passedValues, thisValue):
        '''add a new row to the QTableWidget'''
        thisRow = self.inputWidget.rowCount() # identical with index of row to be appended as row indices are 0 based
        self.inputWidget.setRowCount(thisRow + 1) # append a row
        self.fillRow(thisRow, passedValues, thisValue)

    def setupUi(self,  parent,  db):
        if self.hasCatalog():
            frame = QtWidgets.QFrame(parent)
            frame.setFrameShape(QtWidgets.QFrame.StyledPanel)
            frame.setFrameShadow(QtWidgets.QFrame.Raised)
            frame.setObjectName("frame" + parent.objectName() + self.attribute.name)
            label = self.createLabel(frame)
            self.inputWidget = self.createInputWidget(frame)
            self.setSizeMax(frame)
            self.inputWidget.setToolTip(self.attribute.comment)
            verticalLayout = QtWidgets.QVBoxLayout(frame)
            verticalLayout.setObjectName("vlayout" + parent.objectName() + self.attribute.name)
            verticalLayout.addWidget(label)
            formLayout = QtWidgets.QFormLayout( )
            formLayout.setObjectName("formlayout" + parent.objectName() + self.attribute.name)
            #spacerItem = QtWidgets.QSpacerItem(40, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
            self.catalogCbx = QtWidgets.QComboBox(frame)
            self.catalogCbx.setObjectName("cbx" + parent.objectName() + self.attribute.catalogTable.tableName)
            self.catalogCbx.setToolTip(self.attribute.catalogTable.comment)
            #self.catalogCbx.setEditable(True)
            self.catalogCbx.currentIndexChanged.connect(self.catalogChanged)
            cbxLabel = QtWidgets.QLabel(self.attribute.catalogLabel,  frame)
            cbxLabel.setObjectName("lbl" + parent.objectName() + self.attribute.catalogTable.tableName)
            formLayout.addRow(cbxLabel,  self.catalogCbx)
            verticalLayout.addLayout(formLayout)
            verticalLayout.addWidget(self.inputWidget)
            newRow = parent.layout().rowCount() + 1
            parent.layout().setWidget(newRow, QtWidgets.QFormLayout.SpanningRole, frame)
            pParent = parent

            while (True):
                pParent = pParent.parentWidget()

                if isinstance(pParent,  DdDialog) or isinstance(pParent,  DdSearchDialog):
                    self.parentDialog = pParent
                    break
        else:
            DdN2mWidget.setupUi(self, parent, db)

        for i in range(len(self.attribute.attributes)):
            self.columnWidths.append(None)

    # Slots
    @QtCore.pyqtSlot(int)
    def catalogChanged(self,  thisIndex):
        catalogId = self.catalogCbx.itemData(thisIndex)
        self.catalogIndex = thisIndex
        self.fill(catalogId)

    def doubleClick(self,  thisRow,  thisColumn):
        if self.forEdit and self.mode <= 1:
            chkItem = self.inputWidget.item(thisRow,  0)
            thisFeature = chkItem.feature
            relatedItem = self.inputWidget.item(thisRow,
                self.relationRelatedIdIndex + 1)
            relatedId = relatedItem.id
            thisValue = relatedItem.text()
            doAddFeature = False
            relationFeatureIdFieldIdx = self.tableLayer.fields().lookupField(
                self.attribute.relationFeatureIdField)
            relationRelatedIdFieldIdx = self.tableLayer.fields().lookupField(
                    self.attribute.relationRelatedIdField)

            if thisFeature == None:
                doAddFeature = True
                thisFeature = self.createFeature()
                thisFeature[relationFeatureIdFieldIdx] = self.featureId[0]
                thisFeature[relationRelatedIdFieldIdx] = relatedId

                if not self.tableLayer.addFeature(thisFeature):
                    DdError(QtWidgets.QApplication.translate("DdError",
                        "Could not add feature to layer: ") + self.tableLayer.name())
                    return None

            result = self.parentDialog.ddManager.showFeatureForm(
                self.tableLayer, thisFeature, showParents = self.attribute.showParents,
                title = thisValue, askForSave = (not doAddFeature))

            if result == 1: # user clicked OK
                if doAddFeature:
                    chkItem.setCheckState(QtCore.Qt.Checked)
                    # find the feature again
                    for aFeat in self.tableLayer.getFeatures(
                            QgsFeatureRequest().setFlags(QgsFeatureRequest.NoGeometry)):
                        if aFeat[relationFeatureIdFieldIdx] == self.featureId[0] and \
                            aFeat[relationRelatedIdFieldIdx] == relatedId:
                            thisFeature = aFeat
                            break
                # make sure user did not change parentFeatureId
                self.tableLayer.changeAttributeValue(thisFeature.id(),
                    relationFeatureIdFieldIdx, self.featureId[0])
                self.tableLayer.changeAttributeValue(thisFeature.id(),
                    relationRelatedIdFieldIdx, relatedId)
                # refresh thisFeature with the new values
                self.tableLayer.getFeatures(QgsFeatureRequest().setFilterFid(
                    thisFeature.id()).setFlags(QgsFeatureRequest.NoGeometry)).nextFeature(
                    thisFeature)
                values = self.getFeatureValues(thisFeature)
                self.fillRow(thisRow, [relatedId, values, thisFeature], thisValue)
                self.saveChanges()
            else:
                if doAddFeature:
                    chkItem.setCheckState(QtCore.Qt.Unchecked)

    def saveChanges(self):
        if not self.tableLayer.commitChanges():
            DdError(QtWidgets.QApplication.translate("DdError",
                "Could not save changes for layer: ") + self.tableLayer.name())
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

class DdRelatedComboBox(DdComboBox):
    '''
    A ComboBox that is refreshed when another ComboBox has
    a currentIndexChanged event, i.e. the user chooses another
    value.
    listenToCombo: a DdComboBox
    '''

    def __init__(self, attribute, listenToCombo):
        super().__init__(attribute)
        self.listenToCombo = listenToCombo

    def __str__(self):
        return "<dduserclass.DdRelatedComboBox %s>" % str(self.attribute.label)

    def listenToComboChanged(self, newIndex):
        newValue = self.listenToCombo.getValue()
        self.fill(newValue)

    def initialize(self, layer, feature, db, mode = 0):
        self.mode = mode
        if feature == None:
            self.searchCbx.setVisible(False)
            self.manageChk(None)
        else:
            if self.mode == 1: # searchFeature
                self.chk.setChecked(True)
                self.chk.setVisible(True)
                self.chk.setText(QtWidgets.QApplication.translate("DdInfo", "Ignore"))
                self.chk.setToolTip(QtWidgets.QApplication.translate("DdInfo",
                    "Check if you want this field to be ignored in the search."))
                self.searchCbx.setVisible(True)
            else:
                self.listenToCombo.inputWidget.currentIndexChanged.connect(self.listenToComboChanged)
                self.listenToComboChanged(None)
                self.searchCbx.setVisible(False)
                thisValue = self.getFeatureValue(layer, feature)
                self.setValue(thisValue)
                self.manageChk(thisValue)
                self.hasChanges = (feature.id() < 0) # register this change only for new feature

    def readValues(self, db):
        '''read the values to be shown in the QComboBox from the db'''
        self.values == {}
        query = QtSql.QSqlQuery(db)
        query.prepare(self.attribute.queryForCbx)
        query.exec_()

        if query.isActive():

            while query.next(): # returns false when all records are done
                sValue = query.value(0)

                if not isinstance(sValue, str):
                    sValue = str(sValue)

                keyValue = query.value(1)
                listenValue = query.value(2)
                self.values[keyValue] = [sValue, listenValue]
            query.finish()
            return True
        else:
            DbError(query)
            return False

    def prepareCompleter(self, listenId = None):
        '''user can type in comboBox, appropriate values are displayed'''
        if listenId == None:
            DdComboBox.prepareCompleter(self)
        else:
            completerList = []

            for keyValue, valueArray in list(self.values.items()):
                if valueArray[1] == listenId:
                    completerList.append(valueArray[0])

            self.completer = QtWidgets.QCompleter(completerList)
            #values method of dict class
            self.completer.setCaseSensitivity(0)
            self.inputWidget.setCompleter(self.completer)

    def fill(self, listenId = None):
        '''fill the QComboBox with the values'''
        if self.values != {}:
            self.inputWidget.clear()

            if listenId == None:
                DdComboBox.fill(self)
            else:
                for keyValue, valueArray in list(self.values.items()):
                    if valueArray[1] == listenId:
                        sValue = valueArray[0]
                        self.inputWidget.addItem(sValue, keyValue)

                #sort the comboBox
                model = self.inputWidget.model()
                proxy = QtCore.QSortFilterProxyModel(self.inputWidget)
                proxy.setSourceModel(model)
                model.setParent(proxy)
                model.sort(0)
                self.prepareCompleter(listenId)


