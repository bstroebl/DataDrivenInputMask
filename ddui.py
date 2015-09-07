# -*- coding: utf-8 -*-
"""
ddui
--------
Classes that make up or steer the DataDrivenUI
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
from PyQt4 import QtCore,  QtGui,  QtSql
from qgis.core import *
from dderror import DdError,  DbError
from ddattribute import *
from dddialog import DdDialog,  DdSearchDialog
import ddtools
import xml.etree.ElementTree as ET

class DdFormHelper:
    def __init__(self, thisDialog, layerId, featureId):
        app = QgsApplication.instance()
        ddManager = app.ddManager
        lIface = ddManager.iface.legendInterface()

        for aLayer in lIface.layers():
            if aLayer.id() == layerId:
                #QtGui.QMessageBox.information(None,  "", aLayer.name())
                #thisDialog.hide()
                feat = QgsFeature()
                featureFound = aLayer.getFeatures(QgsFeatureRequest().setFilterFid(featureId).setFlags(QgsFeatureRequest.NoGeometry)).nextFeature(feat)

                if featureFound:
                    result = ddManager.showFeatureForm(aLayer,  feat)
                    #QtGui.QMessageBox.information(None,  "", str(thisDialog))
                    thisDialog.setVisible(False)
                    if result == 1:
                        thisDialog.accept()
                    else:
                        thisDialog.reject()
                break

        #self.prntWidget = self.thisDialog.parentWidget()

def ddFormInit1(dialog, layerId, featureId):
    dialog.setProperty("helper", DdFormHelper(dialog, layerId, featureId))

def ddFormInit(dialog, layerId, featureId):
    app = QgsApplication.instance()
    ddManager = app.ddManager
    lIface = ddManager.iface.legendInterface()

    for aLayer in lIface.layers():
        if aLayer.id() == layerId:
            feat = QgsFeature()
            featureFound = aLayer.getFeatures(QgsFeatureRequest().setFilterFid(featureId).setFlags(QgsFeatureRequest.NoGeometry)).nextFeature(feat)

            if featureFound:
                try:
                    layerValues = ddManager.ddLayers[aLayer.id()]
                except KeyError:
                    ddManager.initLayer(aLayer,  skip = [],  labels = {},  fieldOrder = [],  fieldGroups = {},  minMax = {},  noSearchFields = [],  \
                        showParents = True,  createAction = True,  db = None,  inputMask = True,  searchMask = True,  \
                        inputUi = None,  searchUi = None,  helpText = "")
                    layerValues = ddManager.ddLayers[aLayer.id()]

                db = layerValues[1]
                ui = layerValues[2]
                dlg = DdDialog(ddManager,  ui,  aLayer,  feat,  db,  dialog)
                dlg.show()
                result = dlg.exec_()

                if result == 1:
                    layer.setModified()

class DdEventFilter(QtCore.QObject):
    '''Event filter class to be applied to DdLineEdit's input widgets
    throws a signal even when the input widget is not enabled'''
    doubleClicked = QtCore.pyqtSignal()

    def eventFilter(self, watchedObject, event):
        typ = event.type()

        if typ == QtCore.QEvent.MouseButtonDblClick:
            self.doubleClicked.emit()

        return False # if you want to filter the event out, i.e. stop it being handled further, return true; otherwise return false.

class DataDrivenUi(object):
    '''Creates the DataDrivenUi

    When subclassing this class, you want to rewrite createUi and use DdManager's setUi
    method to apply your custom ui to the layer'''

    def __init__(self,  iface):
        self.iface = iface

    def __str__(self):
        return "<ddui.DataDrivenUi>"

    def __debug(self,  title,  str):
        QgsMessageLog.logMessage(title + "\n" + str)

    def configureLayer(self, ddTable, skip, labels, fieldOrder, fieldGroups,
            minMax, noSearchFields, db, createAction, helpText, fieldDisable):
        '''read configuration from db'''

        #check if config tables exist in db
        configOid = ddtools.getOid(DdTable(schemaName = "public",  tableName = "dd_table"), db)

        if configOid != None:
            # read values for this table from config tables
            query = QtSql.QSqlQuery(db)
            sQuery = "SELECT COALESCE(\"table_help\", \'\'), \
                \"table_action\", \
                COALESCE(\"tab_alias\", \'\'), \
                COALESCE(\"tab_tooltip\", \'\'), \
                \"field_name\", \
                COALESCE(\"field_alias\", \'\'), \
                \"field_skip\", \
                \"field_search\", \
                \"field_min\", \
                \"field_max\", \
                COALESCE(\"field_enabled\",true)::varchar \
            FROM \"public\".\"dd_table\" t \
                LEFT JOIN \"public\".\"dd_tab\" tb ON t.id = tb.\"dd_table_id\" \
                LEFT JOIN \"public\".\"dd_field\" f ON tb.id = f.\"dd_tab_id\" \
            WHERE \"table_schema\" = :schema AND \"table_name\" = :table\
            ORDER BY \"tab_order\", \"field_order\""
            query.prepare(sQuery)
            query.bindValue(":schema",  ddTable.schemaName)
            query.bindValue(":table",  ddTable.tableName)
            query.exec_()

            if query.isActive():
                lastTab = None
                firstDataSet = True

                while query.next():
                    if firstDataSet:
                        helpText += query.value(0)
                        firstDataSet = False
                        createAction = query.value(1)

                    tabAlias = query.value(2)
                    tabTooltip = query.value(3)
                    fieldName = query.value(4)
                    fieldAlias = query.value(5)
                    fieldSkip = query.value(6)
                    fieldSearch =  query.value(7)
                    fieldMin = query.value(8)
                    fieldMax = query.value(9)
                    fieldEnable = query.value(10)

                    if tabAlias != lastTab and not fieldSkip:
                        if tabAlias != "":
                            lastTab = tabAlias
                            fieldGroups[fieldName] = [tabAlias,  tabTooltip]

                    fieldOrder.append(fieldName)

                    if fieldAlias != "":
                        labels[fieldName] = fieldAlias

                    if fieldSkip:
                        skip.append(fieldName)

                    if not fieldSearch:
                        noSearchFields.append(fieldName)

                    if fieldMin != None or fieldMax != None:
                        minMax[fieldName] = [fieldMin,  fieldMax]

                    if fieldEnable == "false":
                        if fieldDisable.count(fieldName) == 0:
                            fieldDisable.append(fieldName)
            else:
                DbError(query)

            query.finish()

        return [skip, labels, fieldOrder, fieldGroups, minMax, noSearchFields,
            createAction, helpText, fieldDisable]

    def __createForms(self, thisTable, db, skip, labels, fieldOrder,
            fieldGroups, minMax, noSearchFields, showParents,
            showChildren, readConfigTables, createAction, fieldDisable):
        """create the forms (DdFom instances) shown in the tabs of the Dialog (DdDialog instance)"""

        ddForms = []
        ddSearchForms = []
        ddAttributes = self.getAttributes(
            thisTable, db, labels, minMax, fieldDisable = fieldDisable)
        # do not pass skip here otherwise pk fields might not be included

        for anAtt in ddAttributes:
            if anAtt.isPK:
                n2mAttributes = self.getN2mAttributes(db, thisTable, anAtt.name,
                    anAtt.num, labels, showChildren, skip, fieldDisable)
                ddAttributes = ddAttributes + n2mAttributes

        #check if we need a QToolBox
        needsToolBox = (len(ddAttributes) > 5)

        unorderedAttributes = []
        msg = ""
        # loop through the attributes and get one-line types (QLineEdit, QComboBox) first
        for anAttribute in ddAttributes:
            msg = msg + " " + anAttribute.name

            nextAtt = False
             #check if this attribute is supposed to be skipped
            for skipName in skip:
                if skipName == anAttribute.name:
                    nextAtt = True
                    break

            if nextAtt:
                continue # skip it

            if anAttribute.type == "text" or anAttribute.type == "n2m" or anAttribute.type == "table":
                needsToolBox = True

            unorderedAttributes.append(anAttribute)

        # create an ordered list of attributes
        if len(fieldOrder) > 0:
            orderedAttributes = []

            for aFieldName in fieldOrder:
                counter = 0
                while counter < len(unorderedAttributes):
                    anAttribute = unorderedAttributes.pop()

                    if aFieldName == anAttribute.name:
                        orderedAttributes.append(anAttribute)
                        break
                    else:
                        unorderedAttributes.insert(0,  anAttribute)

                    counter += 1
            # put the rest in
            orderedAttributes.extend(unorderedAttributes)
        else:
            orderedAttributes = unorderedAttributes

        defaultFormWidget = DdFormWidget(thisTable,  needsToolBox)
        defaultSearchFormWidget = DdFormWidget(thisTable,  needsToolBox)

        useFieldGroups = (len(fieldGroups) > 0 and len(fieldOrder) > 0)

        if not useFieldGroups:
            # we only need one form
            ddFormWidget = defaultFormWidget
            ddSearchFormWidget = defaultSearchFormWidget
        else:
            ddFormWidget = None

        for anAttribute in orderedAttributes:
            addToSearch = True

            for key in fieldGroups.iterkeys():
                if key == anAttribute.name:
                    # we need a new form
                    if ddFormWidget != None:
                        # there is one active, add them to the lists
                        ddForms.append(ddFormWidget)
                        ddSearchForms.append(ddSearchFormWidget)

                    tabTitle = fieldGroups[key][0]
                    try:
                        tabToolTip = fieldGroups[key][1]
                    except:
                        tabToolTip = ""

                    aTable = DdTable(thisTable.oid, thisTable.schemaName,  thisTable.tableName,  tabToolTip,  tabTitle)
                    ddFormWidget = DdFormWidget(aTable,  needsToolBox)
                    ddSearchFormWidget = DdFormWidget(aTable,  needsToolBox)
                    break

            if anAttribute.type == "text":
                ddInputWidget = DdTextEdit(anAttribute)
            elif anAttribute.type == "n2m":

                if anAttribute.subType == "list":
                    ddInputWidget = DdN2mListWidget(anAttribute)
                elif anAttribute.subType == "tree":
                    ddInputWidget = DdN2mTreeWidget(anAttribute)
            elif anAttribute.type == "table":
                ddInputWidget = DdN2mTableWidget(anAttribute)
                #addToSearch = False
            else: # one line attributes
                if anAttribute.isFK:
                    ddInputWidget = DdComboBox(anAttribute)
                else:
                    if anAttribute.isTypeFloat():
                        if anAttribute.isArray:
                            ddInputWidget = DdArrayTableWidgetDouble(anAttribute)
                        else:
                            ddInputWidget = DdLineEditDouble(anAttribute)
                    elif anAttribute.isTypeInt():
                        if anAttribute.isArray:
                            ddInputWidget = DdArrayTableWidgetInt(anAttribute)
                        else:
                            ddInputWidget = DdLineEditInt(anAttribute)
                    else:
                        if anAttribute.type == "bool":
                            if anAttribute.isArray:
                                ddInputWidget = DdArrayTableWidgetBool(anAttribute)
                            else:
                                ddInputWidget = DdLineEditBoolean(anAttribute)
                        elif anAttribute.type == "date":
                            if anAttribute.isArray:
                                ddInputWidget = DdArrayTableWidgetDate(anAttribute)
                            else:
                                ddInputWidget = DdDateEdit(anAttribute)
                        elif anAttribute.type == "geometry":
                            ddInputWidget = DdLineEditGeometry(anAttribute)
                            addToSearch = False
                        else:
                            if anAttribute.isArray:
                                ddInputWidget = DdArrayTableWidget(anAttribute)
                            else:
                                if anAttribute.type == "varchar" and anAttribute.length > 256:
                                    ddInputWidget = DdTextEdit(anAttribute)
                                else:
                                    ddInputWidget = DdLineEdit(anAttribute)

            if ddFormWidget == None:
                # fallback in case fieldOrder and fieldGroups do not match
                ddFormWidget = defaultFormWidget
                ddSearchFormWidget = defaultSearchFormWidget

            ddFormWidget.addInputWidget(ddInputWidget)

            if addToSearch:
                if len(noSearchFields) > 0:
                   addToSearch = (noSearchFields.count(anAttribute.name) == 0)

                if addToSearch:
                    ddSearchFormWidget.addInputWidget(ddInputWidget)

        ddForms.append(ddFormWidget)
        ddSearchForms.append(ddSearchFormWidget)

        if showParents:
            # do not show this table in the parent's form
            skip.append(thisTable.tableName)
            # go recursivly into thisTable's parents
            for aParent in self.getParents(thisTable,  db):
                if readConfigTables:
                    pSkip, pLabels, pFieldOrder, pFieldGroups, pMinMax, pNoSearchFields, pCreateAction, pHelpText, pFieldDisable = \
                        self.configureLayer(aParent, [], {}, [], {}, {}, [], db, createAction, "", [])

                    if pSkip == []:
                        pSkip = skip
                    if pLabels == {}:
                        pLabels = labels
                    if pFieldOrder == []:
                        pFieldOrder = fieldOrder
                    if pFieldGroups == {}:
                        pFieldGroups = fieldGroups
                    if pMinMax == {}:
                        pMinMax = minMax
                    if pNoSearchFields == []:
                        pNoSearchFields = noSearchFields
                    if pFieldDisable == []:
                        pFieldDisable = fieldDisable

                parentForms, parentSearchForms = self.__createForms(aParent, db,
                    pSkip, pLabels, pFieldOrder, pFieldGroups, pMinMax,
                    pNoSearchFields, showParents, False, readConfigTables,
                    pCreateAction, pFieldDisable)
                ddForms = ddForms + parentForms
                ddSearchForms = ddSearchForms + parentSearchForms

        return [ddForms,  ddSearchForms]

    def createUi(self,  thisTable,  db,  skip = [],  labels = {},  fieldOrder = [],  fieldGroups = {},  minMax = {},  \
        noSearchFields = [],  showParents = True,  showChildren = True,   inputMask = True,  searchMask = True,  \
        helpText = "",  createAction = True,  readConfigTables = False, fieldDisable = []):
        '''creates default uis for this table (DdTable instance)
        showChildren [Boolean]: show tabs for 1-to-1 relations (children)
        see ddmanager.initLayer for other parameters
        '''

        if readConfigTables:
            skip, labels, fieldOrder, fieldGroups, minMax, noSearchFields, \
            createAction, helpText, fieldDisable = self.configureLayer( \
                thisTable, skip, labels, fieldOrder, fieldGroups, minMax, \
                noSearchFields, db, createAction, \
                helpText, fieldDisable)

        forms, searchForms = self.__createForms(
            thisTable, db, skip, labels, fieldOrder, fieldGroups,
            minMax, noSearchFields, showParents, showChildren,
            readConfigTables, createAction, fieldDisable)

        if  inputMask:
            ui = DdDialogWidget()
            ui.setHelpText(helpText)

            for ddFormWidget in forms:
                ui.addFormWidget(ddFormWidget)
        else:
            ui = None

        if searchMask:
            searchUi = DdDialogWidget()
            for ddFormWidget in searchForms:
                searchUi.addFormWidget(ddFormWidget)
        else:
            searchUi = None

        return [ui, searchUi]

    def getParent(self,  thisTable,  db):
        ''' deprecated'''
        #Problem: eine Tabelle kann mehrere Eltern haben

        query = QtSql.QSqlQuery(db)
        sQuery = "SELECT c.oid, n.nspname, c.relname \
        FROM pg_inherits i \
        JOIN pg_class c ON i.inhparent = c.oid \
        JOIN pg_namespace n ON c.relnamespace = n.oid \
        WHERE i.inhrelid = :oid"
        query.prepare(sQuery)
        query.bindValue(":oid", thisTable.oid)
        query.exec_()

        parentTable = DdTable()

        if query.isActive():
            if query.size() == 0:
                query.finish()
            else:
                while query.next():
                    oid = query.value(0)
                    schema = query.value(1)
                    table = query.value(2)
                    parentTable.oid = oid
                    parentTable.schemaName = schema
                    parentTable.tableName = table
                    break
                query.finish()
        else:
            DbError(query)

        return parentTable

    def getParents(self,  thisTable,  db):
        ''' query the DB to get a table's parents if any
        A table has a parent if its primary key is defined on one field only and is at the same time
        a foreign key to another table's primary key. Thus there is a 1:1
        relationship between the two.'''

        query = QtSql.QSqlQuery(db)
        sQuery = "SELECT \
               c.oid, ns.nspname, c.relname, COALESCE(d.description,'') \
            FROM pg_attribute att \
                JOIN (SELECT * FROM pg_constraint WHERE contype = 'f') fcon ON att.attrelid = fcon.conrelid AND att.attnum = ANY (fcon.conkey) \
                JOIN (SELECT * FROM pg_constraint WHERE contype = 'p') pcon ON att.attrelid = pcon.conrelid AND att.attnum = ANY (pcon.conkey) \
                JOIN pg_class c ON fcon.confrelid = c.oid \
                JOIN pg_namespace ns ON c.relnamespace = ns.oid \
                LEFT JOIN (SELECT * FROM pg_description WHERE objsubid = 0) d ON c.oid = d.objoid \
            WHERE att.attnum > 0 \
                AND att.attisdropped = false \
                AND att.attrelid = :oid \
                AND array_length(pcon.conkey, 1) = 1"
        # AND array_length(pcon.conkey, 1) = 1:
        # if we have a combined PK we are in a n-to-m relational table
        # pg_description.objsubid = 0 for description on tables
        query.prepare(sQuery)
        query.bindValue(":oid", thisTable.oid)
        query.exec_()

        parents = []

        if query.isActive():
            if query.size() == 0:
                query.finish()
            else:
                while query.next():
                    oid = query.value(0)
                    schema = query.value(1)
                    table = query.value(2)
                    comment = query.value(3)
                    parentTable = DdTable(oid,  schema,  table,  comment)
                    parents.append(parentTable)

                query.finish()
        else:
            DbError(query)

        return parents

    def getN2mAttributes(self, db, thisTable, attName, attNum, labels,
            showChildren, skip = [], fieldDisable = []):
        '''find those tables (n2mtable) where our pk is a fk'''

        n2mAttributes = []
        pkQuery = QtSql.QSqlQuery(db)
        sPkQuery = "SELECT array_length(pk.conkey, 1), att.attname, att.attnum, c.oid as table_oid,n.nspname,c.relname, f.numfields, COALESCE(d.description,'') as comment, COALESCE(inpk.in,0) as inpk \
                FROM pg_attribute att \
                JOIN (SELECT * FROM pg_constraint WHERE contype = 'f') fk ON att.attrelid = fk.conrelid AND att.attnum = ANY (fk.conkey) \
                JOIN (SELECT * FROM pg_constraint WHERE contype = 'p') pk ON pk.conrelid = fk.conrelid \
                LEFT JOIN (SELECT 1 AS in, conrelid, conkey FROM pg_constraint where contype = 'p') inpk ON inpk.conrelid = fk.conrelid AND att.attnum = ANY (inpk.conkey) \
                JOIN pg_class c ON fk.conrelid = c.oid \
                JOIN pg_namespace n ON c.relnamespace = n.oid \
                LEFT JOIN pg_description d ON c.oid = d.objoid AND 0 = d.objsubid \
                JOIN(SELECT attrelid, count(attrelid) as numfields \
                     FROM pg_attribute \
                     WHERE attnum > 0 \
                        AND attisdropped = false \
                     GROUP BY attrelid) f ON c.oid = f.attrelid \
                WHERE fk.confrelid = :oid \
                    AND :attNum = ANY(fk.confkey) "
                    #  0 = d.objsubid: comment on table only, not on its columns
        pkQuery.prepare(sPkQuery)
        pkQuery.bindValue(":oid", thisTable.oid)
        pkQuery.bindValue(":attNum", attNum)
        pkQuery.exec_()

        if pkQuery.isActive():
            while pkQuery.next():
                numPkFields = pkQuery.value(0)
                relationFeatureIdField = pkQuery.value(1)
                fkAttNum = pkQuery.value(2) #is the attribute number in n2mtable
                relationOid = pkQuery.value(3)
                relationSchema = pkQuery.value(4)
                relationTable = pkQuery.value(5)
                numFields = pkQuery.value(6)
                relationComment = pkQuery.value(7)
                inPk = bool(pkQuery.value(8))
                ddRelationTable = DdTable(relationOid,  relationSchema,  relationTable)

                if inPk: # either n:m or 1:1
                    if numPkFields == 1: # 1:1 relation

                        if showChildren:
                            # show 1:1 related tables, too
                            subType = "table"
                            maxRows = 1
                            showParents = False
                        else:
                            continue
                    elif numPkFields > 1: # n:m relation
                        if numFields == 2:
                            # get the related table i.e. the table where the other FK field is the PK
                            relatedQuery = QtSql.QSqlQuery(db)
                            sRelatedQuery = "SELECT c.oid, n.nspname, c.relname, att.attname \
                                FROM pg_constraint con \
                                    JOIN pg_class c ON con.confrelid = c.oid \
                                    JOIN pg_namespace n ON c.relnamespace = n.oid \
                                    JOIN (\
                                        SELECT * \
                                        FROM pg_attribute \
                                        WHERE attnum > 0 \
                                            AND attisdropped = false \
                                            AND attnum != :attNum1 \
                                        ) att ON con.conrelid = att.attrelid \
                                WHERE conrelid = :relationOid \
                                    AND contype = 'f' \
                                    AND :attNum2 != ANY(conkey)"
                            # we do not want the table where we came from in the results, therefore :attNum != ANY(confkey)
                            # JOIN pg_class c ON con.confrelid = c.oid -- referenced table
                            # WHERE conrelid = :relationOid -- table this constraint is on
                            # AND contype = 'f' -- foreign key constraint
                            # AND :attNum2 != ANY(conkey) -- list of constrained columns
                            relatedQuery.prepare(sRelatedQuery)
                            relatedQuery.bindValue(":relationOid", relationOid)
                            relatedQuery.bindValue(":attNum1", fkAttNum)
                            relatedQuery.bindValue(":attNum2", fkAttNum)
                            relatedQuery.exec_()

                            if relatedQuery.isActive():

                                if relatedQuery.size() == 0: #no relatedTable but a Table with two PK columns
                                    subType = "table"
                                    maxRows = 1
                                    showParents = False
                                elif relatedQuery.size() == 1:
                                    while relatedQuery.next():
                                        relatedOid = relatedQuery.value(0)
                                        relatedSchema = relatedQuery.value(1)
                                        relatedTable = relatedQuery.value(2)
                                        relationRelatedIdField = relatedQuery.value(3)
                                        ddRelatedTable = DdTable(relatedOid,  relatedSchema,  relatedTable)
                                    relatedQuery.finish()

                                    relatedFieldsQuery = QtSql.QSqlQuery(db)
                                    relatedFieldsQuery.prepare(self.__attributeQuery("att.attnum"))
                                    relatedFieldsQuery.bindValue(":oid", relatedOid)
                                    relatedFieldsQuery.exec_()

                                    if relatedFieldsQuery.isActive():
                                        if relatedFieldsQuery.size() == 2:
                                            subType = "list"
                                        else:
                                            subType = "tree"

                                        relatedIdField = None
                                        relatedDisplayCandidate = None
                                        relatedDisplayField = None
                                        i = 0

                                        fieldList = []

                                        while relatedFieldsQuery.next():
                                            relatedAttName = relatedFieldsQuery.value(0)
                                            relatedAttNum = relatedFieldsQuery.value(1)
                                            relatedAttNotNull = bool(relatedFieldsQuery.value(2))
                                            relatedAttHasDefault = bool(relatedFieldsQuery.value(3))
                                            relatedAttIsChild = bool(relatedFieldsQuery.value(4))
                                            relatedAttLength = relatedFieldsQuery.value(5)
                                            relatedAttTyp = relatedFieldsQuery.value(6)
                                            relatedAttComment = relatedFieldsQuery.value(7)
                                            relatedAttDefault = relatedFieldsQuery.value(8)
                                            relatedAttConstraint = relatedFieldsQuery.value(9)

                                            if relatedAttConstraint == "p": # PK of the related table
                                                relatedIdField = relatedAttName

                                            if relatedAttTyp == "varchar" or relatedAttTyp == "char":

                                                if relatedAttNotNull and not relatedDisplayField: # we use the first one
                                                    relatedDisplayField = relatedAttName

                                                #we display only char attributes
                                                fieldList.append(relatedAttName)

                                        relatedFieldsQuery.finish()

                                        if not relatedDisplayCandidate: # there was no string field
                                            relatedDisplayCandidate = relatedIdField

                                        if not relatedDisplayField: # there was no notNull string field
                                            relatedDisplayField = relatedDisplayCandidate
                                    else:
                                        DbError(relatedFieldsQuery)
                                else:
                                    relatedQuery.finish()
                                    continue
                            else:
                                DbError(relatedQuery)

                        elif numFields > 2:
                            subType = "table"
                            maxRows = None
                            showParents = False
                else: # 1:n relation
                    subType = "table"
                    maxRows = None
                    showParents = True

                try:
                    attLabel = labels[str(relationTable)]
                except KeyError:
                    attLabel = None

                attEnableWidget = fieldDisable.count(ddRelationTable.tableName) == 0

                if subType == "table":
                    configList =  self.configureLayer(
                        ddRelationTable, [], {}, [], {}, {}, [], db, True, "", [])
                    skipThese = configList[0]
                    rLabels = configList[1]
                    rMinMax = configList[4]
                    attributes = self.getAttributes(
                        ddRelationTable, db, rLabels, rMinMax, skipThese)

                    attrsToKeep = []
                    for aRelAtt in attributes:
                        if aRelAtt.type != "geometry":
                            attrsToKeep.append(aRelAtt)

                    ddAtt = DdTableAttribute(
                        ddRelationTable, relationComment, attLabel, relationFeatureIdField,
                        attrsToKeep, maxRows, showParents, attName, attEnableWidget)
                else:
                    relatedForeignKeys = self.getForeignKeys(ddRelatedTable,  db)

                    ddAtt = DdN2mAttribute(
                        ddRelationTable, ddRelatedTable, subType, relationComment,
                        attLabel, relationFeatureIdField, relationRelatedIdField,
                        relatedIdField, relatedDisplayField, fieldList, relatedForeignKeys,
                        attEnableWidget)

                try:
                    skip.index(ddAtt.name)
                    addAtt = False
                except:
                    addAtt = True

                if addAtt:
                    n2mAttributes.append(ddAtt)

            pkQuery.finish()
        else:
            DbError(pkQuery)

        return n2mAttributes

    def getAttributes(self, thisTable, db, labels, minMax, skip = [], fieldDisable = []):
        ''' query the DB and create DdAttributes'''

        ddAttributes = []
        query = QtSql.QSqlQuery(db)
        sQuery = self.__attributeQuery("att.attnum")
        query.prepare(sQuery)
        query.bindValue(":oid", thisTable.oid)
        query.exec_()

        retValue = dict()

        if query.isActive():
            if query.size() == 0:
                query.finish()
            else:
                foreignKeys = self.getForeignKeys(thisTable,  db)

                while query.next():
                    attName = query.value(0)
                    nextResult = False

                    for skipName in skip:
                        if skipName == attName:
                            nextResult = True
                            break

                    if nextResult:
                        continue

                    attNum = query.value(1)
                    attNotNull = query.value(2)
                    attHasDefault = query.value(3)
                    attIsChild = query.value(4)
                    attLength = query.value(5)
                    attTyp = query.value(6)
                    attComment = query.value(7)
                    attDefault = query.value(8)
                    attConstraint = query.value(9)
                    constrainedAttNums = query.value(10)
                    attCategory = query.value(11)
                    arrayDelim = query.value(12)

                    attTyp = attTyp.replace("_", "") # if array type is e.g. _varchar

                    if not self.isSupportedType(attTyp):
                        continue

                    attEnableWidget = fieldDisable.count(attName) == 0
                    isPK = attConstraint == "p" # PrimaryKey
                    isArray = attCategory == "A"

                    if isArray:
                        normalAtt = True
                    else:
                        if isPK:
                            constrainedAttNums = constrainedAttNums.replace("{",  "").replace("}",  "").split(",")
                        else:
                            constrainedAttNums = []

                        if isPK and len(constrainedAttNums) == 1:
                            # if table has a single PK we do not care if it is a FK, too because we
                            # do not treat a parent in a 1:1 relation as lookup table
                            normalAtt = True
                        else:
                            try: # is this attribute a FK
                                fk = foreignKeys[attName]

                                try:
                                    attLabel = labels[str(attName)]
                                except KeyError:
                                    attLabel = attName + " (" + fk[2] + ")"

                                try:
                                    fkComment = fk[3]
                                except IndexError:
                                    fkComment = ""

                                if attComment == "":
                                    attComment = fkComment
                                else:
                                    if not fkComment == "":
                                        attComment = attComment + "\n(" + fkComment + ")"

                                ddAtt = DdFkLayerAttribute(
                                    thisTable, attTyp, attNotNull, attName, attComment,
                                    attNum, isPK, attDefault, attHasDefault, fk[1], attLabel,
                                    attEnableWidget)
                                normalAtt = False
                            except KeyError:
                                # no fk defined
                                normalAtt = True

                    if normalAtt:
                        try:
                            attLabel = labels[str(attName)]
                        except KeyError:
                            attLabel = None

                        try:
                            thisMinMax = minMax[str(attName)]
                        except KeyError:
                            thisMinMax = None

                        if thisMinMax == None:
                            thisMin = None
                            thisMax = None
                        else:
                            thisMin =  thisMinMax[0]
                            thisMax = thisMinMax[1]

                        if attTyp == "date":
                            ddAtt = DdDateLayerAttribute(
                                thisTable, attTyp, attNotNull, attName, attComment, attNum,
                                isPK, False, attDefault, attHasDefault, attLength, attLabel,
                                thisMin, thisMax, enableWidget = attEnableWidget,
                                isArray = isArray, arrayDelim = arrayDelim)
                        elif attTyp == "geometry":
                            ddAtt = DdGeometryAttribute(
                                thisTable, attTyp, attName, attComment, attNum)
                        else:
                            ddAtt = DdLayerAttribute(
                                thisTable, attTyp, attNotNull, attName, attComment, attNum,
                                isPK, False, attDefault, attHasDefault, attLength, attLabel,
                                thisMin, thisMax, attEnableWidget, isArray, arrayDelim)

                    ddAttributes.append(ddAtt)

                query.finish()
        else:
            DbError(query)

        return ddAttributes

    def isSupportedType(self,  typ):
        supportedAttributeTypes = ["int2", "int4", "int8",
            "char", "varchar", "float4", "float8", "text",
            "bool", "date", "geometry"]
        supported = False

        for aTyp in supportedAttributeTypes:
            if aTyp == typ:
                supported = True
                break

        return supported

    def getForeignKeys(self,  thisTable, db):
        '''querys this table's foreign keys and returns a dict
        attnum: [str: Type of the lookup field, str: sql to query lookup values, str: Name of the value field in the lookup table, str: Comment on lookup table]'''
        query = QtSql.QSqlQuery(db)
        sQuery = "SELECT \
                att.attname, \
                t.typname as typ, \
                CAST(valatt.attnotnull as integer) as notnull, \
                valatt.attname, \
                ((((((('SELECT ' || quote_ident(valatt.attname)) || ' as value, ')  || quote_ident(refatt.attname)) || ' as key FROM ') \
                    || quote_ident(ns.nspname)) || '.') || quote_ident(c.relname)) || ' ;' AS sql_key, \
                ((((((('SELECT ' || quote_ident(refatt.attname)) || ' as value, ')  || quote_ident(refatt.attname)) || ' as key FROM ') \
                    || quote_ident(ns.nspname)) || '.') || quote_ident(c.relname)) || ' ;' AS default_sql, \
                COALESCE(d.description, '') as comment, \
                COALESCE(valcon.contype, 'x') as valcontype \
            FROM pg_attribute att \
                JOIN (SELECT * FROM pg_constraint WHERE contype = 'f') con ON att.attrelid = con.conrelid AND att.attnum = ANY (con.conkey) \
                JOIN pg_class c ON con.confrelid = c.oid \
                JOIN pg_namespace ns ON c.relnamespace = ns.oid \
                JOIN pg_attribute refatt ON con.confrelid = refatt.attrelid AND con.confkey[1] = refatt.attnum \
                JOIN pg_attribute valatt ON con.confrelid = valatt.attrelid \
                LEFT JOIN pg_constraint valcon ON valatt.attrelid = valcon.conrelid AND valatt.attnum = ANY (valcon.conkey)\
                JOIN pg_type t ON valatt.atttypid = t.oid \
                LEFT JOIN pg_description d ON con.confrelid = d.objoid AND 0 = d.objsubid \
            WHERE att.attnum > 0 \
                AND att.attisdropped = false \
                AND valatt.attnum > 0 \
                AND valatt.attisdropped = false \
                AND att.attrelid = :oid \
            ORDER BY att.attnum, valatt.attnum"
        # Query returns all fields in the lookup table for each attnum
        # JOIN valcon  in order to not display any fields that are FKs themsselves
        # add "AND valatt.attnum != con.confkey[1]"  if you want to keep PKs out
        query.prepare(sQuery)
        query.bindValue(":oid", thisTable.oid)
        query.exec_()

        foreignKeys = dict()

        if query.isActive():
            while query.next():
                attName = query.value(0)
                fieldType = query.value(1)
                notNull = query.value(2)
                valAttName = query.value(3)
                keySql = query.value(4)
                defaultSql = query.value(5)
                comment = query.value(6)
                contype = query.value(7)

                if contype == "f":
                    continue

                try:
                    fk = foreignKeys[attName]
                    if fk[0] != "varchar": # we do not already have a varchar field as value field
                    # find a field with a suitable type
                        if notNull and (fieldType == "varchar" or fieldType == "char"):
                            foreignKeys[attName] = [fieldType,  keySql,  valAttName,  comment]
                except KeyError:
                    if notNull and (fieldType == "varchar" or fieldType == "char"):
                        foreignKeys[attName] = [fieldType,  keySql,  valAttName,  comment]
                    else: # put the first in
                        foreignKeys[attName] = [fieldType,  defaultSql,  valAttName,  comment]

            query.finish()
        else:
            DbError(query)

        return foreignKeys

    def getOid(self,  thisTable,  db):
        ''' query the DB to get a table's oid'''
        return ddtools.getOid(thisTable,  db)

    def __attributeQuery(self,  order = "lower(att.attname)"):
        sQuery = "SELECT \
        att.attname, \
        att.attnum, \
        CAST(att.attnotnull as integer) as notnull, \
        CAST(att.atthasdef as integer) as hasdef, \
        CASE att.attinhcount WHEN 0 THEN 0 ELSE 1 END as ischild, \
        CASE att.attlen WHEN -1 THEN att.atttypmod -4 ELSE att.attlen END as length, \
        t.typname as typ, \
        COALESCE(d.description, '') as comment, \
        COALESCE(ad.adsrc, '') as default, \
        COALESCE(con.contype, '') as contype, \
        COALESCE(con.conkey, ARRAY[]::smallint[]) as constrained_columns, \
        t.typcategory, \
        t.typdelim \
        FROM pg_attribute att \
        JOIN pg_type t ON att.atttypid = t.oid \
        LEFT JOIN pg_description d ON att.attrelid = d.objoid AND att.attnum = d.objsubid \
        LEFT JOIN pg_attrdef ad ON att.attrelid = ad.adrelid AND att.attnum = ad.adnum \
        LEFT JOIN (SELECT * FROM pg_constraint WHERE contype = \'p\') con ON att.attrelid = con.conrelid AND att.attnum = ANY (con.conkey) \
        WHERE att.attnum > 0 \
        AND att.attisdropped = false \
        AND att.attrelid = :oid \
        ORDER BY " + order
        # contype = \'p\': only primary key constraints are of interest
        # att.attnum > 0 skip system columns
        # att.attisdropped = false -- skip deleted columns
        return sQuery

class DdWidget(object):
    '''abstract base class of all ui-widgets'''

    def __init__(self):
        pass

    def __str__(self):
        return "<ddui.DdWidget>"

    def checkInput(self,  layer,  feature):
        '''check if input is valid
        returns True if not implemented in child class'''
        return True

    def setupUi(self,  parent,  db):
        '''create the ui
        must be implemented in child classes'''
        raise NotImplementedError("Should have implemented setupUi")

    def initialize(self, layer, feature, db, mode = 0):
        '''initialize this widget for feature in layer
        must be implemented in child classes'''
        raise NotImplementedError("Should have implemented initialize")

    def save(self,  layer,  feature,  db):
        '''saves the input
        must be implemented in child classes'''
        raise NotImplementedError("Should have implemented save")

    def discard(self):
        '''discards the input'''
        pass

    def reset(self):
        '''reset anything changed by the DdWidget'''
        pass

    def search(self,  layer):
        '''creates search string
        must be implemented in child classes'''
        raise NotImplementedError("Should have implemented search")

    def createSearch(self,  parentElement):
        '''creates search xml'''
        pass

    def applySearch(self,  parentElement):
        '''read the appropriate parentElement's tag and apply to the widget'''
        pass

    def debug(self,  msg):
        QgsMessageLog.logMessage(msg)

class DdDialogWidget(DdWidget):
    '''This is the mask ui'''
    def __init__(self):
        DdWidget.__init__(self)
        self.forms = []
        self.helpText = ""

    def __str__(self):
        return "<ddui.DdDialogWidget>"

    def setupUi(self,  ddDialog,  db): # ddDialog is a child of QDialog
        ddDialog.setObjectName("DataDrivenInputMask")
        ddDialog.setWindowModality(QtCore.Qt.ApplicationModal)
        self.horizontalLayout = QtGui.QVBoxLayout(ddDialog)
        self.horizontalLayout.setObjectName("DataDrivenInputMask_horizontalLayout")
        self.scrollArea = QtGui.QScrollArea()
        self.scrollArea.setWidgetResizable(True)
        self.scrollArea.setObjectName("DataDrivenInputMask_scrollArea")
        self.horizontalLayout.addWidget(self.scrollArea)
        self.scrollAreaWidgetContents = QtGui.QWidget(ddDialog)
        self.scrollAreaWidgetContents.setObjectName("DataDrivenInputMask_scrollAreaWidgetContents")
        self.scrollAreaLayout = QtGui.QVBoxLayout(self.scrollAreaWidgetContents)
        self.scrollAreaLayout.setObjectName("DataDrivenInputMask_scrollAreaLayout")
        self.mainTab = QtGui.QTabWidget(self.scrollAreaWidgetContents)
        self.mainTab.setObjectName("DataDrivenInputMask_mainTab")

        # remove forms without widgets (e.g. if the form only has one widget
        # and this widget is no search widget but an input widget the form
        # is not shown in the search dialog
        formsToKeep = []

        while len(self.forms) > 0:
            aForm = self.forms.pop()

            if len(aForm.inputWidgets) > 0:
                formsToKeep.append(aForm)

        self.forms = formsToKeep
        self.forms.reverse()

        for i in range(len(self.forms)):
            aTab = QtGui.QWidget(self.mainTab)
            aTab.setObjectName("tab" + str(i))
            aForm = self.forms[i]
            tabLayout = QtGui.QFormLayout(aTab)
            tabLayout.setObjectName("tabLayout" + str(i))
            aForm.setupUi(aTab,  db)

            if aForm.ddTable.title:
                tabTitle = aForm.ddTable.title
            else:
                tabTitle = aForm.ddTable.tableName

            self.mainTab.addTab(aTab,  tabTitle)

            if aForm.ddTable.comment != "":
                aTab.setToolTip(aForm.ddTable.comment)

        self.mainTab.setCurrentIndex(0)
        self.scrollAreaLayout.addWidget(self.mainTab)
        self.scrollArea.setWidget(self.scrollAreaWidgetContents)
        self.buttonBox = QtGui.QDialogButtonBox(ddDialog)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setObjectName("buttonBox")
        self.buttonBox.accepted.connect(ddDialog.accept)
        self.buttonBox.rejected.connect(ddDialog.reject)

        if self.helpText != "":
            self.buttonBox.setStandardButtons(QtGui.QDialogButtonBox.Cancel|QtGui.QDialogButtonBox.Ok|QtGui.QDialogButtonBox.Help)
            self.buttonBox.helpRequested.connect(ddDialog.helpRequested)
        else:
            self.buttonBox.setStandardButtons(QtGui.QDialogButtonBox.Cancel|QtGui.QDialogButtonBox.Ok)

        self.horizontalLayout.addWidget(self.buttonBox)
        QtCore.QMetaObject.connectSlotsByName(ddDialog)

    def setHelpText(self,  helpText):
        self.helpText = helpText

    def addFormWidget(self,  ddFormWidget):
        '''add this DdFormWidget to the ui'''
        self.forms.append(ddFormWidget)

    def addInputWidget(self, inputWidget, ddFormWidgetIndex = None,  beforeWidget = None):
        '''add inputWidget to form with ddFormWidgetIndex beforeWidget (index in form)'''
        if len(self.forms) > 0:
            if isinstance(ddFormWidgetIndex,  int):
                try:
                    ddFormWidget = self.forms[ddFormWidgetIndex]
                except IndexError:
                    ddFormWidget = self.forms[len(self.forms) - 1]

            else:
                ddFormWidget = self.forms[len(self.forms) - 1]

            ddFormWidget.addInputWidget(inputWidget,  beforeWidget)

    def initialize(self, layer, feature, db, mode = 0):
        for aForm in self.forms:
            aForm.initialize(layer, feature, db, mode)

    def checkInput(self,  layer,  feature):
        inputOk = True
        for aForm in self.forms:
            if not aForm.checkInput(layer,  feature):
                inputOk = False
                break

        return inputOk

    def save(self,  layer,  feature,  db):
        hasChanges = False
        layerDict = {} # layerId:[layerObject, doSave]

        for aForm in self.forms:
            doSave = aForm.save(layer,  feature,  db) # check if there is anything to save

            try:
                oldSave = layerDict[aForm.layer.id()][1] # already in, get current save status
            except KeyError:
                oldSave = None

            if oldSave == None: #add to dict
                layerDict[aForm.layer.id()] = [aForm.layer,  doSave]
            elif oldSave == False: # replace with the new value
                layerDict[aForm.layer.id()][1] = doSave

        hasChanges = False

        for aLayerId in layerDict.iterkeys():
            aLayer = layerDict[aLayerId][0]
            doSave = layerDict[aLayerId][1]

            if doSave:
                hasChanges = True
                if not aLayer.commitChanges():
                    DdError(QtGui.QApplication.translate("DdError", "Could not save changes for layer:", None,
                                                       QtGui.QApplication.UnicodeUTF8) + " " + aLayer.name())
            else:
                if not aLayer.rollBack():
                    DdError(QtGui.QApplication.translate("DdError", "Could not discard changes for layer:", None,
                                               QtGui.QApplication.UnicodeUTF8) + " " + aLayer.name())

        layer.startEditing()
        return hasChanges

    def discard(self):
        for aForm in self.forms:
            aForm.discard()

    def search(self,  layer):
        searchSql = ""
        for aForm in self.forms:
            thisSearch = aForm.search(layer)

            if thisSearch != "":
                if searchSql != "":
                    searchSql += " AND "

                searchSql += thisSearch

        return searchSql

    def createSearch(self,  parentElement):
        #parentElement is the XML root element in this case
        for aForm in self.forms:
            aForm.createSearch(parentElement)

    def applySearch(self,  parentElement):
        #parentElement is the XML root element in this case
        for aForm in self.forms:
            aForm.applySearch(parentElement)

class DdFormWidget(DdWidget):
    '''DdForms are the content of DdDialog, each DdDialog needs at least one DdForm (tab).
    The class arranges its input widgets either in a QToolBox or in the DdDialogWidget's current tab
    A form can represent a (parent) layer with the corresponding (parent) feature'''

    def __init__(self,  ddTable, hasToolBox = False,  layer = None):
        DdWidget.__init__(self)
        self.ddTable = ddTable
        self.hasToolBox = hasToolBox
        self.layer = layer
        self.wasEditable = False

        self.feature = None
        self.parent = None
        self.oldSubsetString = ""
        self.inputWidgets = []

    def __str__(self):
        return "<ddui.DdFormWidget>"

    def __getLayer(self,  db):
        # find the layer in the project
        layer = self.parentDialog.ddManager.findPostgresLayer(db,  self.ddTable)

        if not layer:
            # load the layer into the project
            layer = self.parentDialog.ddManager.loadPostGISLayer(db,  self.ddTable)

        return layer

    def __setLayerEditable(self):
        # put layer in edintg mode
        ok = self.layer.isEditable() # is already in editMode

        if not ok:
            # try to start editing
            ok = self.layer.startEditing()

            if not ok:
                DdError(QtGui.QApplication.translate("DdWarning", "Layer cannot be put in editing mode:", None,
                                                           QtGui.QApplication.UnicodeUTF8) + self.layer.name())

        return ok

    def setupUi(self,  parent,  db):
        self.parent = parent
        pParent = self.parent

        while (True):
            # get the DdDialog instance in order to have access to ddManager
            pParent = pParent.parentWidget()

            if isinstance(pParent,  DdDialog) or isinstance(pParent,  DdSearchDialog):
                self.parentDialog = pParent
                break

        for ddInputWidget in self.inputWidgets:
            ddInputWidget.setupUi(parent,  db)

        if self.layer == None: # has not been passed to __init__
            self.layer = self.__getLayer(db)

    def addInputWidget(self,  ddInputWidget,  beforeWidget = None):
        '''insert this DdInputWidget into this DdForm before Widget'''

        if beforeWidget == None or not isinstance(beforeWidget,  int):
            self.inputWidgets.append(ddInputWidget)
        else:
            self.inputWidgets.insert(beforeWidget,  ddInputWidget)

    def initialize(self, layer, feature, db, mode = 0):
        self.mode = mode
        self.oldSubsetString = self.layer.subsetString()
        enableAll = False

        if self.mode == 1: # search feature
            for anInputWidget in self.inputWidgets:
                anInputWidget.initialize(self.layer, feature, db, self.mode)
        else:
            if layer.id() == self.layer.id():
                self.feature = feature
                self.wasEditable = layer.isEditable()
                enableAll = layer.isEditable()
            else:
                layerPkList = layer.pendingPkAttributesList()

                if len(layerPkList) != 1:
                    self.feature = None # no combined keys
                else:
                    layerPkIdx = layerPkList[0]
                    pkValues = []

                    if self.mode == 0:
                        pkValue = feature[layerPkIdx]

                        if pkValue == None:
                            self.feature = None
                        else:
                            pkValues.append(str(pkValue))
                    elif self.mode == 2:
                        for aFeat in layer.selectedFeatures():
                            pkValue = aFeat[layerPkIdx]

                            if pkValue == None:
                                self.feature = None
                                pkValues = []
                                break
                            else:
                                pkValue = str(pkValue)

                            pkValues.append(pkValue)

                    if len(pkValues) > 0:
                        thisPkList = self.layer.pendingPkAttributesList()

                        if len(thisPkList) != 1:
                            self.feature = None
                        else:
                            #self.oldSubsetString = self.layer.subsetString()
                            thisPkField = self.layer.pendingFields().field(thisPkList[0])
                            newSubsetString = "\"" + thisPkField.name() + "\" IN ("

                            for i in range(len(pkValues)):
                                pkValue = pkValues[i]

                                if thisPkField.typeName().find("char") != -1:
                                    pkValue = "\'" + pkValue + "\'" # quote value as string

                                if i == 0:
                                    newSubsetString += pkValue
                                else:
                                    newSubsetString += "," + pkValue

                            newSubsetString += ")"
                            self.layer.setSubsetString(newSubsetString)
                            self.layer.reload()
                            self.layer.selectAll()

                            if self.mode == 0 and self.layer.selectedFeatureCount() != 1:
                                    # there is no or several features matching our feature
                                    self.feature = None
                            elif self.mode == 2 and self.layer.selectedFeatureCount() == 0:
                                    self.feature = None
                            else:
                                self.feature = self.layer.selectedFeatures()[0]

                                if layer.isEditable():
                                    enableAll = self.__setLayerEditable()

                                    if self.mode == 0:
                                        self.layer.removeSelection()

            for anInputWidget in self.inputWidgets:
                anInputWidget.initialize(self.layer, self.feature, db, self.mode)

                if enableAll:
                    anInputWidget.enableAccordingToDdAttribute()
                else: # enable only n2m widgets to make them scrollable
                    if isinstance(anInputWidget,  DdN2mWidget):
                        anInputWidget.enableAccordingToDdAttribute()

            if not self.feature:
                self.parent.setEnabled(False)

    def checkInput(self,  layer,  feature):
        inputOk = True

        if self.parent.isEnabled(): #only check if the tab is enbaled, e.g. parents are not enabled if this is a new feature
            for anInputWidget in self.inputWidgets:
                if not anInputWidget.checkInput(self.layer,  self.feature):
                    inputOk = False
                    break

        return inputOk

    def search(self,  layer):
        searchSql = ""
        parentSql = ""
        if self.parent.isEnabled():
            for anInputWidget in self.inputWidgets:
                thisSearch = anInputWidget.search(self.layer)

                if thisSearch != "":
                    if searchSql != "":
                        searchSql += " AND "

                    searchSql += thisSearch

            if searchSql != "":
                if layer.id() != self.layer.id(): # this is a parent layer
                    layerPkList = layer.pendingPkAttributesList()
                    selfLayerPkList = self.layer.pendingPkAttributesList()

                    if len(layerPkList) == 1 and len(selfLayerPkList) == 1:
                        layerPkName = layer.dataProvider().fields()[layerPkList[0]].name()
                        selfLayerPkName = self.layer.dataProvider().fields()[selfLayerPkList[0]].name()
                        parentSql = "\"" + layerPkName + "\" IN (SELECT \"" + selfLayerPkName + "\" FROM \"" + \
                                            self.ddTable.schemaName + "\".\"" + self.ddTable.tableName + "\" WHERE "

            if parentSql != "":
                searchSql = parentSql + searchSql + ")"

        self.reset()
        return searchSql

    def save(self,  layer,  feature,  db):
        hasChanges = False

        if self.parent.isEnabled():
            for anInputWidget in self.inputWidgets:
                if anInputWidget.save(self.layer,  self.feature,  db):
                    hasChanges = True

        self.reset()
        return hasChanges

    def discard(self):
        if self.parent.isEnabled():
            if self.layer.isEditable():
                for anInputWidget in self.inputWidgets:
                    anInputWidget.discard()
                if not self.layer.rollBack():
                    DdError(QtGui.QApplication.translate("DdError", "Could not discard changes for layer:", None,
                                                   QtGui.QApplication.UnicodeUTF8) + " "+ self.layer.name())
                if self.wasEditable:
                    self.layer.startEditing()

        self.reset()

    def reset(self):
        for anInputWidget in self.inputWidgets:
            anInputWidget.reset()
        # reset previous subset string
        self.layer.setSubsetString(self.oldSubsetString)
        self.layer.reload()

        if self.layer.geometryType() != 4:
            self.parentDialog.ddManager.iface.mapCanvas().refresh()


    def createSearch(self,  parentElement):
        #parentElement is the XML root element in this case
        #check if there is already an element for this table (happens if tabs are used)
        tableElement = None

        for aTableElement in parentElement.findall("table"):
            if aTableElement.get("tableName",  None) == self.ddTable.tableName:
                tableElement = aTableElement
                break

        if tableElement == None: #create it
            tableElement = ET.SubElement(parentElement,  "table")
            tableElement.set("tableName",  self.ddTable.tableName)

        for anInputWidget in self.inputWidgets:
            anInputWidget.createSearch(tableElement)

    def applySearch(self,  parentElement):
        #parentElement is the XML root element in this case
        #check if there is an element for this table
        tableElement = None

        for aTableElement in parentElement.findall("table"):
            if aTableElement.get("tableName",  None) == self.ddTable.tableName:
                tableElement = aTableElement
                break

        if tableElement != None: #create it
            for anInputWidget in self.inputWidgets:
                anInputWidget.applySearch(tableElement)

class DdInputWidget(DdWidget):
    '''abstract super class for any input widget, corresponds to a DdAttribute'''

    def __init__(self,  ddAttribute):
        DdWidget.__init__(self)
        self.attribute = ddAttribute
        self.hasChanges = False
        self.inputWidget = None

    def __str__(self):
        return "<ddui.DdInputWidget %s>" % str(self.attribute.name)

    def setEnabled(self,  enable):
        '''enable the inputWidget'''

        if self.inputWidget != None:
            self.inputWidget.setEnabled(enable)

    def registerChange(self , thisValue):
        '''slot to be called when user changes the input'''

        self.hasChanges = True

    def getLabel(self):
        '''returns the label for this DdInputWidget'''
        labelString = self.attribute.getLabel()

        return labelString

    def createLabel(self,  parent):
        '''creates a QLabel object'''
        labelString = self.getLabel()
        label = QtGui.QLabel(labelString,  parent)
        label.setObjectName("lbl" + parent.objectName() + self.attribute.name)
        label.setToolTip(self.attribute.comment)
        return label

    def getMaxValueFromTable(self,  schemaName,  tableName,  db):
        '''querys schema.table in db to get the highest occuring values for this DdInputWidget's attribute'''
        query = QtSql.QSqlQuery(db)
        query.prepare("SELECT \"" + \
                      self.attribute.name + \
                      "\" FROM \"" + \
                      schemaName + "\".\"" + \
                      tableName + \
                      "\" ORDER BY \"" + self.attribute.name + "\" DESC LIMIT 1;")
        query.exec_()

        if query.isActive():
            if query.first():
                return query.value(0)
            else:
                return 0

            query.finish()

        else:
            DbError(query)

    def enableAccordingToDdAttribute(self):
        self.setEnabled(self.attribute.enableWidget)

class DdLineEdit(DdInputWidget):
    '''abstract class for all Input Widgets that can be represented in one line,
    creates a QLineEdit as default InputWidget, adds it together with a QCheckBox (to store null values)
    and a label to a QFormLayout.'''

    def __init__(self,  attribute):
        DdInputWidget.__init__(self,  attribute)
        self.chk = None
        self.betweenWidget = None
        self.inputWidget = None
        self.mode = 0 # 0 = single feature edit, 1 = search, 2 = multi edi

    def __str__(self):
        return "<ddui.DdOneLineInputWidget %s>" % str(self.attribute.name)

    def getDefault(self):
        '''function to strip quotation marks and data type from default string'''
        thisValue = self.attribute.default
        if True:
            thisValue = thisValue.split("::")[0]

            if thisValue.find("nextval") != -1:
                thisValue = thisValue + ")"
            else:
                thisValue = thisValue.replace("\'",  "")

        return thisValue

    def getFeatureValue(self,  layer,  feature):
        '''returns a str representing the value in this field for this feature;
        if the value is null, None is returned,
        if it is a new feature the default value is returned if available.'''

        if feature == None:
            return None

        if self.mode == 2 and not self.attribute.notNull:
            return None

        fieldIndex = self.getFieldIndex(layer)
        thisValue = feature[fieldIndex]

        if feature.id() < 0 and thisValue == None: # new feature
            if self.mode == 1: # no return value for search feature
                if self.attribute.hasDefault:
                    thisValue = self.getDefault()

        return thisValue

    def createInputWidget(self,  parent):
        inputWidget = QtGui.QLineEdit(parent) # defaultInputWidget
        inputWidget.setObjectName("txl" + parent.objectName() + self.attribute.name)
        inputWidget.textChanged.connect(self.registerChange)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(inputWidget.sizePolicy().hasHeightForWidth())
        inputWidget.setSizePolicy(sizePolicy)
        betweenWidget = QtGui.QLineEdit(parent) # defaultInputWidget
        betweenWidget.setObjectName("txl" + parent.objectName() + self.attribute.name + "between")
        betweenWidget.textChanged.connect(self.registerChange)
        return [inputWidget,  betweenWidget]

    def manageChk(self,  thisValue):
        '''check/uncheck the null checkbox depending on the value and
        the attribute's notNull property'''

        if self.attribute.notNull: # uncheck in order to make inputWidget editable
            self.chk.setChecked(False)
        else:
            self.chk.setChecked(thisValue == None)

    def setValidator(self,  min = None,  max = None):
        '''set a validator, if needed must be implemented in child classes'''
        pass

    # public methods
    def setValue(self,  thisValue):
        '''sets thisValue into the input widget'''

        if thisValue == None:
            thisValue = ""

        self.inputWidget.setText(unicode(thisValue))

    def setSearchValue(self,  thisValue):
        '''sets the search value, diverging implementations in subclasses'''
        self.setValue(thisValue)

    def setBetweenValue(self,  thisValue):
        '''sets thisValue into the betweenWidget'''

        if thisValue == None:
            thisValue = ""

        self.betweenWidget.setText(unicode(thisValue))

    def toString(self,  thisValue):
        return unicode(thisValue)

    def getValue(self):
        if self.chk.isChecked():
            thisValue = None
        else:
            thisValue = self.inputWidget.text()

            if thisValue == "":
                thisValue = None

        return thisValue

    def getBetweenValue(self):
        thisValue = None

        if not self.chk.isChecked():
            if self.betweenWidget != None:
                thisValue = self.betweenWidget.text()

                if thisValue == "":
                    thisValue = None

        return thisValue

    def setupUi(self,  parent,  db):
        '''setup the label and add the inputWidget to parents formLayout'''

        self.label = self.createLabel(parent)
        hLayout = QtGui.QHBoxLayout()
        hLayout.setObjectName(
            "hLayout" + parent.objectName() + self.attribute.name)
        self.searchCbx = QtGui.QComboBox(parent)
        self.searchEventFilter = DdEventFilter(self.searchCbx)
        self.searchCbx.installEventFilter(self.searchEventFilter)
        self.searchEventFilter.doubleClicked.connect(self.onDoubleClick)
        searchItems = ["=",  "!="]

        if not self.attribute.isFK:
            if self.attribute.isTypeChar():
                searchItems += ["IN", "LIKE",  "ILIKE"]
            elif (self.attribute.isTypeInt() or self.attribute.isTypeFloat()):
                searchItems += [ "IN", ">",  "<",  ">=",  "<=",  "BETWEEN...AND..."]
            else:
                if  self.attribute.type == "text":
                    searchItems += ["IN", "LIKE",  "ILIKE"]
                elif  self.attribute.type == "date":
                    searchItems += [ ">",  "<",  ">=",  "<=",  "BETWEEN...AND..."]

        if not self.attribute.notNull:
            searchItems += ["IS NULL",  "IS NOT NULL"]

        self.searchCbx.addItems(searchItems)
        self.searchCbx.currentIndexChanged.connect(self.searchCbxChanged)
        hLayout.addWidget(self.searchCbx)
        inputWidgets = self.createInputWidget(parent)
        self.inputWidget = inputWidgets[0]
        self.eventFilter = DdEventFilter(self.inputWidget)
        self.inputWidget.installEventFilter(self.eventFilter)
        self.eventFilter.doubleClicked.connect(self.onDoubleClick)
        self.betweenWidget = inputWidgets[1]
        self.inputWidget.setToolTip(self.attribute.comment)
        hLayout.addWidget(self.inputWidget)

        if self.betweenWidget != None:
            self.betweenWidget.setVisible(False)
            hLayout.addWidget(self.betweenWidget)

        self.chk = QtGui.QCheckBox(QtGui.QApplication.translate("DdInfo", "Null", None,
                                                           QtGui.QApplication.UnicodeUTF8),  parent)
        self.chk.setObjectName("chk" + parent.objectName() + self.attribute.name)
        self.chk.setToolTip(QtGui.QApplication.translate("DdInfo", "Check if you want to save an empty (or null) value.", None,
                                                           QtGui.QApplication.UnicodeUTF8))
        self.chk.stateChanged.connect(self.chkStateChanged)
        self.chk.setVisible(not self.attribute.notNull)
        hLayout.addWidget(self.chk)
        newRow = parent.layout().rowCount() + 1
        parent.layout().setWidget(newRow, QtGui.QFormLayout.LabelRole, self.label)
        parent.layout().setLayout(newRow, QtGui.QFormLayout.FieldRole, hLayout)

    def setEnabled(self,  enable):
        if self.inputWidget != None:
            if enable:
                self.inputWidget.setEnabled(self.chk.checkState() == QtCore.Qt.Unchecked)
            else:
                self.inputWidget.setEnabled(enable)

            self.chk.setEnabled(enable)

    def setNull(self,  setnull):
        '''Set this inputWidget to NULL'''
        if setnull:
            thisValue = None
        else:
            if self.attribute.hasDefault:
                if self.searchCbx.isVisible():
                    thisValue = ""
                else:
                    thisValue = self.getDefault()
            else:
                thisValue = ""

        self.setValue(thisValue)

        if self.betweenWidget != None:
            self.setBetweenValue(thisValue)

    def initialize(self, layer, feature, db, mode = 0):

        self.mode = mode

        if feature == None:
            self.searchCbx.setVisible(False)
            self.manageChk(None)
        else:
            if self.mode == 1: # searchFeature
                self.chk.setChecked(True)
                self.chk.setVisible(True)
                self.chk.setText(QtGui.QApplication.translate("DdInfo", "Ignore", None,
                                                               QtGui.QApplication.UnicodeUTF8))
                self.chk.setToolTip(QtGui.QApplication.translate("DdInfo", "Check if you want this field to be ignored in the search.", None,
                                                               QtGui.QApplication.UnicodeUTF8))
                self.searchCbx.setVisible(True)
            else:
                self.searchCbx.setVisible(False)
                thisValue = self.getFeatureValue(layer,  feature)
                self.setValue(thisValue)
                self.setValidator(min = thisValue,  max = thisValue)
                # make sure the validator does not kick out an already existing value
                self.manageChk(thisValue)
                self.hasChanges = (feature.id() < 0) # register this change only for new feature

    def validate(self, thisValue, layer, feature, showMsg = True):
        '''checks if value is within min/max range (if defined) and returns the value;
        subclasses can manipulate thisValue in order to make it valid input'''
        accepted = True
        msgShown = False

        if self.hasChanges:
            if thisValue != None:
                if self.attribute.min != None:
                    if thisValue < self.attribute.min:
                        if showMsg:
                            QtGui.QMessageBox.warning(
                                None, self.label.text(),
                                QtGui.QApplication.translate(
                                    "DdWarning", "Field value is too small! Minimum is ",
                                    None, QtGui.QApplication.UnicodeUTF8
                                ) + self.toString(self.attribute.min))
                            msgShown = True
                        accepted = False

                if accepted:
                    if self.attribute.max != None:
                        if thisValue > self.attribute.max:
                            if showMsg:
                                QtGui.QMessageBox.warning(
                                    None, self.label.text(),
                                    QtGui.QApplication.translate(
                                        "DdWarning", "Field value is too large! Maximum is ",
                                        None, QtGui.QApplication.UnicodeUTF8
                                    ) + self.toString(self.attribute.max))
                                msgShown = True
                            accepted = False
            else:
                if not self.chk.isChecked() and self.attribute.hasDefault:
                    thisValue = self.getDefault()

        return [accepted,  msgShown]

    def checkInput(self,  layer,  feature):
        ''' check if current value is an acceptable result '''
        thisValue = self.getValue()

        if self.attribute.notNull and thisValue == None:
            QtGui.QMessageBox.warning(None,
                self.label.text(), QtGui.QApplication.translate(
                    "DdWarning", "Field must not be empty!", None,
                    QtGui.QApplication.UnicodeUTF8) )
            return False
        else:
            if self.getFeatureValue(layer,  feature) == thisValue:
                # not changing a value is always allowed
                return True
            else:
                accepted, msgShown = self.validate(thisValue, layer, feature)

                if not accepted and not msgShown:
                    QtGui.QMessageBox.warning(None,
                        self.label.text(), QtGui.QApplication.translate(
                            "DdWarning", "Input is not valid! Field type is %s", None,
                            QtGui.QApplication.UnicodeUTF8
                        )  % str(self.attribute.type) )

                return accepted

    def getFieldIndex(self,  layer):
        '''return the field index for this DdInputWidget's attribute's name in this layer'''
        if layer:
            fieldIndex = layer.fieldNameIndex(self.attribute.name)
        else:
            fieldIndex = self.attribute.num

        if fieldIndex == -1:
            DdError(QtGui.QApplication.translate(
                    "DdError", "Field not found in layer: ", None,
                    QtGui.QApplication.UnicodeUTF8
                ) + layer.name() + "." + self.attribute.name)
        return fieldIndex

    def save(self,  layer,  feature,  db):
        thisValue = self.getValue()
        fieldIndex = self.getFieldIndex(layer)

        if self.hasChanges:
            if self.mode == 0:
                layer.changeAttributeValue(feature.id(), fieldIndex, thisValue)
            elif self.mode == 2:
                for anId in layer.selectedFeaturesIds():
                    layer.changeAttributeValue(anId, fieldIndex, thisValue)

        return self.hasChanges

    def search(self,  layer):
        '''create search sql-string'''

        searchSql = ""
        thisValue = self.getValue()
        operator = self.searchCbx.currentText()

        if not self.chk.isChecked():
            if operator == "IS NULL" or operator == "IS NOT NULL":
                searchSql += "\"" + self.attribute.name + "\" " + operator
            else:
                if thisValue != None:
                    if (self.attribute.isTypeInt() or self.attribute.isTypeFloat()):
                        thisValue = str(thisValue)
                    elif self.attribute.isTypeChar():
                        thisValue = thisValue.replace("\'", "").strip()

                        if operator == "IN":
                            thisValue = unicode(thisValue)
                        elif operator == "LIKE" or operator == "ILIKE":
                            thisValue = thisValue.replace("*", "%") #get rid of user's wildcard

                            if thisValue.find("%") == -1:
                                thisValue = "%" + thisValue + "%" # add wildcard

                            thisValue = "\'" + unicode(thisValue) + "\'"
                        else:
                            thisValue = "\'" + unicode(thisValue) + "\'"
                    else:
                        if self.attribute.type == "bool":
                            if thisValue:
                                thisValue = "\'t\'"
                            else:
                                thisValue = "\'f\'"
                        elif self.attribute.type == "text":
                            if operator == "IN":
                                thisValue = unicode(thisValue)
                            elif operator == "LIKE" or operator == "ILIKE":
                                thisValue = thisValue.replace("*", "%") #get rid of user's wildcard

                                if thisValue.find("%") == -1:
                                    thisValue = "%" + thisValue + "%" # add wildcard

                                thisValue = "\'" + unicode(thisValue) + "\'"
                            else:
                                thisValue = "\'" + unicode(thisValue) + "\'"
                        elif self.attribute.type == "date":
                            thisValue = "\'" + thisValue.toString("yyyy-MM-dd") + "\'"
                        else:
                            thisValue = self.toString(thisValue)

                    if operator == "IN":
                        inSql = ""
                        for aValue in thisValue.split(","):
                            aValue = aValue.strip()

                            if inSql == "":
                                inSql = "\"" + self.attribute.name + "\" " + operator + " ("
                            else:
                                inSql += ","

                            if self.attribute.isTypeChar():
                                inSql += "\'" + aValue + "\'"
                            else:
                                if self.attribute.type == "text":
                                    inSql += "\'" + aValue + "\'"
                                else:
                                    inSql += aValue

                        searchSql +=  inSql + ")"
                    elif operator == "BETWEEN...AND...":
                        betweenValue = self.getBetweenValue()

                        if betweenValue != None:
                            if (self.attribute.isTypeInt() or self.attribute.isTypeFloat()):
                                betweenValue = str(betweenValue)
                            if self.attribute.type == "date":
                                betweenValue = "\'" + betweenValue.toString("yyyy-MM-dd") + "\'"

                            searchSql += "\"" + self.attribute.name + "\" BETWEEN " + thisValue + " AND " + betweenValue
                        else:
                            operator = ">="
                            searchSql += "\"" + self.attribute.name + "\" " + operator + " " + thisValue
                    else:
                        searchSql += "\"" + self.attribute.name + "\" " + operator + " " + thisValue

        return searchSql

    def createSearch(self,  parentElement):
        '''create the search XML'''
        fieldElement = None

        if not self.chk.isChecked():
            thisValue = self.getValue()
            operator = self.searchCbx.currentText()
            fieldElement = ET.SubElement(parentElement,  "field")
            fieldElement.set("fieldName",  self.attribute.name)
            fieldElement.set("type",  self.attribute.type)
            fieldElement.set("widgetType",  "DdLineEdit")
            operatorElement = ET.SubElement(fieldElement, "operator")
            valueElement = ET.SubElement(fieldElement, "value")

            if operator == "IS NULL" or operator == "IS NOT NULL":
                thisValue = ""
            else:
                if thisValue != None:
                    if (self.attribute.isTypeInt() or self.attribute.isTypeFloat()):
                        thisValue = str(thisValue)
                    elif self.attribute.isTypeChar():
                        thisValue = unicode(thisValue.replace("\'", "").strip())
                    else:
                        if self.attribute.type == "bool":
                            thisValue = str(thisValue)
                        elif self.attribute.type == "text":
                            thisValue = unicode(thisValue.replace("\'", "").strip())
                        elif self.attribute.type == "date":
                            thisValue = thisValue.toString("yyyy-MM-dd")
                        else:
                            thisValue = self.toString(thisValue)

                #if thisValue != "None":
                valueElement.text = thisValue

                if operator == "BETWEEN...AND...":
                    betweenValue = self.getBetweenValue()

                    if betweenValue != None:
                        if (self.attribute.isTypeInt() or self.attribute.isTypeFloat()):
                            betweenValue = str(betweenValue)
                        elif self.attribute.isTypeChar():
                            betweenValue = unicode(betweenValue.replace("\'", "").strip())
                        else:
                            if self.attribute.type == "bool":
                                betweenValue = str(betweenValue)
                            elif self.attribute.type == "text":
                                betweenValue = unicode(betweenValue.replace("\'", "").strip())
                            elif self.attribute.type == "date":
                                betweenValue = betweenValue.toString("yyyy-MM-dd")
                            else:
                                betweenValue = self.toString(betweenValue)

                        betweenElement = ET.SubElement(fieldElement, "bvalue")
                        betweenElement.text = betweenValue
                    else:
                        operator = ">="

            operatorElement.text = operator
        return fieldElement

    def applySearch(self,  parentElement):
        notFound = True
        for fieldElement in parentElement.findall("field"):
            if fieldElement.get("fieldName") == self.attribute.name:
                notFound = False
                operatorElement = fieldElement.find("operator")

                if operatorElement != None:
                    self.chk.setChecked(False)
                    operator = operatorElement.text

                    for i in range(self.searchCbx.count()):
                        if self.searchCbx.itemText( i ) == operator:
                            self.searchCbx.setCurrentIndex( i )
                            break

                    valueElement = fieldElement.find("value")

                    if valueElement != None:
                        value = valueElement.text
                        self.setSearchValue(value)
                        bvalueElement = fieldElement.find("bvalue")

                        if bvalueElement != None:
                            betweenValue = bvalueElement.text
                            self.setBetweenValue(betweenValue)

                break

        if notFound:
            self.chk.setChecked(True)

    #slots
    def chkStateChanged(self,  newState):
        '''slot: disables the input widget if the null checkbox is checked and vice versa'''
        if self.mode == 1:
            self.inputWidget.setEnabled(newState == QtCore.Qt.Unchecked)
        else:
            self.inputWidget.setEnabled(
                newState == QtCore.Qt.Unchecked and self.attribute.enableWidget)

        if self.betweenWidget != None:
            if self.betweenWidget.isVisible():
                self.betweenWidget.setEnabled(newState == QtCore.Qt.Unchecked)

        self.searchCbx.setEnabled(newState == QtCore.Qt.Unchecked)
        self.setNull(newState == QtCore.Qt.Checked)
        self.hasChanges = True

    def searchCbxChanged(self,  thisIndex):
        '''steer visibility of betweenWidget'''
        if self.betweenWidget != None:
            self.betweenWidget.setVisible(self.searchCbx.itemText(thisIndex) == "BETWEEN...AND...")

    def onDoubleClick(self):
        '''slot called when event filter on self.inputWidget throws doubleClick signal'''
        doActivate = self.chk.isChecked() # activate only if currently deactivated

        if self.mode != 1:
            doActivate = self.attribute.enableWidget
            # activate only if enableWidget flag is True (not if in searchMode)

        if doActivate:
            self.chk.setChecked(False)
            self.inputWidget.setFocus()

class DdLineEditInt(DdLineEdit):
    '''input widget (QLineEdit) for an IntegerValue'''

    def __init__(self,  attribute):
        DdLineEdit.__init__(self,  attribute)

    def __str__(self):
        return "<ddui.DdLineEditInt %s>" % str(self.attribute.name)

    def setValue(self,  thisValue):

        if thisValue == None:
            thisValue = ""
        else:
            # convert int to a locale string representation
            if self.mode != 1:
                try:
                    thisInt = int(thisValue)
                    thisValue = self.toString(thisInt)
                except ValueError:
                    if thisValue != self.getDefault():
                        thisValue = ""

        self.inputWidget.setText(thisValue)

    def toString(self,  thisValue):
        loc = QtCore.QLocale.system()
        return loc.toString(thisValue)

    def getFeatureValue(self,  layer,  feature):
        if feature == None:
            return None

        if self.mode == 2 and not self.attribute.notNull:
            return None

        fieldIndex = self.getFieldIndex(layer)
        thisValue = feature[fieldIndex]

        if feature.id() < 0 and (thisValue == None or not isinstance(thisValue,  int)):
            # new feature and no value set or sequence value in its original form
            if self.mode != 1: # no return value for search feature
                if self.attribute.hasDefault:
                    thisValue = self.getDefault()

        return thisValue

    def getValue(self,  noSerial = False):
        if self.chk.isChecked():
            thisValue = None
        else:
            thisValue = self.inputWidget.text()

            if thisValue == "":
                thisValue = None
            else:
                if self.mode == 1:
                    loc = QtCore.QLocale.system()
                else:
                    loc = self.inputWidget.validator().locale()

                intValue,  accepted = loc.toInt(thisValue.replace(loc.groupSeparator(), ""))

                if accepted:
                    thisValue = intValue
                else:
                    if self.mode != 1:
                        if noSerial: # if thisValue is a serial we set it to None
                            thisValue = None

        return thisValue

    def setNull(self,  setnull):
        '''Set this inputWidget to NULL; set only to default if default is an integer'''
        if setnull:
            thisValue = None
        else:
            if self.attribute.hasDefault:
                if self.mode == 1:
                    thisValue = ""
                else:
                    thisValue = self.getDefault()

                    try:
                        thisValue = str(int(thisValue))
                    except ValueError:
                        thisValue = ""
            else:
                thisValue = ""

        self.setValue(thisValue)
        self.setBetweenValue(thisValue)

    def checkDefault(self,  feature):
        accepted = True
        thisValue = self.getDefault()

        try:
            thisValue = int(thisValue)
        except ValueError:
            if feature.id() >= 0: # only sequence values for new features
                thisValue = None
                accepted = False

        return [accepted,  thisValue]

    def save(self,  layer,  feature,  db):
        thisValue = self.getValue(noSerial = True)
        # save None in case of a serial (which is only allowed for new features anyways
        fieldIndex = self.getFieldIndex(layer)

        if self.hasChanges:
            if self.mode == 0:
                layer.changeAttributeValue(feature.id(), fieldIndex, thisValue)
            elif self.mode == 2:
                for anId in layer.selectedFeaturesIds():
                    layer.changeAttributeValue(anId, fieldIndex, thisValue)

        return self.hasChanges

    def validate(self, thisValue, layer, feature, showMsg = True):
        accepted = True
        msgShown = False

        if isinstance(thisValue,  int):
            return DdLineEdit.validate(self, thisValue,  feature,  showMsg)
        else:
            if thisValue == None:
                if not self.chk.isChecked() and self.attribute.hasDefault:
                    accepted,  thisValue = self.checkDefault(feature)
            else:
                loc = self.inputWidget.validator().locale()
                validationState = self.inputWidget.validator().validate(thisValue, 0)[0]

                if validationState == 0: #clearly invalid
                    if self.attribute.hasDefault: # could be a serial
                        if thisValue == self.getDefault(): # unchanged serial => ok
                            accepted,  thisValue = self.checkDefault(feature)
                        else:
                            accepted = False
                    else:
                        accepted = False

                else: #validationState == 1:  intermediate, 2: accepted
                    thisValue,  accepted = loc.toInt(thisValue.replace(loc.groupSeparator(), ""))
                    # replace groupSeparator but not decimalSeparator

                    if accepted:
                        accepted,  msgShown = DdLineEdit.validate(self, thisValue,  feature,  showMsg)

            if accepted:
                self.setValue(thisValue)

            return [accepted,  msgShown]

    def setValidator(self, min = None, max = None):
        '''sets an appropriate QValidator for the QLineEdit
        if this DdInputWidget's attribute has min/max values validator is set to them
        A Python2 int covers PostgreSQL's int2, int4 and int8
        Upon initialization setValidator is called with the current value as min and max'''

        validator = ddtools.getIntValidator(self.inputWidget, self.attribute, min, max)
        self.inputWidget.setValidator(validator)
        self.betweenWidget.setValidator(validator)

class DdLineEditDouble(DdLineEdit):
    '''input widget (QLineEdit) for a DoubleValue'''

    def __init__(self,  attribute):
        DdLineEdit.__init__(self,  attribute)

    def __str__(self):
        return "<ddui.DdLineEditDouble %s>" % str(self.attribute.name)

    def setValue(self,  thisValue):

        if thisValue == None:
            thisValue = ""
        else:
            try:
                thisDouble = float(thisValue)
                thisValue = self.toString(thisDouble)
            except ValueError:
                thisValue = ""

        self.inputWidget.setText(thisValue)

    def setBetweenValue(self,  thisValue):

        if thisValue == None:
            thisValue = ""
        else:
            try:
                thisDouble = float(thisValue)
                thisValue = self.toString(thisDouble)
            except ValueError:
                thisValue = ""

        self.betweenWidget.setText(thisValue)

    def toString(self,  thisValue):
        loc = QtCore.QLocale.system()
        return loc.toString(thisValue)

    def getValue(self):
        if self.chk.isChecked():
            thisValue = None
        else:
            thisValue = self.inputWidget.text()

            if thisValue == "":
                thisValue = None
            else:
                if self.mode == 1:
                    loc = QtCore.QLocale.system()
                else:
                    loc = self.inputWidget.validator().locale()

                thisDouble = loc.toDouble(thisValue.replace(loc.groupSeparator(), ""))

                if thisDouble[1]:
                    thisValue = thisDouble[0]
                else:
                    if self.mode != 1:
                        thisValue = None

        return thisValue

    def getBetweenValue(self):
        if self.chk.isChecked():
            thisValue = None
        else:
            thisValue = self.betweenWidget.text()

            if thisValue == "":
                thisValue = None
            else:
                loc = QtCore.QLocale.system()
                thisDouble = loc.toDouble(thisValue.replace(loc.groupSeparator(), ""))

                if thisDouble[1]:
                    thisValue = thisDouble[0]
                else:
                    if self.mode != 1:
                        thisValue = None

        return thisValue

    def setValidator(self,  min = None,  max = None):
        '''sets an appropriate QValidator for the QLineEdit
        if this DdInputWidget's attribute has min/max values validator is set to them'''

        validator = ddtools.getDoubleValidator(self.inputWidget, self.attribute, min, max)
        self.inputWidget.setValidator(validator)
        self.betweenWidget.setValidator(validator)

    def validate(self, thisValue, layer, feature, showMsg = True):
        accepted = True
        msgShown = False

        if isinstance(thisValue,  float):
            accepted,  msgShown = DdLineEdit.validate(self, thisValue,  feature,  showMsg)
        else:
            accepted = (not self.attribute.notNull and thisValue == None)

        if accepted:
            self.setValue(thisValue)

        return [accepted,  msgShown]

class DdLineEditChar(DdLineEdit):
    '''input widget (QLineEdit) for a char or varchar'''

    def __init__(self,  attribute):
        DdLineEdit.__init__(self,  attribute)

    def __str__(self):
        return "<ddui.DdLineEditChar %s>" % str(self.attribute.name)

    def checkInput(self,  layer,  feature):
        ok = DdLineEdit.checkInput(layer,  feature)

        if ok:
            thisValue = self.getValue()
            size = thisValue.size()

            if size > self.attribute.length:
                QtGui.QMessageBox.warning(None, self.label.text(),  QtGui.QApplication.translate("DdWarning", "Input in Field is too long! ", None,
                                                           QtGui.QApplication.UnicodeUTF8) )
                return False

            if self.attribute.type == "char" and size != self.attribute.length:
                QtGui.QMessageBox.warning(None, self.label.text(),  QtGui.QApplication.translate("DdWarning", "Input in Field is too short!", None,
                                                           QtGui.QApplication.UnicodeUTF8) )
                return False

        return ok

class DdComboBox(DdLineEdit):
    '''input widget (QComboBox) for a foreign key'''

    def __init__(self,  attribute):
        DdLineEdit.__init__(self,  attribute)
        self.values = {}

    def __str__(self):
        return "<ddui.DdComboBox %s>" % str(self.attribute.name)

    def getFeatureValue(self,  layer,  feature):
        '''returns a value representing the value in this field for this feature'''

        if feature == None:
            return None

        if self.mode == 2 and not self.attribute.notNull:
            return None

        fieldIndex = self.getFieldIndex(layer)
        thisValue = feature[fieldIndex] #returns None if empty

        if  feature.id() < 0 and thisValue == None: # new feature and no value set
            if self.mode != 1: # no return value for search feature
                if self.attribute.hasDefault:
                    if self.attribute.isTypeInt():
                        thisValue = int(self.getDefault())
                    elif self.attribute.isTypeChar():
                        thisValue = self.getDefault()

        return thisValue

    def createInputWidget(self,  parent):
        inputWidget = QtGui.QComboBox(parent) # defaultInputWidget
        inputWidget.setObjectName("cbx" + parent.objectName() + self.attribute.name)
        inputWidget.setEditable(True)
        inputWidget.currentIndexChanged.connect(self.registerChange)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(inputWidget.sizePolicy().hasHeightForWidth())
        inputWidget.setSizePolicy(sizePolicy)
        return [inputWidget,  None]

    def readValues(self,  db):
        '''read the values to be shown in the QComboBox from the db'''
        self.values == {}
        query = QtSql.QSqlQuery(db)
        query.prepare(self.attribute.queryForCbx)
        query.exec_()

        if query.isActive():

            while query.next(): # returns false when all records are done
                sValue = query.value(0)

                if not isinstance(sValue,  unicode):
                    sValue = str(sValue)

                keyValue = query.value(1)
                self.values[keyValue] = [sValue]
            query.finish()
            return True
        else:
            DbError(query)
            return False

    def fill(self):
        '''fill the QComboBox with the values'''
        if self.values != {}:
            self.inputWidget.clear()

            for keyValue, valueArray in self.values.iteritems():
                sValue = valueArray[0]
                self.inputWidget.addItem(sValue, keyValue)

            #sort the comboBox
            model = self.inputWidget.model()
            proxy = QtGui.QSortFilterProxyModel(self.inputWidget)
            proxy.setSourceModel(model)
            model.setParent(proxy)
            model.sort(0)

    def prepareCompleter(self):
        '''user can type in comboBox, appropriate values are displayed'''

        completerList = []

        for keyValue, valueArray in self.values.iteritems():
            completerList.append(valueArray[0])

        self.completer = QtGui.QCompleter(completerList)
        #values method of dict class
        self.completer.setCaseSensitivity(0)
        self.inputWidget.setCompleter(self.completer)

    def setNull(self,  setnull):
        thisValue = None

        if setnull:
            self.inputWidget.clear()
        else:
            self.fill()

            if self.attribute.hasDefault:
                if self.attribute.isTypeInt():
                    thisValue = int(self.getDefault())
                elif self.attribute.isTypeChar():
                    thisValue = self.getDefault()

        self.setValue(thisValue)

    def setValue(self,  thisValue):

        if thisValue == None:
            self.inputWidget.setCurrentIndex(0)
        else:
            for i in range(self.inputWidget.count()):
                if self.inputWidget.itemData(i) == thisValue:
                    self.inputWidget.setCurrentIndex(i)
                    break

    def setSearchValue(self,  thisValue):
        '''search value is always type string (because it is stored in xml)
        foreign keys normally are of type int'''

        if self.attribute.isTypeInt():
            try:
                thisValue = int(thisValue)
            except:
                thisValue = None

        self.setValue(thisValue)

    def getValue(self):
        if self.chk.isChecked():
            thisValue = None
        else:
            thisValue = self.inputWidget.itemData(self.inputWidget.currentIndex())

        return thisValue

    def setupUi(self,  parent,  db):
        DdLineEdit.setupUi(self,  parent,  db)
        if self.readValues(db):
            self.fill()
            self.prepareCompleter()

class DdDateEdit(DdLineEdit):
    '''input widget (QDateEdit) for a date field'''

    def __init__(self,  attribute):
        DdLineEdit.__init__(self,  attribute)

    def __str__(self):
        return "<ddui.DdDateEdit %s>" % str(self.attribute.name)

    def setValidator(self,  min = None,  max = None):
        '''set the min and max date if attribute has min/max
        use either the passed values or attributes min/max'''

        if self.attribute.min != None:
            thisMin = self.attribute.min

            if min != None:
                if min < self.attribute.min:
                    thisMin = min

            self.inputWidget.setMinimumDate(thisMin)
            self.betweenWidget.setMinimumDate(thisMin)

        if self.attribute.max != None:
            thisMax = self.attribute.max

            if max != None:
                if max > self.attribute.max:
                    thisMax = max

            self.inputWidget.setMaximumDate(thisMax)
            self.betweenWidget.setMaximumDate(thisMax)

    def getFeatureValue(self,  layer,  feature):
        '''returns a QDate representing the value in this field for this feature'''

        if feature == None:
            return None

        if self.mode == 2 and not self.attribute.notNull:
            return None

        fieldIndex = self.getFieldIndex(layer)
        thisValue = feature[fieldIndex]

        if thisValue == QtCore.QDate():
            thisValue = None

        if thisValue == None:
            if self.mode != 1: # no return value for search feature
                if feature.id() < 0 and self.attribute.hasDefault:
                    thisValue = self.getDefault().toDate()
                else:
                    if self.attribute.notNull:
                        thisValue = QtCore.QDate.currentDate()

        if isinstance(thisValue,  unicode):
            if thisValue.find("now") != -1 or thisValue.find("current_date") != -1:
                thisValue = QtCore.QDate.currentDate()

        return thisValue

    def createInputWidget(self,  parent):
        inputWidget = QtGui.QDateEdit(parent)
        inputWidget.setCalendarPopup(True)
        loc = QtCore.QLocale.system()
        inputWidget.setDisplayFormat(loc.dateFormat())
        inputWidget.setObjectName("dat" + parent.objectName() + self.attribute.name)
        inputWidget.setToolTip(self.attribute.comment)
        inputWidget.dateChanged.connect(self.registerChange)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(inputWidget.sizePolicy().hasHeightForWidth())
        inputWidget.setSizePolicy(sizePolicy)
        betweenWidget = QtGui.QDateEdit(parent)
        betweenWidget.setCalendarPopup(True)
        betweenWidget.setDisplayFormat(loc.dateFormat())
        betweenWidget.setObjectName("dat" + parent.objectName() + self.attribute.name + "between")
        betweenWidget.dateChanged.connect(self.registerChange)
        return [inputWidget,  betweenWidget]

    def setNull(self,  setnull):
        if setnull:
            if self.attribute.max != None:
                thisValue = self.attribute.max
            else:
                thisValue = self.inputWidget.maximumDate()
        else:
            if self.attribute.hasDefault:
                thisValue = self.getDefault()
                thisValue = QtCore.QDate.fromString(thisValue,  self.attribute.dateFormat)
            else:
                thisValue = None

        self.setBetweenValue(thisValue)
        self.setValue(thisValue)

    def setSearchValue(self,  thisValue):
        '''sets the search value'''
        if thisValue != None:
            if isinstance(thisValue,  unicode) or isinstance(thisValue,  str): # this is the case when derived from XML
                newDate = QtCore.QDate.fromString(thisValue,  "yyyy-MM-dd")

                if newDate.isNull():
                    thisValue = None
                else:
                    thisValue = newDate

        self.setValue(thisValue)

    def setBetweenValue(self,  thisValue):
        '''sets the between value'''
        newDate = QtCore.QDate.currentDate()

        if thisValue != None:
            if isinstance(thisValue,  unicode) or isinstance(thisValue,  str): # this is the case when derived from XML
                newDate = QtCore.QDate.fromString(thisValue,  "yyyy-MM-dd")

                if newDate.isNull():
                    newDate = QtCore.QDate.currentDate()

        self.betweenWidget.setDate(newDate)

    def toString(self,  thisValue):
        loc = QtCore.QLocale.system()
        return loc.toString(thisValue)

    def setValue(self,  thisValue):

        if not thisValue: # i.e. None
            newDate = QtCore.QDate.currentDate()
        else:
            newDate = thisValue

        self.inputWidget.setDate(newDate)

    def getValue(self):
        if self.chk.isChecked():
            thisValue = None
        else:
            thisValue = self.inputWidget.date()

        return thisValue

    def getBetweenValue(self):
        if self.chk.isChecked():
            thisValue = None
        else:
            thisValue = self.betweenWidget.date()

        return thisValue

class DdLineEditBoolean(DdLineEdit):
    '''input widget Radio Buttons labeld with yes/no for a boolean field'''

    def __init__(self,  attribute):
        DdLineEdit.__init__(self,  attribute)
        self.inputWidgetYes = None
        self.inputWidgetNo = None

    def __str__(self):
        return "<ddui.DdLineEditBoolean %s>" % str(self.attribute.name)

    def getFeatureValue(self,  layer,  feature):
        '''returns a boolean representing the value in this field for this feature'''

        if feature == None:
            return None

        if self.mode == 2 and not self.attribute.notNull:
            return None

        fieldIndex = self.getFieldIndex(layer)
        thisValue = feature[fieldIndex]

        if thisValue:
            if thisValue == "f" or thisValue == "false" or thisValue == "False":
                thisValue = False
            else:
                thisValue = True

        if feature.id() < 0 and thisValue == None: # new feature and no value set
            if self.mode != 1: # no return value for search feature
                if self.attribute.hasDefault:
                    thisValue = bool(self.getDefault())

        return thisValue

    def createInputWidget(self, parent):
        inputWidget = QtGui.QWidget(parent)
        hLayout = QtGui.QHBoxLayout(inputWidget)
        inputWidget.setObjectName("frm" + parent.objectName() + self.attribute.name)
        self.inputWidgetYes = QtGui.QRadioButton(inputWidget)
        self.inputWidgetYes.setObjectName("radYes" + parent.objectName() + self.attribute.name)
        self.inputWidgetYes.toggled.connect(self.registerChange)
        yesEventFilter = DdEventFilter(self.inputWidgetYes)
        self.inputWidgetYes.installEventFilter(yesEventFilter)
        yesEventFilter.doubleClicked.connect(self.onDoubleClick)
        labelYes = QtGui.QLabel(QtGui.QApplication.translate(
            "DdInput", "Yes", None, QtGui.QApplication.UnicodeUTF8),
            inputWidget)
        labelYes.setObjectName("lblYes" + parent.objectName() + self.attribute.name)
        hLayout.addWidget(labelYes)
        hLayout.addWidget(self.inputWidgetYes)
        self.inputWidgetNo = QtGui.QRadioButton(inputWidget)
        self.inputWidgetNo.setObjectName("radNo" + parent.objectName() + self.attribute.name)
        self.inputWidgetNo.toggled.connect(self.registerChange)
        noEventFilter = DdEventFilter(self.inputWidgetNo)
        self.inputWidgetNo.installEventFilter(noEventFilter)
        noEventFilter.doubleClicked.connect(self.onDoubleClick)
        labelNo = QtGui.QLabel(QtGui.QApplication.translate(
            "DdInput", "No", None, QtGui.QApplication.UnicodeUTF8),
            inputWidget)
        labelNo.setObjectName("lblNo" + parent.objectName() + self.attribute.name)
        hLayout.addWidget(labelNo)
        hLayout.addWidget(self.inputWidgetNo)
        return [inputWidget, None]

    def setupUi(self,  parent,  db):
        '''setup the label and add the inputWidget to parents formLayout'''

        self.label = self.createLabel(parent)
        self.label.setMinimumSize(QtCore.QSize(0, 42))
        hLayout = QtGui.QHBoxLayout()
        hLayout.setObjectName(
            "hLayout" + parent.objectName() + self.attribute.name)
        self.searchCbx = QtGui.QComboBox(parent)
        self.searchEventFilter = DdEventFilter(self.searchCbx)
        self.searchCbx.installEventFilter(self.searchEventFilter)
        self.searchEventFilter.doubleClicked.connect(self.onDoubleClick)
        searchItems = ["=",  "!="]

        if not self.attribute.notNull:
            searchItems += ["IS NULL",  "IS NOT NULL"]

        self.searchCbx.addItems(searchItems)
        self.searchCbx.currentIndexChanged.connect(self.searchCbxChanged)
        hLayout.addWidget(self.searchCbx)
        inputWidgets = self.createInputWidget(parent)
        self.inputWidget = inputWidgets[0]
        self.eventFilter = DdEventFilter(self.inputWidget)
        self.inputWidget.installEventFilter(self.eventFilter)
        self.eventFilter.doubleClicked.connect(self.onDoubleClick)
        self.inputWidget.setToolTip(self.attribute.comment)
        hLayout.addWidget(self.inputWidget)
        self.chk = QtGui.QCheckBox(QtGui.QApplication.translate("DdInfo", "Null", None,
                                                           QtGui.QApplication.UnicodeUTF8),  parent)
        self.chk.setObjectName("chk" + parent.objectName() + self.attribute.name)
        self.chk.setToolTip(QtGui.QApplication.translate("DdInfo", "Check if you want to save an empty (or null) value.", None,
                                                           QtGui.QApplication.UnicodeUTF8))
        self.chk.stateChanged.connect(self.chkStateChanged)
        self.chk.setVisible(not self.attribute.notNull)
        hLayout.addItem(QtGui.QSpacerItem(40, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum))
        hLayout.addWidget(self.chk)
        newRow = parent.layout().rowCount() + 1
        parent.layout().setWidget(newRow, QtGui.QFormLayout.LabelRole, self.label)
        parent.layout().setLayout(newRow, QtGui.QFormLayout.FieldRole, hLayout)

    def setNull(self, setnull):
        '''Set this inputWidget to NULL'''

        thisValue = None
        if not setnull:
            if self.attribute.hasDefault:
                thisValue = self.getDefault()

                if thisValue == "true":
                    thisValue = True
                else:
                    thisValue = False

        self.setValue(thisValue)

    def setValue(self, thisValue):
        if isinstance(thisValue, str): # happens whe read from XML
            if thisValue.upper() == "TRUE":
                thisValue = True
            elif thisValue.upper() == "FALSE":
                thisValue = False
            else:
                thisValue = None

        if None == thisValue: #handle Null values
            self.inputWidgetYes.setChecked(False) # false
            self.inputWidgetNo.setChecked(False) # false
        else:
            self.inputWidgetYes.setChecked(thisValue)
            self.inputWidgetNo.setChecked(not thisValue)

    def getValue(self):
        if self.chk.isChecked():
            thisValue = None
        else:
            thisValue = self.inputWidgetYes.isChecked()

        return thisValue

# class DdCheckBox is deprecated and replaced by DdLineEditBoolean
class DdCheckBox(DdLineEditBoolean):
    '''subclass DdLineEditBoolean to issue a deprecation warning'''
    def __init__(self, attribute):
        from warnings import warn
        warn("The 'DdCheckBox' class was renamed to 'DdLineEditBoolean'",
                      DeprecationWarning)
        DdLineEditBoolean.__init__(self, attribute)

class DdTextEdit(DdLineEdit):
    '''input widget (QTextEdit) for a text field'''

    def __init__(self,  attribute):
        DdLineEdit.__init__(self,  attribute)

    def __str__(self):
        return "<ddui.DdTextEdit %s>" % str(self.attribute.name)

    def registerChange(self):
        self.hasChanges = True

    def createInputWidget(self,  parent):
        inputWidget = QtGui.QPlainTextEdit(parent)
        inputWidget.setTabChangesFocus(True)
        inputWidget.setObjectName("txt" + parent.objectName() + self.attribute.name)
        inputWidget.textChanged.connect(self.registerChange)
        return [inputWidget,  None]

    def setValue(self,  thisValue):

        if thisValue == None:
            thisValue = ""

        self.inputWidget.setPlainText(thisValue)

    def getValue(self):
        if self.chk.isChecked():
            thisValue = None
        else:
            thisValue = self.inputWidget.toPlainText()

            if thisValue == '':
                thisValue = None

        return thisValue

class DdN2mWidget(DdInputWidget):
    '''abstract class for any n-to-m relation'''
    def __init__(self,  attribute):
        DdInputWidget.__init__(self,  attribute)
        self.tableLayer = None
        self.oldSubsetString = ""
        self.featureId = []
        self.forEdit = False

    def setSizeMax(self,  widget):
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(1)
        sizePolicy.setHeightForWidth(widget.sizePolicy().hasHeightForWidth())
        widget.setSizePolicy(sizePolicy)

    def setupUi(self,  parent,  db):
        label = self.createLabel(parent)
        inputWidgets = self.createInputWidget(parent)
        self.inputWidget = inputWidgets[0]
        self.setSizeMax(self.inputWidget)
        self.inputWidget.setToolTip(self.attribute.comment)
        vLayout = QtGui.QVBoxLayout()
        vLayout.setObjectName(
            "vLayout" + parent.objectName() + self.attribute.name)
        vLayout.addWidget(label)
        vLayout.addWidget(self.inputWidget)
        newRow = parent.layout().rowCount() + 1
        parent.layout().setLayout(newRow, QtGui.QFormLayout.SpanningRole, vLayout)
        pParent = parent

        while (True):
            pParent = pParent.parentWidget()

            if isinstance(pParent,  DdDialog) or isinstance(pParent,  DdSearchDialog):
                self.parentDialog = pParent
                break

    #def reset(self):
    #    self.applySubsetString(True)

    def initializeLayer(self,  layer,  feature,  db,  doShowParents = False,  withMask = False,  skip = []):
        # find the layer in the project
        self.tableLayer = self.parentDialog.ddManager.findPostgresLayer(db,  self.attribute.table)

        if not self.tableLayer:
            # load the layer into the project
            self.tableLayer = self.parentDialog.ddManager.loadPostGISLayer(db,  self.attribute.table)

        if withMask:
            # create a DdUi for the layer without the featureIdField it it has not yet been created
            try:
                self.parentDialog.ddManager.ddLayers[self.tableLayer.id()]
            except KeyError:
                skip.append(self.attribute.relationFeatureIdField)
                self.parentDialog.ddManager.initLayer(self.tableLayer,  skip = skip,  \
                                                showParents = doShowParents,  searchMask = True,  \
                                                labels = {},  fieldOrder = [],  fieldGroups = {},  minMax = {},  noSearchFields = [],  \
                                                createAction = True,  db = None,  inputMask = True,   \
                                                inputUi = None,  searchUi = None,  helpText = "") # reinitialize inputMask only

        if self.mode == 2:
            self.featureId = []

            for anId in layer.selectedFeaturesIds():
                self.featureId.append(anId)
        else:
            self.featureId = [feature.id()]

        self.oldSubsetString = self.tableLayer.subsetString()

        if self.mode == 1: #search ui
            self.forEdit = True
        else:
            self.forEdit = self.featureId[0] > 0

            if self.forEdit:
                self.forEdit = layer.isEditable()

                if self.forEdit:
                    self.forEdit = self.tableLayer.isEditable()

                    if not self.forEdit:
                        self.forEdit = self.tableLayer.startEditing()

                        if not self.forEdit:
                            DdError(QtGui.QApplication.translate("DdInfo", "Layer cannot be edited: ", None,
                               QtGui.QApplication.UnicodeUTF8) + self.tableLayer.name(),  showInLog = True)

    def applySubsetString(self,  reset = True):
        if self.tableLayer != None:
            if reset:
                    if self.tableLayer.setSubsetString(self.oldSubsetString):
                        self.tableLayer.reload()
                        return True
            else:
                # reduce the features in self.tableLayer to those related to feature
                subsetString = self.attribute.subsetString + "("

                for i in range(len(self.featureId)):
                    anId = self.featureId[i]

                    if i == 0:
                        subsetString += str(anId)
                    else:
                        subsetString += "," + str(anId)

                subsetString += ")"

                if self.tableLayer.setSubsetString(subsetString):
                    self.tableLayer.reload()
                    return True

        return False

    def createFeature(self, fid = None):
        '''create a new QgsFeature for the relation table with this fid'''
        if fid:
            newFeature = QgsFeature(fid)
        else:
            newFeature = QgsFeature() # gid wird automatisch vergeben

        provider = self.tableLayer.dataProvider()
        fields = self.tableLayer.pendingFields()
        newFeature.initAttributes(fields.count())

        if self.mode != 1:
            for i in range(fields.count()):
                newFeature.setAttribute(i,provider.defaultValue(i))

        return newFeature

    def save(self,  layer,  feature,  db):
        if self.forEdit:
            if self.hasChanges:
                if self.tableLayer.isEditable():
                    if self.tableLayer.isModified():
                        if self.tableLayer.commitChanges():
                            return True
                        else:
                            DdError(QtGui.QApplication.translate("DdError", "Could not save changes for layer:", None,
                                                                       QtGui.QApplication.UnicodeUTF8)  + " " + self.tableLayer.name())
                            self.discard()
                    else:
                        self.discard()
            else:
                self.discard()
        self.reset()
        return False

    def discard(self):
        if self.tableLayer.isEditable():
            if not self.tableLayer.rollBack():
                DdError(QtGui.QApplication.translate("DdError", "Could not discard changes for layer:", None,
                                                   QtGui.QApplication.UnicodeUTF8) + " " + self.tableLayer.name())
                return None

class DdN2mListWidget(DdN2mWidget):
    '''input widget (clickable QListWidget) for simple n2m relations'''

    def __init__(self,  attribute):
        DdN2mWidget.__init__(self,  attribute)

    def __str__(self):
        return "<ddui.DdN2mListWidget %s>" % str(self.attribute.name)

    def registerChange(self,  thisItem):
        if self.forEdit:
            featureIdField = self.tableLayer.fieldNameIndex(self.attribute.relationFeatureIdField)
            relatedIdField = self.tableLayer.fieldNameIndex(self.attribute.relationRelatedIdField)
            itemId = thisItem.id

            if thisItem.checkState() == 2:
                for anId in self.featureId:
                    feat = self.createFeature()
                    feat.setAttribute(featureIdField, anId)
                    feat.setAttribute(relatedIdField, itemId)
                    self.tableLayer.addFeature(feat, False)
            else:
                self.applySubsetString(False)
                self.tableLayer.selectAll()

                for aFeature in self.tableLayer.selectedFeatures():
                    for anId in self.featureId:
                        if aFeature[featureIdField] == anId:
                            if aFeature[relatedIdField] == itemId:
                                idToDelete = aFeature.id()
                                self.tableLayer.deleteFeature(idToDelete)

                self.applySubsetString(True)

            self.hasChanges = True
        else: # do not show any changes
            self.inputWidget.itemChanged.disconnect(self.registerChange)

            if thisItem.checkState() == 2:
                thisItem.setCheckState(0)
            else:
                thisItem.setCheckState(2)

            self.inputWidget.itemChanged.connect(self.registerChange)

    def createInputWidget(self,  parent):
        inputWidget = QtGui.QListWidget(parent) # defaultInputWidget
        inputWidget.setObjectName("lst" + parent.objectName() + self.attribute.name)
        inputWidget.itemChanged.connect(self.registerChange)
        return [inputWidget,  None]

    def initialize(self, layer, feature, db, mode = 0):
        self.mode = mode

        if feature != None:
            self.initializeLayer(layer,  feature,  db)
            query = QtSql.QSqlQuery(db)
            dispStatement = self.attribute.displayStatement

            if self.mode == 2:
                dispStatement = dispStatement.replace("ORDER BY checked DESC,","ORDER BY ")

            query.prepare(dispStatement)
            query.bindValue(":featureId", feature.id())
            query.exec_()

            if query.isActive():
                self.inputWidget.clear()
                self.inputWidget.itemChanged.disconnect(self.registerChange)

                while query.next(): # returns false when all records are done
                    parentId = int(query.value(0))
                    parent = unicode(query.value(1))

                    if self.mode == 2:
                        checked = 0
                    else:
                        checked = int(query.value(2))

                    parentItem = QtGui.QListWidgetItem(parent)
                    parentItem.id = parentId
                    parentItem.setCheckState(checked)
                    self.inputWidget.addItem(parentItem)

                query.finish()
                self.inputWidget.itemChanged.connect(self.registerChange)
            else:
                DbError(query)

    def search(self,  layer):
        searchSql = ""

        if self.hasChanges:
            layerPkList = layer.pendingPkAttributesList()
            ids = ""

            for i in range(self.inputWidget.count()):
                anItem = self.inputWidget.item(i)
                if anItem.checkState() == 2:
                    if ids != "":
                        ids += ","
                    ids += str(anItem.id)

            if len(layerPkList) == 1 and ids != "":
                layerPkName = layer.dataProvider().fields()[layerPkList[0]].name()
                selfLayerPkName = self.attribute.relationFeatureIdField
                searchSql = "\"" + layerPkName + "\" IN (SELECT \"" + selfLayerPkName + "\" FROM \"" + \
                                    self.attribute.table.schemaName + "\".\"" + self.attribute.table.tableName + "\" WHERE \"" + \
                                    self.attribute.relationRelatedIdField + "\" IN (" + ids + "))"

        return searchSql

    def createSearch(self,  parentElement):
        fieldElement = None

        if self.hasChanges:
            fieldElement = ET.SubElement(parentElement,  "field")
            fieldElement.set("fieldName",  self.attribute.name)
            fieldElement.set("type",  self.attribute.type)
            fieldElement.set("widgetType",  "DdN2mListWidget")

            for i in range(self.inputWidget.count()):
                anItem = self.inputWidget.item(i)
                if anItem.checkState() == 2:
                    valueElement = ET.SubElement(fieldElement, "value")
                    valueElement.text = str(anItem.id)

        return fieldElement

    def applySearch(self,  parentElement):
        self.inputWidget.itemChanged.disconnect(self.registerChange)

        for fieldElement in parentElement.findall("field"):
            if fieldElement.get("fieldName") == self.attribute.name:

                for valueElement in fieldElement.findall("value"):
                    thisValue = int(valueElement.text)

                    for i in range(self.inputWidget.count()):
                        anItem = self.inputWidget.item(i)

                        if anItem.id == thisValue:
                            anItem.setCheckState(2)
                            self.hasChanges = True
                            break

        self.inputWidget.itemChanged.connect(self.registerChange)

class DdN2mTreeWidget(DdN2mWidget):
    '''input widget (clickable QTreeWidget) for n2m relations with more than one additional field in the related table
    TreeWidget is initialized directly from the DB'''

    def __init__(self,  attribute):
        DdN2mWidget.__init__(self,  attribute)

    def __str__(self):
        return "<ddui.DdN2mTreeWidget %s>" % str(self.attribute.name)

    def registerChange(self,  thisItem,  thisColumn):
        if thisColumn == 0:
            if self.forEdit:
                featureIdField = self.tableLayer.fieldNameIndex(self.attribute.relationFeatureIdField)
                relatedIdField = self.tableLayer.fieldNameIndex(self.attribute.relationRelatedIdField)
                itemId = thisItem.id

                if thisItem.checkState(0) == 2:
                    for anId in self.featureId:
                        feat = self.createFeature()
                        feat.setAttribute(featureIdField, anId)
                        feat.setAttribute(relatedIdField, itemId)
                        self.tableLayer.addFeature(feat, False)
                else:
                    self.applySubsetString(False)
                    self.tableLayer.selectAll()

                    for aFeature in self.tableLayer.selectedFeatures():
                        for anId in self.featureId:
                            if aFeature[featureIdField] == anId:
                                if aFeature[relatedIdField] == itemId:
                                    idToDelete = aFeature.id()
                                    self.tableLayer.deleteFeature(idToDelete)

                    self.applySubsetString(True)
                self.hasChanges = True
            else: # do not show any changes
                self.inputWidget.itemChanged.disconnect(self.registerChange)

                if thisItem.checkState(0) == 2:
                    thisItem.setCheckState(0,  0)
                else:
                    thisItem.setCheckState(0,  2)

                self.inputWidget.itemChanged.connect(self.registerChange)

    def createInputWidget(self,  parent):
        inputWidget = QtGui.QTreeWidget(parent)
        inputWidget.setEditTriggers(QtGui.QAbstractItemView.NoEditTriggers)
        inputWidget.setHeaderHidden(True)
        inputWidget.setColumnCount(1)
        inputWidget.setObjectName("tre" + parent.objectName() + self.attribute.name)
        inputWidget.itemChanged.connect(self.registerChange)
        return [inputWidget,  None]

    def initialize(self, layer, feature, db, mode = 0):
        self.mode = mode

        if feature != None:
            self.initializeLayer(layer,  feature,  db)
            query = QtSql.QSqlQuery(db)
            dispStatement = self.attribute.displayStatement

            if self.mode == 2:
                dispStatement = dispStatement.replace("ORDER BY checked DESC,","ORDER BY ")

            query.prepare(dispStatement)
            query.bindValue(":featureId", feature.id())
            query.exec_()
            self.debug(query.lastQuery())
            if query.isActive():
                self.inputWidget.clear()
                self.inputWidget.itemChanged.disconnect(self.registerChange)

                while query.next(): # returns false when all records are done
                    parentId = int(query.value(0))
                    parent = unicode(query.value(1))

                    if self.mode == 2:
                        checked = 0
                    else:
                        checked = int(query.value(2))

                    parentItem = QtGui.QTreeWidgetItem(self.inputWidget)
                    parentItem.id = parentId
                    parentItem.setCheckState(0,  checked)
                    parentItem.setText(0,  parent)

                    self.debug(str(self.attribute.fieldList))
                    for i in range(len(self.attribute.fieldList) -1):
                        val = query.value(i + 3)

                        if val != None:
                            childItem = QtGui.QTreeWidgetItem(parentItem)
                            childItem.setText(0,  val)
                            parentItem.addChild(childItem)
                        else: # no more fields left
                            break

                    parentItem.setExpanded(False)
                    self.inputWidget.addTopLevelItem(parentItem)
                query.finish()
                self.inputWidget.itemChanged.connect(self.registerChange)
            else:
                DbError(query)

    def search(self,  layer):
        searchSql = ""

        if self.hasChanges:
            layerPkList = layer.pendingPkAttributesList()
            ids = ""

            for i in range(self.inputWidget.topLevelItemCount() -1):
                anItem = self.inputWidget.topLevelItem(i)
                if anItem.checkState(0) == 2:
                    if ids != "":
                        ids += ","
                    ids += str(anItem.id)

            if len(layerPkList) == 1 and ids != "":
                layerPkName = layer.dataProvider().fields()[layerPkList[0]].name()
                selfLayerPkName = self.attribute.relationFeatureIdField
                searchSql = "\"" + layerPkName + "\" IN (SELECT \"" + selfLayerPkName + "\" FROM \"" + \
                                    self.attribute.table.schemaName + "\".\"" + self.attribute.table.tableName + "\" WHERE \"" + \
                                    self.attribute.relationRelatedIdField + "\" IN (" + ids + "))"

        return searchSql

    def createSearch(self,  parentElement):
        fieldElement = None

        if self.hasChanges:
            fieldElement = ET.SubElement(parentElement,  "field")
            fieldElement.set("fieldName",  self.attribute.name)
            fieldElement.set("type",  self.attribute.type)
            fieldElement.set("widgetType",  "DdN2mTreeWidget")

            for i in range(self.inputWidget.topLevelItemCount() -1):
                anItem = self.inputWidget.topLevelItem(i)

                if anItem.checkState(0) == 2:
                    ET.SubElement(fieldElement, "value").text = str(anItem.id)

        return fieldElement

    def applySearch(self,  parentElement):
        self.inputWidget.itemChanged.disconnect(self.registerChange)

        for fieldElement in parentElement.findall("field"):
            if fieldElement.get("fieldName") == self.attribute.name:

                for valueElement in fieldElement.findall("value"):
                    thisValue = int(valueElement.text)

                    for i in range(self.inputWidget.topLevelItemCount() -1):
                        anItem = self.inputWidget.topLevelItem(i)

                        if anItem.id == thisValue:
                            anItem.setCheckState(0,  2)
                            self.hasChanges = True
                            break
                break

        self.inputWidget.itemChanged.connect(self.registerChange)

class DdN2mTableWidget(DdN2mWidget):
    '''a input widget for n-to-m relations with more than one field in the relation table
    The input widget consists of a QTableWidget and an add (+) and a remove (-) button'''

    def __init__(self,  attribute):
        DdN2mWidget.__init__(self,  attribute)
        self.fkValues = {}
        self.root = ET.Element('DdSearch')
        self.ddManager = QgsApplication.instance().ddManager

    def __str__(self):
        return "<ddui.DdN2mTableWidget %s>" % str(self.attribute.name)

    def createInputWidget(self,  parent):
        inputWidget = QtGui.QTableWidget(parent)
        inputWidget.setEditTriggers(QtGui.QAbstractItemView.NoEditTriggers)
        inputWidget.setColumnCount(len(self.attribute.attributes))
        fieldNames =  []

        for anAtt in self.attribute.attributes:
            fieldNames.append(anAtt.getLabel())
        horizontalHeaders = fieldNames

        inputWidget.setHorizontalHeaderLabels(horizontalHeaders)
        inputWidget.setSelectionMode(QtGui.QAbstractItemView.SingleSelection)
        inputWidget.setSelectionBehavior(QtGui.QAbstractItemView.SelectRows)
        inputWidget.setEditTriggers(QtGui.QAbstractItemView.NoEditTriggers)
        inputWidget.setSortingEnabled(True)
        inputWidget.cellDoubleClicked.connect(self.doubleClick)
        inputWidget.itemSelectionChanged.connect(self.selectionChanged)
        inputWidget.setObjectName("tbl" + parent.objectName() + self.attribute.name)
        return [inputWidget,  None]

    def fill(self):
        self.inputWidget.setRowCount(0)

        if self.mode == 1:
            ddTable = self.ddManager.makeDdTable(self.tableLayer)
            thisFeature = self.createFeature(-3333)

            for tableElement in self.root.findall("table"):
                if tableElement.get("tableName") == ddTable.tableName:
                    for fieldElement in tableElement.findall("field"):
                        for anAttr in self.attribute.attributes:
                            attName = anAttr.name

                            if fieldElement.get("fieldName") == attName:
                                operatorElement = fieldElement.find("operator")
                                searchString = ""

                                if operatorElement != None:
                                    operator = operatorElement.text
                                    valueElement = fieldElement.find("value")

                                    if valueElement != None and \
                                            operator != "IS NULL" and \
                                            operator != "IS NOT NULL":
                                        textValue = valueElement.text

                                        if anAttr.isFK:
                                            values = self.fkValues[anAttr.name]

                                            if anAttr.isTypeInt():
                                                lookupValue = int(textValue)
                                            elif anAttr.isTypeFloat():
                                                lookupValue = float(textValue)
                                            else:
                                                lookupValue = textValue

                                            try:
                                                aValue = values[lookupValue]
                                            except KeyError:
                                                aValue = textValue

                                            if not isinstance(aValue, unicode):
                                                aValue = str(aValue)
                                        else:
                                            aValue = textValue

                                            if operator == "BETWEEN...AND...":
                                                bvalueElement = fieldElement.find("bvalue")

                                                if bvalueElement != None:
                                                    operator = "BETWEEN"
                                                    aValue += " AND " + bvalueElement.text
                                    else:
                                        aValue = ""

                                    searchString = operator + " " + aValue

                                thisFeature[self.tableLayer.fieldNameIndex(attName)] =  searchString
                                break

                    self.appendRow(thisFeature)
                    self.addButton.setEnabled(False)
        elif self.mode == 2:
            self.addButton.setEnabled(False)
        else:
            self.applySubsetString(False)
            # display the features in the QTableWidget
            for aFeat in self.tableLayer.getFeatures(QgsFeatureRequest().setFlags(QgsFeatureRequest.NoGeometry)):
                self.appendRow(aFeat)

            if self.forEdit:
                if self.attribute.maxRows:
                    self.addButton.setEnabled(self.inputWidget.rowCount()  < self.attribute.maxRows)
            else:
                self.addButton.setEnabled(False)

            # reset here in case the same table is connected twice
            self.applySubsetString(True)

    def initialize(self, layer, feature, db, mode = 0):
        self.mode = mode

        if feature != None:
            if self.mode == 1:
                self.root = ET.Element('DdSearch')

            self.initializeLayer(layer,  feature,  db,  self.attribute.showParents,  withMask = True)

            # read the values for any foreignKeys
            for anAtt in self.attribute.attributes:
                if anAtt.isFK:
                    values = {}

                    if not anAtt.notNull:
                        values[""] = None

                    query = QtSql.QSqlQuery(db)
                    query.prepare(anAtt.queryForCbx)
                    query.exec_()

                    if query.isActive():
                        while query.next(): # returns false when all records are done
                            sValue =query.value(0)
                            keyValue = query.value(1)
                            values[keyValue] = sValue
                        query.finish()
                    else:
                        DbError(query)

                    self.fkValues[anAtt.name] = values

            self.fill()

    def fillRow(self, thisRow, thisFeature):
        '''fill thisRow with values from thisFeature'''

        for i in range(len(self.attribute.attributes)):
            anAtt = self.attribute.attributes[i]

            try:
                aValue = thisFeature[self.tableLayer.fieldNameIndex(anAtt.name)]
            except:
                DdError("Field " + anAtt.name + " not found!")
                continue

            if self.mode == 1:
                if isinstance(aValue,  QtCore.QPyNullVariant):
                    aValue = ""
            else:
                if anAtt.isFK:
                    values = self.fkValues[anAtt.name]
                    try:
                        aValue = values[aValue]
                    except KeyError:
                        aValue = 'NULL'

                if isinstance(aValue,  QtCore.QPyNullVariant):
                    aValue = 'NULL'

            if isinstance(anAtt, DdDateLayerAttribute):
                item = QtGui.QTableWidgetItem()
                item.setData(QtCore.Qt.DisplayRole, aValue)
            else:
                if anAtt.isTypeInt() or anAtt.isTypeFloat():
                    item = QtGui.QTableWidgetItem()
                    item.setData(QtCore.Qt.DisplayRole, aValue)
                else:
                    item = QtGui.QTableWidgetItem(unicode(aValue))

            if i == 0:
                item.feature = thisFeature

            self.inputWidget.setItem(thisRow, i, item)

    def appendRow(self, thisFeature):
        '''add a new row to the QTableWidget'''
        thisRow = self.inputWidget.rowCount() # identical with index of row to be appended as row indices are 0 based
        self.inputWidget.setRowCount(thisRow + 1) # append a row
        self.fillRow(thisRow, thisFeature)

    def setupUi(self,  parent,  db):
        frame = QtGui.QFrame(parent)
        frame.setFrameShape(QtGui.QFrame.StyledPanel)
        frame.setFrameShadow(QtGui.QFrame.Raised)
        frame.setObjectName("frame" + parent.objectName() + self.attribute.name)
        label = self.createLabel(frame)
        inputWidgets = self.createInputWidget(frame)
        self.inputWidget = inputWidgets[0]
        self.setSizeMax(frame)
        self.inputWidget.setToolTip(self.attribute.comment)
        vLayout = QtGui.QVBoxLayout(frame)
        vLayout.setObjectName(
            "vLayout" + parent.objectName() + self.attribute.name)
        hLayout = QtGui.QHBoxLayout()
        hLayout.setObjectName(
            "hLayout" + parent.objectName() + self.attribute.name)
        hLayout.addWidget(label)
        spacerItem = QtGui.QSpacerItem(40, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        hLayout.addItem(spacerItem)
        self.addButton = QtGui.QPushButton(QtGui.QApplication.translate("DdInput", "Add", None,
                                                           QtGui.QApplication.UnicodeUTF8) ,  frame)
        self.removeButton = QtGui.QPushButton(QtGui.QApplication.translate("DdInput", "Remove", None,
                                                           QtGui.QApplication.UnicodeUTF8) ,  frame)
        self.addButton.clicked.connect(self.add)
        self.removeButton.clicked.connect(self.remove)
        self.removeButton.setEnabled(False)
        hLayout.addWidget(self.addButton)
        hLayout.addWidget(self.removeButton)
        vLayout.addLayout(hLayout)
        vLayout.addWidget(self.inputWidget)
        newRow = parent.layout().rowCount() + 1
        parent.layout().setWidget(newRow, QtGui.QFormLayout.SpanningRole, frame)
        pParent = parent

        while (True):
            pParent = pParent.parentWidget()

            if isinstance(pParent,  DdDialog) or isinstance(pParent,  DdSearchDialog):
                self.parentDialog = pParent
                break

    def search(self,  layer):
        '''create search sql-string'''
        searchSql = ""
        ddTable = self.ddManager.makeDdTable(self.tableLayer)

        if self.inputWidget.rowCount() == 1:
            for tableElement in self.root.findall("table"):
                if tableElement.get("tableName") == ddTable.tableName:
                    for fieldElement in tableElement.findall("field"):
                        fieldName = fieldElement.get("fieldName")

                        for anAttribute in self.attribute.attributes:
                            if anAttribute.name == fieldName:
                                if searchSql == "":
                                    searchSql = self.attribute.pkAttName + " IN (SELECT \""  + \
                                        self.attribute.relationFeatureIdField + "\""
                                    searchSql += " FROM \"" + ddTable.schemaName + "\".\"" + ddTable.tableName + "\" WHERE "
                                else:
                                    searchSql += " AND "

                                operatorElement= fieldElement.find("operator")

                                if operatorElement != None:
                                    operator = operatorElement.text
                                    thisValue = ""

                                    if operator != "IS NULL" and operator != "IS NOT NULL":
                                        valueElement = fieldElement.find("value")

                                        if valueElement != None:
                                            thisValue = valueElement.text

                                            if (anAttribute.isTypeInt() or anAttribute.isTypeFloat()):
                                                thisValue = thisValue
                                            elif anAttribute.isTypeChar():
                                                if thisValue[:1] != "\'":
                                                    thisValue = "\'" + thisValue + "\'"
                                            else:
                                                if anAttribute.type == "bool":
                                                    if thisValue.upper() == "TRUE":
                                                        thisValue = "\'t\'"
                                                    else:
                                                        thisValue = "\'f\'"
                                                elif anAttribute.type == "text":
                                                    if thisValue[:1] != "\'":
                                                        thisValue = "\'" + thisValue + "\'"
                                                elif anAttribute.type == "date":
                                                    thisValue = "\'" + thisValue + "\'"

                                    if operator == "IN":
                                        searchSql += "\"" + anAttribute.name + "\" " + operator + " (" + thisValue + ")"
                                    elif operator == "BETWEEN...AND...":
                                        bvalueElement = fieldElement.find("bvalue")

                                        if bvalueElement != None:
                                            betweenValue = bvalueElement.text

                                            if betweenValue != None:
                                                if anAttribute.type == "date":
                                                    betweenValue = "\'" + betweenValue + "\'"

                                                searchSql += "\"" + anAttribute.name + "\" BETWEEN " + thisValue + " AND " + betweenValue
                                            else:
                                                operator = ">="
                                                searchSql += "\"" + anAttribute.name + "\" " + operator + " " + thisValue
                                        else:
                                            operator = ">="
                                            searchSql += "\"" + anAttribute.name + "\" " + operator + " " + thisValue
                                    else:
                                        searchSql += "\"" + anAttribute.name + "\" " + operator + " " + thisValue

                                break

        if searchSql != "":
            searchSql += ")"

        return searchSql

    def createSearch(self,  parentElement):
        ddTable = self.ddManager.makeDdTable(self.tableLayer)

        for tableElement in self.root.findall("table"):
            if tableElement.get("tableName") == ddTable.tableName:
                parentElement.append(tableElement)
                break

    def applySearch(self,  parentElement):
        ddTable = self.ddManager.makeDdTable(self.tableLayer)
        for tableElement in parentElement.findall("table"):
            if tableElement.get("tableName") == ddTable.tableName:
                self.root = ET.Element('DdSearch')
                self.root.append(tableElement)
                self.fill()
                break

    # SLOTS
    def selectionChanged(self):
        '''slot to be called when the QTableWidget's selection has changed'''
        if self.forEdit:
            self.removeButton.setEnabled(
                len(self.inputWidget.selectedItems()) > 0 and \
                self.attribute.enableWidget)

    def doubleClick(self,  thisRow,  thisColumn):
        '''slot to be called when the user double clicks on the QTableWidget'''
        if self.mode == 1:
            self.ddManager.setLastSearch(self.tableLayer,  self.root)
            result = self.ddManager.showSearchForm(self.tableLayer)

            if result == 1:
                self.root = self.ddManager.ddLayers[self.tableLayer.id()][6]
                thisRow = self.inputWidget.currentRow()
                self.inputWidget.removeRow(thisRow)
                self.fill()
        if self.mode == 0:
            if self.attribute.enableWidget:
                featureItem = self.inputWidget.item(thisRow,  0)
                thisFeature = featureItem.feature
                result = self.ddManager.showFeatureForm(self.tableLayer,
                    thisFeature, showParents = self.attribute.showParents)

                if result == 1: # user clicked OK
                    # make sure user did not change parentFeatureId
                    #self.tableLayer.changeAttributeValue(thisFeature.id(),
                    #   self.tableLayer.fieldNameIndex(self.attribute.relationFeatureIdField), self.featureId)
                    # refresh thisFeature with the new values
                    self.tableLayer.getFeatures(
                        QgsFeatureRequest().setFilterFid(thisFeature.id()).setFlags(
                        QgsFeatureRequest.NoGeometry)).nextFeature(thisFeature)

                    self.fillRow(thisRow,  thisFeature)
                    self.hasChanges = True

    def add(self):
        '''slot to be called when the user clicks on the add button'''
        if self.mode == 1:
            result = self.ddManager.showSearchForm(self.tableLayer)

            if result == 1:
                self.root = self.ddManager.ddLayers[self.tableLayer.id()][6]
                self.fill()
        elif self.mode == 0:
            thisFeature = self.createFeature()
            # set the parentFeature's id
            relationFeatFldIdx = self.tableLayer.fieldNameIndex(self.attribute.relationFeatureIdField)
            thisFeature[relationFeatFldIdx] = self.featureId[0]

            if self.tableLayer.addFeature(thisFeature):
                result = self.ddManager.showFeatureForm(self.tableLayer,  thisFeature,  askForSave = False)

                if result == 1: # user clicked OK
                    self.fill()

    def remove(self):
        '''slot to be called when the user clicks on the remove button'''
        thisRow = self.inputWidget.currentRow()

        if self.mode == 1:
            self.inputWidget.removeRow(thisRow)
            self.addButton.setEnabled(True)
            self.root = ET.Element('DdSearch')
        elif self.mode == 0:
            featureItem = self.inputWidget.takeItem(thisRow, 0)
            thisFeature = featureItem.feature
            self.tableLayer.deleteFeature(thisFeature.id())
            self.inputWidget.removeRow(thisRow)
            self.hasChanges = True

            if self.attribute.maxRows:
                self.addButton.setEnabled(self.inputWidget.rowCount()  < self.attribute.maxRows)

    def enableAccordingToDdAttribute(self):
        if self.attribute.enableWidget:
            self.setEnabled(self.attribute.enableWidget)
        else:
            self.inputWidget.setEnabled(True)
            self.addButton.setEnabled(False)

class DdArrayTableWidget(DdLineEdit):
    '''a table widget to show/edit values of an array field'''
    def __init__(self, attribute):
        DdLineEdit.__init__(self,  attribute)

    def __str__(self):
        return "<ddui.DdArrayTableWidget %s>" % str(self.attribute.name)

    def setSizeMax(self,  widget):
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(1)
        sizePolicy.setHeightForWidth(widget.sizePolicy().hasHeightForWidth())
        widget.setSizePolicy(sizePolicy)

    def getFeatureValue(self,  layer,  feature):
        '''returns an array[str] representing the value in this field for this feature;
        if the value is null, None is returned,
        if it is a new feature the default is returned.'''

        if feature == None:
            return None

        if self.mode == 2 and not self.attribute.notNull:
            return None

        fieldIndex = self.getFieldIndex(layer)
        thisValue = feature[fieldIndex]
        retValue = None

        if thisValue != None:
            if self.attribute.isTypeChar():
                thisValue = thisValue.replace("\"", "")
                # QGIS adds " if string contains spaces
                thisValue = thisValue.replace("NULL", "\'\'")
                thisValue = thisValue.replace("{\'", "").replace("\'}", "")
                thisValue = thisValue.split("\'" + self.attribute.arrayDelim + "\'")
            else:
                thisValue = thisValue.replace("{", "").replace("}", "")
                thisValue = thisValue.split(self.attribute.arrayDelim)

            retValue = []

            for aValue in thisValue:
                retValue.append(self.fromString(aValue))

        if feature.id() < 0 and thisValue == None: # new feature
            if self.mode != 1: # no return value for search feature
                if self.attribute.hasDefault:
                    retValue = self.getDefault()

        return retValue

    def setValue(self, thisValue):
        '''sets thisValue into the input widget'''

        self.inputWidget.setRowCount(0)

        if thisValue != None:
            for aValue in thisValue:
                self.appendRow(aValue)

    def extractValues(self):
        '''
        extract the values from the cells;
        implementation for strings
        '''

        thisValue = []

        for aRow in range(self.inputWidget.rowCount()):
            nullChk = self.inputWidget.cellWidget(
                aRow, self.inputWidget.columnCount() - 1)

            if (self.mode != 1) and nullChk.isChecked():
                thisValue.append(None)
            else:
                thisColumn = self.valueColumnIndex
                thisCellWidget = self.inputWidget.cellWidget(aRow,
                    thisColumn)

                if thisCellWidget != None:
                    aValue = self.extractCellWidgetValue(thisCellWidget)
                    thisValue.append(aValue)
                else:
                    aValue = self.inputWidget.item(aRow, thisColumn).text()
                    thisValue.append(self.fromString(aValue))

        if thisValue == []:
            thisValue = None

        return thisValue

    def extractCellWidgetValue(self, thisCellWidget):
        lineEdit = thisCellWidget
        return self.fromString(lineEdit.text())

    def getValue(self):
        if self.chk.isChecked():
            thisValue = None
        else:
            thisValue = self.extractValues()

        return thisValue

    def getDefault(self):
        '''function to strip quotation marks and data type from default string'''

        thisValue = self.attribute.default
        thisValue = thisValue.replace("ARRAY[", "")
        thisValue = thisValue[0:len(thisValue)-1] # drop closing ]

        for aType in ["::text", "::character varying"]:
            if thisValue.find(aType) != -1:
                thisType = aType

        thisValue = thisValue.replace(thisType, "") # strip type def
        returnValue = []

        for aValue in thisValue.split(self.attribute.arrayDelim):
            aValue = aValue.strip()

            if self.attribute.isTypeChar:
                aValue = aValue.replace("'", "")

            returnValue.append(aValue)

        return returnValue

    def setNull(self, setnull):
        '''Set this inputWidget to NULL'''

        thisValue = None

        if (not setnull) and (self.mode != 1) and self.attribute.hasDefault:
            thisValue = self.getDefault()

        self.setValue(thisValue)

    def save(self, layer, feature, db):
        if self.hasChanges:
            fieldIndex = self.getFieldIndex(layer)
            thisValue = self.getValue()

            if thisValue == None:
                saveValue = None
            else:
                saveValue = "{"

                for aValue in thisValue:
                    if aValue == None:
                        aValue = "NULL"
                        # save nulls in order to preserve the number of elements in array
                    else:
                        aValue = self.toSqlString(aValue)

                    if saveValue != "{":
                        saveValue += self.attribute.arrayDelim

                    saveValue += aValue

                saveValue += "}"

                if saveValue == "{}":
                    saveValue = None

            if self.mode == 0:
                layer.changeAttributeValue(feature.id(), fieldIndex, saveValue)
            elif self.mode == 2:
                for anId in layer.selectedFeaturesIds():
                    layer.changeAttributeValue(anId, fieldIndex, saveValue)

        return self.hasChanges

    def createInputWidget(self,  parent):
        inputWidget = QtGui.QTableWidget(parent)
        inputWidget.setColumnCount(2)
        self.valueColumnIndex = 0
        inputWidget.setSelectionMode(QtGui.QAbstractItemView.SingleSelection)
        inputWidget.setSelectionBehavior(QtGui.QAbstractItemView.SelectRows)
        #inputWidget.horizontalHeader().setVisible(False)
        inputWidget.setEditTriggers(QtGui.QAbstractItemView.DoubleClicked)
        inputWidget.setSortingEnabled(True)
        inputWidget.cellChanged.connect(self.cellChanged)
        #inputWidget.cellDoubleClicked.connect(self.cellDoubleClicked)
        inputWidget.itemSelectionChanged.connect(self.selectionChanged)
        inputWidget.cellClicked.connect(self.cellClicked)
        inputWidget.setObjectName("tbl" + parent.objectName() + self.attribute.name)
        return [inputWidget,  None]

    def initialize(self, layer, feature, db, mode = 0):
        self.mode = mode

        if feature == None:
            self.manageChk(None)
        else:
            logicHeader = QtGui.QApplication.translate(
                "DdInfo", "logical", None,
                QtGui.QApplication.UnicodeUTF8)
            operatorHeader = QtGui.QApplication.translate(
                "DdInfo", "operator", None,
                QtGui.QApplication.UnicodeUTF8)
            valueHeader = QtGui.QApplication.translate(
                "DdInfo", "value", None,
                QtGui.QApplication.UnicodeUTF8)
            nullHeader = QtGui.QApplication.translate("DdInfo",
                "Null", None, QtGui.QApplication.UnicodeUTF8)

            if self.mode == 1: # searchFeature
                self.inputWidget.setColumnCount(4)
                self.inputWidget.hideColumn(3)
                self.inputWidget.setHorizontalHeaderLabels([
                    logicHeader, valueHeader, operatorHeader])
                self.chk.setChecked(True)
                self.chk.setVisible(True)
                self.chk.setText(QtGui.QApplication.translate(
                    "DdInfo", "Ignore", None,
                    QtGui.QApplication.UnicodeUTF8))
                self.chk.setToolTip(QtGui.QApplication.translate(
                    "DdInfo", "Check if you want this field to be ignored in the search.",
                    None, QtGui.QApplication.UnicodeUTF8))
                self.valueColumnIndex = 1
            else:
                self.inputWidget.setHorizontalHeaderLabels(
                    [valueHeader, nullHeader])
                thisValue = self.getFeatureValue(layer, feature)
                self.setValue(thisValue)
                #self.setValidator(min = thisValue, max = thisValue)
                # make sure the validator does not kick out an already existing value
                self.manageChk(thisValue)
                self.hasChanges = (feature.id() < 0) # register this change only for new feature

    def validate(self, thisValue, layer, feature, showMsg = True):
        '''
        checks if values are within min/max range (if defined)
        '''
        accepted = True
        msgShown = False
        featureValue = self.getFeatureValue(layer, feature)

        if self.hasChanges:
            if thisValue != None:
                for i in range(len(thisValue)):
                    aValue = thisValue[i]

                    try:
                        fValue = featureValue[i]
                    except:
                        fValue = None

                    if aValue != None and aValue != fValue:
                        if self.attribute.min != None:
                            if aValue < self.attribute.min:
                                if showMsg:
                                    QtGui.QMessageBox.warning(
                                        None, self.getLabel(),
                                        QtGui.QApplication.translate(
                                            "DdWarning", "Value ",
                                            None, QtGui.QApplication.UnicodeUTF8
                                        ) + self.toString(aValue) +
                                        QtGui.QApplication.translate(
                                            "DdWarning", " is too small! Minimum is ",
                                            None, QtGui.QApplication.UnicodeUTF8
                                            ) + self.toString(self.attribute.min))
                                    msgShown = True
                                accepted = False
                                break
                        if self.attribute.max != None:
                            if aValue > self.attribute.max:
                                if showMsg:
                                    QtGui.QMessageBox.warning(
                                        None, self.getLabel(),
                                       QtGui.QApplication.translate(
                                            "DdWarning", "Value ",
                                            None, QtGui.QApplication.UnicodeUTF8
                                        ) + self.toString(aValue) +
                                        QtGui.QApplication.translate(
                                            "DdWarning", " is too large! Maximum is ",
                                            None, QtGui.QApplication.UnicodeUTF8
                                        ) + self.toString(self.attribute.max))
                                    msgShown = True
                                accepted = False
                                break
            else:
                if not self.chk.isChecked() and self.attribute.hasDefault:
                    thisValue = self.getDefault()
                    self.setValue(thisValue)

        return [accepted, msgShown]

    def setSearchCombo(self, thisRow, link = None, operator = None):
        '''sets combo boxes for searching to columns 0 and 1'''

        combo = QtGui.QComboBox()
        searchItems = ["=",  "!="]

        if self.attribute.isTypeChar():
            searchItems += ["LIKE",  "ILIKE"]
        else:
            if self.attribute.type != "bool":
                searchItems += [">",  "<",  ">=",  "<="]

        li = []

        for a in ["ANY", "ALL"]:
            for s in searchItems:
                li.append (s + " " + a)

        if not self.attribute.notNull:
            li.append("IS NULL")
            li.append ("IS NOT NULL")

        combo.addItems(li)

        if operator != None:
            idx = li.index(operator)
            combo.setCurrentIndex(idx)

        self.inputWidget.setCellWidget(thisRow, 2, combo)

        if thisRow > 0:
            li2 = ["AND", "OR"]
            combo2 = QtGui.QComboBox()
            combo2.addItems(li2)

            if link != None:
                idx2 = li2.index(link)
                combo2.setCurrentIndex(idx2)

            self.inputWidget.setCellWidget(thisRow, 0, combo2)

    def getDefaultItemValue(self):
        '''returns the default value to be added for new items'''
        return ""

    def setCellWidget(self, thisRow, aValue):
        '''replace the QTableWidget item with an appropriate QWidget'''
        lineEdit = QtGui.QLineEdit(self.inputWidget)

        if aValue == None:
            lineEdit.setText(self.getDefaultItemValue())
        else:
            lineEdit.setText(self.toString(aValue))

        lineEdit.textChanged.connect(self.registerChange)
        lineEdit.editingFinished.connect(self.focusLost)
        self.inputWidget.setCellWidget(thisRow,
            self.valueColumnIndex, lineEdit)

    def setRowValue(self, thisRow, aValue, checkIfNon = True):
        '''
        sets this row's value to thisValue;
        default implementation for strings
        '''

        if aValue == None:
            item = QtGui.QTableWidgetItem("")
        else:
            item = QtGui.QTableWidgetItem(self.toString(aValue))

        self.inputWidget.setItem(thisRow,
            self.valueColumnIndex, item)

        nullChk = QtGui.QCheckBox()
        nullChk.setChecked(aValue == None and checkIfNon)
        nullChk.stateChanged.connect(self.nullChkStateChanged)
        self.inputWidget.setCellWidget(thisRow,
            self.inputWidget.columnCount() - 1, nullChk)

    def fillRow(self, thisRow, aValue, link = None,
        operator = None, checkIfNone = True):
        '''fill thisRow with aValue'''

        if self.mode == 1:
            self.setSearchCombo(thisRow, link, operator)

        self.setRowValue(thisRow, aValue, checkIfNone)
        self.inputWidget.resizeColumnToContents(
            self.valueColumnIndex)

    def appendRow(self, aValue, link = None, operator = None, checkIfNone = True):
        '''add a new row to the QTableWidget'''

        thisRow = self.inputWidget.rowCount() # identical with index of row to be appended as row indices are 0 based
        self.inputWidget.setRowCount(thisRow + 1) # append a row
        self.fillRow(thisRow, aValue, link, operator, checkIfNone)
        return thisRow

    def insertRow(self, thisRow, aValue, link = None, operator = None):
        '''add a new row to the QTableWidget'''

        self.inputWidget.insertRow(thisRow) # append a row
        self.fillRow(thisRow, aValue, link, operator)
        return thisRow

    def setupUi(self, parent, db):
        frame = QtGui.QFrame(parent)
        frame.setFrameShape(QtGui.QFrame.StyledPanel)
        frame.setFrameShadow(QtGui.QFrame.Raised)
        frame.setObjectName("frame" + parent.objectName() + self.attribute.name)
        label = self.createLabel(frame)
        inputWidgets = self.createInputWidget(frame)
        self.inputWidget = inputWidgets[0]
        self.setSizeMax(frame)
        self.inputWidget.setToolTip(self.attribute.comment)
        vLayout = QtGui.QVBoxLayout(frame)
        vLayout.setObjectName(
            "vLayout" + parent.objectName() + self.attribute.name)
        hLayout = QtGui.QHBoxLayout()
        hLayout.setObjectName(
            "hLayout" + parent.objectName() + self.attribute.name)
        hLayout.addWidget(label)
        spacerItem = QtGui.QSpacerItem(40, 20, QtGui.QSizePolicy.Expanding,
            QtGui.QSizePolicy.Minimum)
        hLayout.addItem(spacerItem)
        self.addButton = QtGui.QPushButton(
            QtGui.QApplication.translate("DdInput", "Add", None,
            QtGui.QApplication.UnicodeUTF8), frame)
        self.removeButton = QtGui.QPushButton(
            QtGui.QApplication.translate("DdInput", "Remove", None,
            QtGui.QApplication.UnicodeUTF8) ,  frame)
        self.addButton.clicked.connect(self.add)
        self.addButton.setEnabled(self.attribute.enableWidget)
        self.removeButton.clicked.connect(self.remove)
        self.removeButton.setEnabled(False)
        hLayout.addWidget(self.addButton)
        hLayout.addWidget(self.removeButton)
        self.chk = QtGui.QCheckBox(QtGui.QApplication.translate("DdInfo",
            "Null", None, QtGui.QApplication.UnicodeUTF8), parent)
        self.chk.setObjectName("chk" + parent.objectName() + self.attribute.name)
        self.chk.setToolTip(QtGui.QApplication.translate(
            "DdInfo", "Check if you want to save an empty (or null) value.", None,
            QtGui.QApplication.UnicodeUTF8))
        self.chk.stateChanged.connect(self.chkStateChanged)
        self.chk.setVisible(not self.attribute.notNull)
        hLayout.addWidget(self.chk)
        vLayout.addLayout(hLayout)
        vLayout.addWidget(self.inputWidget)
        newRow = parent.layout().rowCount() + 1
        parent.layout().setWidget(newRow, QtGui.QFormLayout.SpanningRole, frame)

    def toSqlString(self, aValue):
        '''
        convert aValue to a string representation that
        can be used in a SQL statement
        default implementation for string
        '''

        retValue = "'" + self.toString(aValue) + "'"
        return retValue

    def fromString(self, aValue):
        '''
        convert aValue from its string representation
        to a value of the appropriate class
        default implementation for string
        '''

        if aValue == "": # empty string considered NULL
            return None
        else:
            return aValue

    def search(self,  layer):
        '''create search sql-string'''

        searchSql = ""

        if not self.chk.isChecked():
            thisValue = self.getValue()

            for aRow in range(len(thisValue)):

                operator = self.inputWidget.cellWidget(aRow, 2).currentText()

                if aRow > 0:
                    link = self.inputWidget.cellWidget(aRow, 0).currentText()
                    searchSql += " " + link + " "

                if operator == "IS NULL" or operator == "IS NOT NULL":
                    searchSql += " \"" + self.attribute.name + "\" " + operator
                else:
                    aValue = thisValue[aRow]
                    searchSql += self.toSqlString(aValue) + \
                        operator + " (\"" + self.attribute.name + "\")"

        if searchSql != "":
            searchSql = "(" + searchSql + ")"

        return searchSql

    def createSearch(self, parentElement):
        '''create the search XML'''
        fieldElement = None

        if not self.chk.isChecked():
            thisValue = self.getValue()
            fieldElement = ET.SubElement(parentElement,  "field")
            fieldElement.set("fieldName", self.attribute.name)
            fieldElement.set("type", self.attribute.type)
            fieldElement.set("widgetType", "DdArrayTableWidget")
            arrayElement = ET.SubElement(fieldElement, "array")

            for aRow in range(len(thisValue)):
                aValue = thisValue[aRow]
                valueElement = ET.SubElement(arrayElement, "entry")
                operator = self.inputWidget.cellWidget(aRow, 2).currentText()
                linkElement = ET.SubElement(valueElement, "link")

                if operator != "IS NULL" and operator != "IS NOT NULL":
                    valueElement.set("value", self.toString(aValue))

                if aRow > 0:
                    link = self.inputWidget.cellWidget(aRow, 0).currentText()
                    linkElement.text = link

                operatorElement = ET.SubElement(valueElement, "operator")
                operatorElement.text = operator

        return fieldElement

    def applySearch(self, parentElement):
        notFound = True

        for fieldElement in parentElement.findall("field"):
            if fieldElement.get("fieldName") == self.attribute.name:
                arrayElement = fieldElement.find("array")

                if arrayElement != None:
                    self.chk.setChecked(False)
                    self.inputWidget.removeRow(0) # checking adds a row
                    notFound = False

                    for valueElement in arrayElement.findall("entry"):
                        operator = valueElement.find("operator").text

                        if operator == "IS NULL" or operator == "IS NOT NULL":
                            aValue = None
                        else:
                            aValue = self.fromString(valueElement.get("value"))

                        link = valueElement.find("link").text

                        if link == "":
                            link = None

                        self.appendRow(aValue, link, operator)

                break

        if notFound:
            self.chk.setChecked(True)

    #SLOTs
    def nullChkStateChanged(self, newState):
        self.hasChanges = True
        nullChk = QgsApplication.instance().focusWidget()
        thisRow = self.inputWidget.rowAt(nullChk.pos().y())
        self.inputWidget.removeRow(thisRow)

        if newState == QtCore.Qt.Checked:
            self.insertRow(thisRow, None)
        else:
            self.insertRow(thisRow, self.getDefaultItemValue())

    def focusLost(self, thisRow = None):
        '''implementation in child classes'''

        if thisRow == None:
            lineEdit = QgsApplication.instance().focusWidget()
            thisRow = self.inputWidget.rowAt(lineEdit.pos().y())

            if thisRow == None: # we left this DdWidget
                return None

        if thisRow == self.inputWidget.currentRow():
            return None # do not do anything if we stay in the row

        thisColumn = self.valueColumnIndex
        lineEdit = self.inputWidget.cellWidget(thisRow, thisColumn)

        if lineEdit != None:
            thisValue = self.fromString(lineEdit.text())
            operator = None
            link = None

            if self.mode == 1:
                operator = self.inputWidget.cellWidget(thisRow, 2).currentText()

                if thisRow > 0:
                    link = self.inputWidget.cellWidget(thisRow, 0).currentText()

            self.inputWidget.removeRow(thisRow)
            self.insertRow(thisRow, thisValue, link, operator)

    def cellClicked(self, thisRow, thisColumn):
        if thisColumn != self.valueColumnIndex:
            thisColumn = self.valueColumnIndex
            # dataColumn

        thisItem = self.inputWidget.item(thisRow, thisColumn)

        if thisItem != None:
            thisValue = thisItem.text()

            if thisValue == "":
                thisValue = None
            else:
                thisValue = self.fromString(thisValue)

            self.setRowValue(thisRow, None, checkIfNon = False)
            self.setCellWidget(thisRow, thisValue)

    def cellChanged(self, thisRow, thisColumn):
        self.registerChange(None)

    def chkStateChanged(self, newState):
        '''slot: disables the input widget if the null checkbox is checked and vice versa'''

        self.setNull(newState == QtCore.Qt.Checked)

        if self.mode == 1:
            self.inputWidget.setEnabled(newState == QtCore.Qt.Unchecked)
            self.addButton.setEnabled(newState == QtCore.Qt.Unchecked)

            if newState == QtCore.Qt.Unchecked:
                self.appendRow(None)
        else:
            if self.attribute.enableWidget:
                self.inputWidget.setEnabled(
                    newState == QtCore.Qt.Unchecked)
                self.addButton.setEnabled(
                    newState == QtCore.Qt.Unchecked)

                if newState == QtCore.Qt.Unchecked and \
                        self.inputWidget.rowCount() == 0:
                    self.appendRow(None, checkIfNone = False)

        self.hasChanges = True

    def selectionChanged(self):
        '''slot to be called when the QTableWidget's selection has changed'''
        self.removeButton.setEnabled(len(self.inputWidget.selectedItems()) > 0)

    def add(self):
        '''slot to be called when the user clicks on the add button'''
        self.appendRow(self.getDefaultItemValue())
        self.hasChanges = True

    def remove(self):
        '''slot to be called when the user clicks on the remove button'''
        thisRow = self.inputWidget.currentRow()
        self.inputWidget.removeRow(thisRow)

        if self.mode == 1:
            if thisRow == 0:
                if self.inputWidget.rowCount() > 0:
                    # we need to get rid of the combo box in the first column
                    # therefore we refill the tableWidget completely
                    thisValue = self.getValue()
                    operators = []
                    links = []

                    for aRow in range(len(thisValue)):
                        operators.append(self.inputWidget.cellWidget(aRow, 1).currentText())
                        links.append(self.inputWidget.cellWidget(aRow, 0).currentText())

                    self.inputWidget.clear()
                    self.inputWidget.setRowCount(0)

                    for aRow in range(len(thisValue)):
                        aValue = thisValue[aRow]
                        operator = operators[aRow]
                        link = links[aRow]
                        self.appendRow(aValue, link, operator)

            self.addButton.setEnabled(True)
            self.root = ET.Element('DdSearch')
        else:
            self.hasChanges = True

class DdArrayTableWidgetInt(DdArrayTableWidget):
    '''a table widget to show/edit values of an integer array field'''
    def __init__(self, attribute):
        DdArrayTableWidget.__init__(self, attribute)

    def __str__(self):
        return "<ddui.DdArrayTableWidgetInt %s>" % str(self.attribute.name)

    def toString(self,  thisValue):
        loc = QtCore.QLocale.system()
        return loc.toString(thisValue)

    def toSqlString(self, aValue):
        retValue = str(aValue)
        return retValue

    def fromString(self, aValue):
        try:
            newValue = int(aValue)
        except:
            loc = QtCore.QLocale.system()
            newValue, valid = loc.toInt(aValue)

            if not valid:
                newValue, valid = loc.toLongLong(aValue)

                if not valid:
                    newValue = None

        return newValue

    def getDefaultItemValue(self):
        if self.attribute.min != None:
            return self.attribute.min
        else:
            return 0

    def setCellWidget(self, thisRow, aValue):
        lineEdit = QtGui.QLineEdit(self.inputWidget)

        if aValue == None:
            lineEdit.setText(self.toString(self.getDefaultItemValue()))
        else:
            lineEdit.setText(self.toString(aValue))

        if self.mode != 1:
            validator = ddtools.getIntValidator(lineEdit,
                self.attribute, aValue, aValue)
                # pass aValue as min and max so existing values are
                # allowed no matter of attribute's min and max
            lineEdit.setValidator(validator)

        lineEdit.textChanged.connect(self.registerChange)
        lineEdit.editingFinished.connect(self.focusLost)
        self.inputWidget.setCellWidget(thisRow,
            self.valueColumnIndex, lineEdit)

class DdArrayTableWidgetDouble(DdArrayTableWidget):
    '''a table widget to show/edit values of an integer array field'''
    def __init__(self, attribute):
        DdArrayTableWidget.__init__(self, attribute)

    def __str__(self):
        return "<ddui.DdArrayTableWidgetDouble %s>" % str(self.attribute.name)

    def getDefaultItemValue(self):
        if self.attribute.min != None:
            return self.attribute.min
        else:
            return 0

    def setCellWidget(self, thisRow, aValue):
        lineEdit = QtGui.QLineEdit(self.inputWidget)

        if aValue == None:
            lineEdit.setText(self.toString(self.getDefaultItemValue()))
        else:
            lineEdit.setText(self.toString(aValue))

        if self.mode != 1:
            validator = ddtools.getDoubleValidator(lineEdit,
                self.attribute, aValue, aValue)
                # pass aValue as min and max so existing values are
                # allowed no matter of attribute's min and max
            lineEdit.setValidator(validator)

        lineEdit.textChanged.connect(self.registerChange)
        lineEdit.editingFinished.connect(self.focusLost)
        self.inputWidget.setCellWidget(thisRow,
            self.valueColumnIndex, lineEdit)

    def toString(self, thisValue):
        loc = QtCore.QLocale.system()
        return loc.toString(thisValue)

    def toSqlString(self, aValue):
        retValue = str(aValue)
        return retValue

    def fromString(self, aValue):
        try:
            newValue = float(aValue)
        except:
            loc = QtCore.QLocale.system()
            newValue, valid = loc.toDouble(aValue)

            if not valid:
                newValue = None

        return newValue

class DdArrayTableWidgetBool(DdArrayTableWidget):
    '''a table widget to show/edit values of a boolean array field'''
    def __init__(self, attribute):
        DdArrayTableWidget.__init__(self, attribute)

    def __str__(self):
        return "<ddui.DdArrayTableWidgetBool %s>" % str(self.attribute.name)

    def extractCellWidgetValue(self, thisCellWidget):
        chk = thisCellWidget
        return chk.isChecked()

    def getDefaultItemValue(self):
        return False

    def setCellWidget(self, thisRow, aValue):
        chk = QtGui.QCheckBox(self.inputWidget)

        if aValue == None:
            chk.setChecked(self.getDefaultItemValue())
        else:
            chk.setChecked(aValue)

        chk.stateChanged.connect(self.registerChange)
        chk.released.connect(self.focusLost)
        self.inputWidget.setCellWidget(thisRow,
            self.valueColumnIndex, chk)

    def focusLost(self, thisRow = None):
        if thisRow == None:
            chk = QgsApplication.instance().focusWidget()
            thisRow = self.inputWidget.rowAt(chk.pos().y())

            if thisRow == None: # we left this DdWidget
                return None

        if thisRow == self.inputWidget.currentRow():
            return None

        thisColumn = self.valueColumnIndex
        chk = self.inputWidget.cellWidget(thisRow,thisColumn)
        thisValue = chk.isChecked()
        operator = None
        link = None

        if self.mode == 1:
            operator = self.inputWidget.cellWidget(aRow, 2).currentText()

            if thisRow > 0:
                link = self.inputWidget.cellWidget(aRow, 0).currentText()

        self.inputWidget.removeRow(thisRow)
        self.insertRow(thisRow, thisValue, link, operator)

    def toSqlString(self, aValue):
        if aValue:
            retValue = "true"
        else:
            retValue = "false"

        return retValue

    def fromString(self, aValue):
        if aValue == "True" or aValue == "true" or aValue == "t":
            newValue = True
        elif aValue == "False" or aValue == "false" or aValue == "f":
            newValue = False
        else:
            newValue = None

        return newValue

class DdArrayTableWidgetDate(DdArrayTableWidget):
    '''a table widget to show/edit values of a date array field'''
    def __init__(self, attribute):
        DdArrayTableWidget.__init__(self, attribute)

    def __str__(self):
        return "<ddui.DdArrayTableWidgetBool %s>" % str(self.attribute.name)

    def extractCellWidgetValue(self, thisCellWidget):
        dateEdit = thisCellWidget
        return dateEdit.date()

    def getDefaultItemValue(self):
        if self.attribute.min != None:
            return self.attribute.min
        else:
            return QtCore.QDate.currentDate()

    def setCellWidget(self, thisRow, aValue):
        date = QtGui.QDateEdit(self.inputWidget)
        date.setCalendarPopup(True)
        loc = QtCore.QLocale.system()
        date.setDisplayFormat(loc.dateFormat())

        if self.mode != 1:
            if self.attribute.min != None:
                thisMin = self.attribute.min

                if aValue != None:
                    if aValue < self.attribute.min:
                        thisMin = min

                date.setMinimumDate(thisMin)

            if self.attribute.max != None:
                thisMax = self.attribute.max

                if aValue != None:
                    if aValue > self.attribute.max:
                        thisMax = max

                date.setMaximumDate(thisMax)

        if aValue == None:
            date.setDate(self.getDefaultItemValue())
        else:
            date.setDate(aValue)

        date.dateChanged.connect(self.registerChange)
        date.editingFinished.connect(self.focusLost)
        self.inputWidget.setCellWidget(thisRow,
            self.valueColumnIndex, date)

    def focusLost(self, thisRow = None):
        if thisRow == None:
            date = QgsApplication.instance().focusWidget()
            thisRow = self.inputWidget.rowAt(date.pos().y())

            if thisRow == None: # we left this DdWidget
                return None

        if thisRow == self.inputWidget.currentRow():
            return None

        thisColumn = self.valueColumnIndex
        date = self.inputWidget.cellWidget(thisRow, thisColumn)
        thisValue = date.date()
        operator = None
        link = None

        if self.mode == 1:
            operator = self.inputWidget.cellWidget(aRow, 2).currentText()

            if thisRow > 0:
                link = self.inputWidget.cellWidget(aRow, 0).currentText()

        self.inputWidget.removeRow(thisRow)
        self.insertRow(thisRow, thisValue, link, operator)

    def toString(self, thisValue):
        loc = QtCore.QLocale.system()
        return loc.toString(thisValue)

    def toSqlString(self, aValue):
        retValue = aValue.toString("yyyy-MM-dd")
        retValue = "\'" + retValue + "\'"
        return retValue

    def fromString(self, aValue):
        newValue = QtCore.QDate.fromString(aValue,'yyyy-MM-dd')

        if newValue.isNull():
            loc = QtCore.QLocale.system()
            newValue = loc.toDate(aValue)

            if newValue.isNull():
                newValue = None

        return newValue

class DdLineEditGeometry(DdLineEditInt):

    def __init__(self, attribute):
        DdLineEditInt.__init__(self, attribute)

    def __str__(self):
        return "<ddui.DdLineEditGeometry %s>" % str(self.attribute.name)

    def getFeatureValue(self, layer, feature):
        if feature == None or self.mode == 2:
            return None

        geom = feature.geometry()

        if geom == None: # possible if new feature from within another mask
            self.inputWidget.setVisible(False)
            self.label.setVisible(False)
            return None
        else:
            area = geom.area()

            if area > 0:
                self.label.setText(QtGui.QApplication.translate(
                    "DdInfo", "GIS area", None, QtGui.QApplication.UnicodeUTF8))
                return int(round(area))
            else:
                length = int(geom.length())

                if length > 0:
                    self.label.setText(QtGui.QApplication.translate(
                        "DdInfo", "GIS length", None, QtGui.QApplication.UnicodeUTF8))
                    return round(length)
                else:
                    self.inputWidget.setVisible(False)
                    self.label.setVisible(False)
                    return None

    def checkDefault(self, feature):
        return [True, None]

    def checkInput(self, layer, feature):
        return True

    def save(self,  layer,  feature,  db):
        return True

    def validate(self, thisValue, layer, feature, showMsg = True):
        return True















