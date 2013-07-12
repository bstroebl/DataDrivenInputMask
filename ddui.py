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
        copyright            : (C) 2012 by Bernhard Strรถbl / Kommunale Immobilien Jena
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
from dddialog import DdDialog

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
        #QtGui.QMessageBox.information(None,  "",  str(self.prntWidget))

def ddFormInit1(dialog, layerId, featureId):
    dialog.setProperty("helper", DdFormHelper(dialog, layerId, featureId))

def ddFormInit(dialog, layerId, featureId):
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
                try:
                    layerValues = ddManager.ddLayers[aLayer.id()]
                except KeyError:
                    ddManager.initLayer(aLayer,  skip = [])
                    layerValues = ddManager.ddLayers[aLayer.id()]

                #QtGui.QMessageBox.information(None, "", str(layerValues[2]))
                db = layerValues[1]
                ui = layerValues[2]
                dlg = DdDialog(ddManager,  ui,  aLayer,  feat,  db,  dialog)
                dlg.show()
                result = dlg.exec_()

                if result == 1:
                    layer.setModified()

class DdManager(object):
    """DdManager manages all masks in the current project"""

    def __init__(self,  iface):
        self.iface = iface
        self.ddLayers = dict()

    def __debug(self,  title,  str):
        QtGui.QMessageBox.information(None,  title,  str)

    def __str__(self):
        return "<ddui.DdManager>"

    def initLayer(self,  layer,  skip = [],  labels = {},  fieldOrder = [],  minMax = {},  showParents = True,  createAction = True,  db = None):
        '''api method initLayer: initialize the layer with a data-driven input mask
        Returns a Boolean stating the success of the initialization'''

        if 0 != layer.type():   # not a vector layer
            DdError(QtGui.QApplication.translate("DdError", "Layer is not a vector layer: ", None,
                                                           QtGui.QApplication.UnicodeUTF8) + layer.name())
            return False
        else:
            if u'PostgreSQL' != layer.dataProvider().storageType()[0:10] :
                DdError(QtGui.QApplication.translate("DdError", "Layer is not a PostgreSQL layer: ", None,
                                                               QtGui.QApplication.UnicodeUTF8) + layer.name())
                return False
            else:
                if not db:
                    db = self.__createDb(layer)

                layerSrc = self.__analyzeSource(layer)
                relation = layerSrc["table"].split('"."')
                schema = relation[0].replace('"', '')
                table = relation[1].replace('"', '')
                #QtGui.QMessageBox.information(None, "",  schema + '.' + table)
                thisTable = DdTable(schemaName = schema,  tableName = table,  title = layer.name())
                thisTable.oid = self.__getOid(thisTable,  db)
                comment = self.__getComment(thisTable,  db)

                if comment:
                    thisTable.comment = comment

                if not self.__isTable(thisTable,  db):
                    DdError(QtGui.QApplication.translate("DdError", "Layer is not a PostgreSQL table: ", None,
                                                                       QtGui.QApplication.UnicodeUTF8) + layer.name())
                    return False

                ddui = DataDrivenUi(self.iface)
                ui = ddui.createUi(thisTable,  db,  skip,  labels,  fieldOrder,  minMax,  showParents)
                self.ddLayers.pop(layer.id(),  None) # remove entries if they exist
                self.ddLayers[layer.id()] = [thisTable,  db,  ui]
                self.__connectSignals(layer)

                if createAction:
                    self.addAction(layer)

                return True

    def addAction(self,  layer,  actionName = u'showDdForm'):
        '''api method to add an action to the layer with a self defined name'''

        createAction = True
        #check if the action is already attached
        for i in range(layer.actions().size()):
            act = layer.actions().at(i)

            if act.name() == actionName:
                createAction = False
                break

        if createAction:
            layer.actions().addAction(1,  actionName, # actionType 1: Python
                                 "app=QgsApplication.instance();ddManager=app.ddManager;ddManager.showDdForm([% $id %]);")

    def removeAction(self,  layer,  actionName):
        '''api method to remove an action from the layer'''

        wereActions = []
        for i in range(layer.actions().size()):
            act = layer.actions().at(i)

            if act.name() != actionName:
                wereActions.append(act)

        layer.actions().clearActions()

        for act in wereActions:
            layer.actions().addAction(act.type(),  act.name(), act.action())

    def showFeatureForm(self,  layer,  feature):
        '''api method showFeatureForm: show the data-driven input mask for a layer and a feature
        returns 1 if user clicked OK, 0 if CANCEL'''

        layerValues = self.__getLayerValues(layer)

        if layerValues != None:
            #QtGui.QMessageBox.information(None, "", str(layerValues[2]))
            db = layerValues[1]
            ui = layerValues[2]
            dlg = DdDialog(self,  ui,  layer,  feature,  db)
            dlg.show()
            result = dlg.exec_()

            if result == 1:
                layer.emit(QtCore.SIGNAL('layerModified()'))

        else:
            result = 0

        return result

    def showDdForm(self,  fid):
        aLayer = self.iface.activeLayer()
        feat = QgsFeature()
        featureFound = aLayer.getFeatures(QgsFeatureRequest().setFilterFid(fid).setFlags(QgsFeatureRequest.NoGeometry)).nextFeature(feat)

        if featureFound:
            self.showFeatureForm(aLayer,  feat)

    def setUi(self,  layer,  ui):
        '''api method to exchange the default ui with a custom ui'''

        layerValues = self.__getLayerValues(layer)

        if layerValues != None:
            #QtGui.QMessageBox.information(None, "", str(layerValues[2]))
            thisTable = layerValues[0]
            db = layerValues[1]
            self.ddLayers[layer.id()] = [thisTable,  db,  ui]

    def setDb(self,  layer,  db):
        '''api method to set the db for a layer'''
        layerValues = self.__getLayerValues(layer)

        if layerValues != None:
            thisTable = layerValues[0]
            oldDb = layerValues[1]
            self.__disconnectDb(oldDb)
            ui = layerValues[2]
            self.ddLayers[layer.id()] = [thisTable,  db,  ui]

    def findPostgresLayer(self, db,  ddTable):
        layerList = self.iface.legendInterface().layers()
        procLayer = None # ini

        for layer in layerList:
            if isinstance(layer, QgsVectorLayer):
                src = layer.source()

                if ("table=\"" + ddTable.schemaName + "\".\"" + ddTable.tableName + "\"" in src) and \
                    (db.databaseName() in src) and \
                    (db.hostName() in src):
                    procLayer = layer
                    break

        return procLayer

    def getGroupIndex(self,  groupName):
        '''Find the index for groupName in the legend'''
        retValue = -1
        groups = self.iface.legendInterface().groups()

        for i in range(len(groups)):
            if groups[i] == groupName:
                retValue = i
                break

        return retValue

    def loadPostGISLayer(self,  db, ddTable, displayName = None,
        geomColumn = None, whereClause = None, keyColumn = None,
        intoDdGroup = True):

        if not displayName:
            displayName = ddTable.schemaName + "." + ddTable.tableName

        uri = QgsDataSourceURI()
        thisPort = db.port()

        if thisPort == -1:
            thisPort = 5432

        # set host name, port, database name, username and password
        uri.setConnection(db.hostName(), str(thisPort), db.databaseName(), db.userName(), db.password())
        # set database schema, table name, geometry column and optionaly subset (WHERE clause)

        uri.setDataSource(ddTable.schemaName, ddTable.tableName, geomColumn)

        if whereClause:
            uri.setSql(whereClause)

        if keyColumn:
            uri.setKeyColumn(keyColumn)
        vlayer = QgsVectorLayer(uri.uri(), displayName, "postgres")
        tLayer = QgsMapLayerRegistry.instance().addMapLayers([vlayer])
        if intoDdGroup:
            groupIdx = self.getGroupIndex("DataDrivenInputMask")
            legendIface= self.iface.legendInterface()

            if groupIdx == -1:
                groupIdx = legendIface.addGroup("DataDrivenInputMask",  False)

            legendIface.moveLayer(vlayer,  groupIdx)
        return vlayer

    def quit(self):
        for ddLayer in self.ddLayers.values():
            db = ddLayer[1]
            self.__disconnectDb(db)

    #Slots
    def editingStarted(self):
        layer = self.iface.activeLayer()

        layerValues = self.__getLayerValues(layer)

        if layerValues != None:
            db = layerValues[1]

            if not db:
                db = self.__ceateDb(layer)
                self.setDb(layer,  db)

    def editingStopped(self):
        pass
        # better keep the connection, if too many connections exist we must change this
        #self.__disconnectDb(db)
        #self.setDb(layer,  None)

    def __getLayerValues(self,  layer):
        '''Get this layer's from ddLayers or create them'''
        try:
            layerValues = self.ddLayers[layer.id()]
        except KeyError:
            if self.initLayer(layer,  skip = []):
                layerValues = self.ddLayers[layer.id()]
            else:
                layerValues = None

        return layerValues

    def __getComment(self,  thisTable,  db):
        ''' query the DB to get a table's comment'''
        query = QtSql.QSqlQuery(db)
        sQuery = "SELECT description FROM pg_description \
        WHERE objoid = :oid AND objsubid = 0"
        # objsubid = 0 is the table, objsubid > 0 are comments on fields
        query.prepare(sQuery)
        query.bindValue(":oid", thisTable.oid)
        query.exec_()

        comment = None

        if query.isActive():
            if query.size() == 0:
                query.finish()
            else:
                while query.next():
                    comment = query.value(0)
                    break
                query.finish()
        else:
            DbError(query)

        return comment

    def __getOid(self,  thisTable,  db):
        ''' query the DB to get a table's oid'''
        query = QtSql.QSqlQuery(db)
        sQuery = "SELECT c.oid FROM pg_class c \
        JOIN pg_namespace n ON c.relnamespace = n.oid \
        WHERE n.nspname = :schema AND c.relname = :table"
        query.prepare(sQuery)
        query.bindValue(":schema", thisTable.schemaName)
        query.bindValue(":table", thisTable.tableName)
        query.exec_()

        oid = None

        if query.isActive():
            if query.size() == 0:
                query.finish()
            else:
                while query.next():
                    oid = query.value(0)
                    break
                query.finish()
        else:
            DbError(query)

        return oid

    def __isTable(self,  thisTable,  db):
        '''checks if the given relation is a table'''

        query = QtSql.QSqlQuery(db)
        sQuery = "SELECT * FROM pg_tables WHERE schemaname = :schema AND tablename = :table"
        query.prepare(sQuery)
        query.bindValue(":schema", thisTable.schemaName)
        query.bindValue(":table", thisTable.tableName)
        query.exec_()

        if query.isActive():
            if query.size() == 0:
                query.finish()
                return False
            else:
                query.finish()
                return True
        else:
            DbError(query)
            return False

    def __connectSignals(self,  layer):
        layer.editingStarted.connect(self.editingStarted)
        layer.editingStopped.connect(self.editingStopped)

    def __analyzeSource(self,  layer):
        '''Split the layer's source information and return them as a dict'''
        src = layer.source()
        srcList = src.split(' ')
        result = dict()

        for anElement in srcList:
            aPair = anElement.replace("'",  "").split("=")

            if 2 == len(aPair):
                result[aPair[0]] = aPair[1]

        return result

    def __connectDb(self,  qSqlDatabaseName,  host,  database,  port,  username,  passwd):
        '''connect to the PostgreSQL DB'''
        db = QtSql.QSqlDatabase.addDatabase ("QPSQL",  qSqlDatabaseName)
        db.setHostName(host)
        db.setPort(port)
        db.setDatabaseName(database)
        db.setUserName(username)
        db.setPassword(passwd)
        ok = db.open()

        if not ok:
            DdError(QtGui.QApplication.translate("DdError", "Could not connect to PostgreSQL database:", None,
                                                 QtGui.QApplication.UnicodeUTF8) + database)
            return None
        else:
            return db

    def __connectServiceDb(self,  qSqlDatabaseName,  service,  username,  passwd):
        '''connect to the PostgreSQL DB via pg_service'''
        db = QtSql.QSqlDatabase.addDatabase ("QPSQL",  qSqlDatabaseName)
        db.setConnectOptions("service=" + service)
        db.setUserName(username)
        db.setPassword(passwd)
        ok = db.open()

        if not ok:
            DdError(QtGui.QApplication.translate("DdError", "Could not connect to PostgreSQL database:", None,
                                                 QtGui.QApplication.UnicodeUTF8) + database)
            return None
        else:
            return db

    def __createDb(self,  layer):
        '''create a QtSql.QSqlDatabase object  for the DB-connection this layer comes from'''
        layerSrc = self.__analyzeSource(layer)

        try:
            service = layerSrc["service"]
            host = None
        except KeyError:
            try:
                host = layerSrc["host"]
            except KeyError:
                host = '127.0.0.1' # we assume localhost

            dbname = layerSrc["dbname"]

        try:
            user = layerSrc["user"]
        except KeyError:
            user,  ok = QtGui.QInputDialog.getText(None,  QtGui.QApplication.translate("DdWarning", "Username missing"),
                                                QtGui.QApplication.translate("DdWarning", "Enter username for ", None,
                                                QtGui.QApplication.UnicodeUTF8) + dbname + "." + host)
            if not ok:
                return None

        try:
            password =  layerSrc["password"]
        except KeyError:
            password,  ok = QtGui.QInputDialog.getText(None,  QtGui.QApplication.translate("DdWarning", "Password missing"),
                                                QtGui.QApplication.translate("DdWarning", "Enter password for ", None,
                                                QtGui.QApplication.UnicodeUTF8) + user + u"@" + dbname + host,
                                                QtGui.QLineEdit.Password)

            if not ok:
                return None

        if host == None:
            db = self.__connectServiceDb(layer.id(),  service, user, password)
        else:
            db = self.__connectDb(layer.id(), host ,  dbname,
                int(layerSrc["port"]),  user,
                password)
        return db

    def __disconnectDb(self,  db):
        '''disconnect from the DB'''
        if db:
            db.close()
            db = None

class DataDrivenUi(object):
    '''Creates the DataDrivenUi

    When subclassing this class, you want to rewrite createUi and use DdManager's setUi
    method to apply your custom ui to the layer'''

    def __init__(self,  iface):
        self.iface = iface

    def __str__(self):
        return "<ddui.DataDrivenUi>"

    def __createForms(self,  thisTable,  db,  skip,  labels,  fieldOrder,  minMax,  showParents,  showChildren):
        """create the forms (DdFom instances) shown in the tabs of  the Dialog (DdDialog instance)"""

        ddForms = []
        ddAttributes = self.getAttributes(thisTable, db,  labels,  minMax)

        for anAtt in ddAttributes:
            if anAtt.isPK:
                #QtGui.QMessageBox.information(None, "debug",  anAtt.name + " isPK")
                n2mAttributes = self.getN2mAttributes(db,  thisTable,  anAtt.name,  anAtt.num,  labels,  showChildren)
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
                    #QtGui.QMessageBox.information(None, "debug",  "skipping " + anAttribute.name)
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
            #QtGui.QMessageBox.information(None, "attribute",  anAttribute.name)

        ddFormWidget = DdFormWidget(thisTable,  needsToolBox)

        for anAttribute in orderedAttributes:
            #QtGui.QMessageBox.information(None, "orderedAttribute",  anAttribute.name)
            if anAttribute.type == "text":
                ddInputWidget = DdTextEdit(anAttribute)
            elif anAttribute.type == "n2m":

                if anAttribute.subType == "list":
                    ddInputWidget = DdN2mListWidget(anAttribute)
                elif anAttribute.subType == "tree":
                    ddInputWidget = DdN2mTreeWidget(anAttribute)
            elif anAttribute.type == "table":
                ddInputWidget = DdN2mTableWidget(anAttribute)
            else: # on line attributes
                if anAttribute.isFK:
                    ddInputWidget = DdComboBox(anAttribute)
                else:
                    if anAttribute.isTypeFloat():
                        ddInputWidget = DdLineEditDouble(anAttribute)
                    elif anAttribute.isTypeInt():
                        ddInputWidget = DdLineEditInt(anAttribute)
                    else:
                        if anAttribute.type == "bool":
                            ddInputWidget = DdCheckBox(anAttribute)
                        elif anAttribute.type == "date":
                            ddInputWidget = DdDateEdit(anAttribute)
                        else:
                            ddInputWidget = DdLineEdit(anAttribute)

            ddFormWidget.addInputWidget(ddInputWidget)

        ddForms.append(ddFormWidget)

        #QtGui.QMessageBox.information(None, "attributes for",  thisTable.tableName + ": \n" + msg)

        if showParents:
            # do not show this table in the parent's form
            skip.append(thisTable.tableName)
            # go recursivly into thisTable's parents
            for aParent in self.getParents(thisTable,  db):
                parentForms = self.__createForms(aParent,  db,  skip,  labels,  fieldOrder,  minMax,  showParents,  False)
                ddForms = ddForms + parentForms

        return ddForms

    def createUi(self,  thisTable,  db,  skip = [],  labels = {},  fieldOrder = [],  minMax = {},  showParents = True,  showChildren = True):
        '''creates a default ui for this table (DdTable instance)
        skip is an array with field names to not show
        labels is a dict with entries: "fieldname": "label"
        fieldOrder is an array containing the field names in the order they should be shown
        minMax is a dict with entries: "fieldname": [min, max] (use for numerical fields only!'''

        ui = DdDialogWidget()
        forms = self.__createForms(thisTable,  db,  skip,  labels,  fieldOrder,  minMax,  showParents,  showChildren)

        for ddFormWidget in forms:
            ui.addFormWidget(ddFormWidget)

        return ui

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

        #myParents = "myParents:"
        #for aParent in parents:
        #    myParents = myParents + " " + aParent.tableName

        #QtGui.QMessageBox.information(None, "getParents",  "called with " + thisTable.tableName + "\n" + myParents)

        return parents

    def getN2mAttributes(self,  db,  thisTable,  attName,  attNum,  labels,  showChildren):
        '''find those tables (n2mtable) where our pk is a fk'''
        #QtGui.QMessageBox.information(None, "Debug", "getN2mAttributes:" + thisTable.tableName)
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
        #QtGui.QMessageBox.information(None, str(attNum), str(thisTable.oid))
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
                                    #QtGui.QMessageBox.information(None, "relatedQuery.size()", str(relatedQuery.size()))
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
                                            #QtGui.QMessageBox.information(None, "Debug", "tree: " + relatedSchema + "." + relatedTable + "." + relationRelatedIdField)

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

                if subType == "table":
                    attributes = self.getAttributes(ddRelationTable,  db,  {},  {})
                    ddAtt = DdTableAttribute(ddRelationTable,  relationComment,  attLabel, relationFeatureIdField,  attributes,  maxRows,  showParents)
                else:
                    ddAtt = DdN2mAttribute(ddRelationTable,  ddRelatedTable,  \
                                       subType,  relationComment,  attLabel,  \
                                       relationFeatureIdField, relationRelatedIdField,  relatedIdField,  relatedDisplayField,  fieldList)

                n2mAttributes.append(ddAtt)
            pkQuery.finish()
        else:
            DbError(pkQuery)

        return n2mAttributes

    def getAttributes(self,  thisTable, db,  labels,  minMax):
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
                    attNum = query.value(1)
                    attNotNull = query.value(2)
                    attHasDefault = query.value(3)
                    attIsChild = query.value(4)
                    attLength = query.value(5)
                    attTyp = query.value(6)
                    attComment = query.value(7)
                    attDefault = query.value(8)

                    if not self.isSupportedType(attTyp):
                        continue

                    attConstraint = query.value(9)
                    constrainedAttNums = query.value(10)
                    isPK = attConstraint == "p" # PrimaryKey

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
                            fk = foreignKeys[attNum]

                            try:
                                attLabel = labels[str(attName)]
                            except KeyError:
                                attLabel = attName + " (" + fk[2] + ")"

                            try:
                                fkComment = fk[3]
                            except IndexError:
                                #QtGui.QMessageBox.information(None, "",  "no fkComment for " + attName)
                                fkComment = ""

                            if attComment == "":
                                attComment = fkComment
                            else:
                                if not fkComment == "":
                                    attComment = attComment + "\n(" + fkComment + ")"

                            ddAtt = DdFkLayerAttribute(thisTable,  attTyp,  attNotNull,  attName,  attComment,  attNum,  isPK, attDefault,  attHasDefault,  fk[1],  attLabel)
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
                            ddAtt = DdLayerAttribute(thisTable,  attTyp,  attNotNull,  attName,  attComment,  attNum,  isPK,
                                                     False,  attDefault,  attHasDefault,  attLength,  attLabel)
                        else:
                            ddAtt = DdLayerAttribute(thisTable,  attTyp,  attNotNull,  attName,  attComment,  attNum,  isPK,
                                                     False,  attDefault,  attHasDefault,  attLength,  attLabel,  thisMinMax[0],  thisMinMax[1])

                    ddAttributes.append(ddAtt)

                query.finish()
        else:
            DbError(query)

        return ddAttributes

    def isSupportedType(self,  typ):
        supportedAttributeTypes = ["int2", "int4",  "int8",  "char",  "varchar",  "float4", "float8",  "text",  "bool",  "date"]
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
                att.attnum, \
                t.typname as typ, \
                CAST(valatt.attnotnull as integer) as notnull, \
                valatt.attname, \
                ((((((('SELECT ' || quote_ident(valatt.attname)) || ' as value, ')  || quote_ident(refatt.attname)) || ' as key FROM ') || quote_ident(ns.nspname)) || '.') || quote_ident(c.relname)) || ';' AS sql_key, \
                ((((((('SELECT ' || quote_ident(refatt.attname)) || ' as value, ')  || quote_ident(refatt.attname)) || ' as key FROM ') || quote_ident(ns.nspname)) || '.') || quote_ident(c.relname)) || ';' AS default_sql, \
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
                attNum = query.value(0)
                fieldType = query.value(1)
                notNull = query.value(2)
                valAttName = query.value(3)
                keySql = query.value(4)
                defaultSql = query.value(5)
                comment = query.value(6)
                contype = query.value(7)

                if contype == "f":
                    continue

               # QtGui.QMessageBox.information(None, "",  str(attNum) + ": " + fieldType + " " + valAttName + " " + keySql)
                try:
                    fk = foreignKeys[attNum]
                    if fk[0] != "varchar": # we do not already have a varchar field as value field
                    # find a field with a suitable type
                        if notNull and (fieldType == "varchar" or fieldType == "char"):
                            foreignKeys[attNum] = [fieldType,  keySql,  valAttName,  comment]
                except KeyError:
                    if notNull and (fieldType == "varchar" or fieldType == "char"):
                        foreignKeys[attNum] = [fieldType,  keySql,  valAttName]
                    else: # put the first in
                        foreignKeys[attNum] = [fieldType,  defaultSql,  valAttName,  comment]

            query.finish()
        else:
            DbError(query)

        return foreignKeys

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
        COALESCE(con.conkey, ARRAY[]::smallint[]) as constrained_columns \
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

    def checkInput(self):
        '''check if input is valid
        returns True if not implemented in child class'''
        return True

    def setupUi(self,  parent,  db):
        '''create the ui
        must be implemented in child classes'''
        raise NotImplementedError("Should have implemented setupUi")

    def initialize(self,  layer,  feature,  db):
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

    def debug(self,  msg):
        QtGui.QMessageBox.information(None, "debug",  unicode(msg))

class DdDialogWidget(DdWidget):
    '''This is the mask ui'''
    def __init__(self):
        DdWidget.__init__(self)
        self.forms = []

    def __str__(self):
        return "<ddui.DdDialogWidget>"

    def setupUi(self,  ddDialog,  db): # ddDialog is a child of QDialog
        self.layout = QtGui.QVBoxLayout(ddDialog)
        self.layout.setObjectName("layout")
        self.mainTab = QtGui.QTabWidget(ddDialog)
        self.mainTab.setObjectName("mainTab")
        ddDialog.setObjectName("DataDrivenInputMask")
        ddDialog.setWindowModality(QtCore.Qt.ApplicationModal)

        for i in range(len(self.forms)):
            aTab = QtGui.QWidget(self.mainTab)
            aTab.setObjectName("tab" + str(i))
            aForm = self.forms[i]

            if aForm.hasToolBox:
                tabLayout = QtGui.QVBoxLayout(aTab)
            else:
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

        self.layout.addWidget(self.mainTab)
        self.buttonBox = QtGui.QDialogButtonBox(ddDialog)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtGui.QDialogButtonBox.Cancel|QtGui.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName("buttonBox")
        self.layout.addWidget(self.buttonBox)

        self.mainTab.setCurrentIndex(0)
        self.buttonBox.accepted.connect(ddDialog.accept)
        self.buttonBox.rejected.connect(ddDialog.reject)
        #QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL("accepted()"), ddDialog.accept)
        #QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL("rejected()"), ddDialog.reject)
        QtCore.QMetaObject.connectSlotsByName(ddDialog)

    def addFormWidget(self,  ddFormWidget):
        '''add this DdFormWidget to the ui'''
        self.forms.append(ddFormWidget)

    def initialize(self,  layer,  feature,  db):
        for aForm in self.forms:
            aForm.initialize(layer,  feature,  db)

    def checkInput(self):
        inputOk = True
        for aForm in self.forms:
            if not aForm.checkInput():
                inputOk = False
                break

        return inputOk

    def save(self,  layer,  feature,  db):
        hasChanges = False
        for aForm in self.forms:
            if aForm.save(layer,  feature,  db):
                hasChanges = True

        return hasChanges

    def discard(self):
        for aForm in self.forms:
            aForm.discard()

class DdFormWidget(DdWidget):
    '''DdForms are the content of DdDialog, each DdDialog needs at least one DdForm (tab).
    The class arranges its input widgets either in a QToolBox or in the DdDialogWidget's current tab'''

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
        pParent = self.parent

        while (True):
            pParent = pParent.parentWidget()
            #QtGui.QMessageBox.information(None, "pParent",  str(parent) + "" + str(pParent))

            if isinstance(pParent,  DdDialog):
                self.parentDialog = pParent
                break

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
                QtGui.QMessageBox.warning(None, "",  QtGui.QApplication.translate("DdWarning", "Layer cannot be put in editing mode:", None,
                                                           QtGui.QApplication.UnicodeUTF8)) + " %s"% str(self.layer.name())

        return ok

    def setupUi(self,  parent,  db):
        #QtGui.QMessageBox.information(None, "DdFormWidget setupUi", parent.objectName())
        self.parent = parent
        sorted = False
        labels = []
        for ddInputWidget in self.inputWidgets:
            labels.append(ddInputWidget.getLabel())

        if sorted:
            labels.sort()

        if self.hasToolBox:
            scrollArea = QtGui.QScrollArea(parent)
            scrollArea.setWidgetResizable(True)
            scrollArea.setObjectName(parent.objectName() + "_scrollArea")
            scrollAreaWidgetContents = QtGui.QWidget(parent)
            scrollAreaWidgetContents.setObjectName(parent.objectName() + "_scrollAreaWidgetContents")
            formLayout = QtGui.QFormLayout(scrollAreaWidgetContents)

            for label in labels:
                for anWidget in self.inputWidgets:
                    if anWidget.getLabel() == label:
                        ddInputWidget = anWidget
                        break
                #QtGui.QMessageBox.information(None, "",  str(ddInputWidget))
                ddInputWidget.setupUi(scrollAreaWidgetContents,  db)

            scrollArea.setWidget(scrollAreaWidgetContents)
            parent.layout().addWidget(scrollArea)
        else:
            for label in labels:
                for anWidget in self.inputWidgets:
                    if anWidget.getLabel() == label:
                        ddInputWidget = anWidget
                        break
                ddInputWidget.setupUi(parent,  db)

        self.layer = self.__getLayer(db)

    def addInputWidget(self,  ddInputWidget):
        '''insert this DdInputWidget into this DdForm'''
        #QtGui.QMessageBox.information(None,  "addInputWidget",  ddInputWidget.attribute.name)
        self.inputWidgets.append(ddInputWidget)

    def initialize(self,  layer,  feature,  db):
        self.oldSubsetString = ""

        if layer.id() == self.layer.id():
            self.feature = feature
            self.wasEditable = layer.isEditable()
        else:
            layerPkList = layer.pendingPkAttributesList()

            if len(layerPkList) != 1:
                self.feature = None # no combined keys
            else:
                layerPkIdx = layerPkList[0]
                pkValue = feature[layerPkIdx]

                if pkValue == None:
                    self.feature = None
                else:
                    pkValue = str(pkValue)
                    thisPkList = self.layer.pendingPkAttributesList()

                    if len(thisPkList) != 1:
                        self.feature = None
                    else:
                        self.oldSubsetString = self.layer.subsetString()
                        thisPkField = self.layer.pendingFields().field(thisPkList[0])

                        if thisPkField.typeName().find("char") != -1:
                            pkValue = "\'" + pkValue + "\'" # quote value as string

                        newSubsetString = "\"" + thisPkField.name() + "\"=" + pkValue
                        self.layer.setSubsetString(newSubsetString)
                        self.layer.reload()

                        if self.layer.featureCount() != 1:
                            # there is no or several features matching our feature
                            self.feature = None
                        else:
                            self.feature = QgsFeature()
                            featureFound = self.layer.getFeatures(QgsFeatureRequest().setFlags(QgsFeatureRequest.NoGeometry)).nextFeature(self.feature)

                            if layer.isEditable():
                                self.parent.setEnabled(self.__setLayerEditable())

        if self.feature:
            for anInputWidget in self.inputWidgets:
                anInputWidget.initialize(self.layer,  self.feature,  db)
        else:
            self.parent.setEnabled(False)

        #QtGui.QMessageBox.information(None,  "initializing Form",  "passed layer: "+ layer.name() + "\n self.layer: " + self.layer.name() + "\n self.ddTable: " + self.ddTable.tableName + "\n self.feature: " + str(self.feature) + "\n self.parent.isEnabled: " + str(self.parent.isEnabled()))

    def checkInput(self):
        inputOk = True

        if self.parent.isEnabled(): #only check if the tab is enbaled, e.g. parents are not enabled if this is a new feature
            for anInputWidget in self.inputWidgets:
                if not anInputWidget.checkInput():
                    inputOk = False
                    break

        return inputOk

    def save(self,  layer,  feature,  db):
        hasChanges = False
        if self.parent.isEnabled():
            for anInputWidget in self.inputWidgets:
                if anInputWidget.save(self.layer,  self.feature,  db):
                    hasChanges = True

        if hasChanges:
            if not self.layer.commitChanges():
                DdError(QtGui.QApplication.translate("DdError", "Could not save changes for layer:", None,
                                                   QtGui.QApplication.UnicodeUTF8) + self.layer.name())
        else:
            if not self.layer.rollBack():
                DdError(QtGui.QApplication.translate("DdError", "Could not discard changes for layer:", None,
                                                   QtGui.QApplication.UnicodeUTF8) + self.layer.name())
        if self.wasEditable:
            self.layer.startEditing()

        # reset previous subset string
        self.layer.setSubsetString(self.oldSubsetString)
        return hasChanges

    def discard(self):
        if self.parent.isEnabled():
            if self.layer.isEditable():
                for anInputWidget in self.inputWidgets:
                    anInputWidget.discard()
                if not self.layer.rollBack():
                    DdError(QtGui.QApplication.translate("DdError", "Could not discard changes for layer:", None,
                                                   QtGui.QApplication.UnicodeUTF8) + self.layer.name())
                if self.wasEditable:
                    self.layer.startEditing()

        # reset previous subset string
        self.layer.setSubsetString(self.oldSubsetString)

class DdInputWidget(DdWidget):
    '''abstract super class for any input widget, corresponds to a DdAttribute'''

    def __init__(self,  ddAttribute):
        DdWidget.__init__(self)
        self.attribute = ddAttribute
        self.hasChanges = False

    def __str__(self):
        return "<ddui.DdInputWidget %s>" % str(self.attribute.name)

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

class DdLineEdit(DdInputWidget):
    '''abstract class for all Input Widgets that can be represented in one line,
    creates a QLineEdit as default InputWidget, adds it together with a QCheckBox (to store null values)
    and a label to a QFormLayout.'''

    def __init__(self,  attribute):
        DdInputWidget.__init__(self,  attribute)

    def __str__(self):
        return "<ddui.DdOneLineInputWidget %s>" % str(self.attribute.name)

    def getFeatureValue(self,  layer,  feature,  db):
        '''returns a str representing the value in this field for this feature;
        if the value is null, None is returned,
        if it is a new feature the default value is returned if available.'''

        fieldIndex = self.getFieldIndex(layer)
        thisValue = feature[fieldIndex]

        if feature.id() < 0 and thisValue == None: # new feature
            if self.attribute.hasDefault:
                thisValue = self.attribute.default

        return thisValue

    def createInputWidget(self,  parent):
        inputWidget = QtGui.QLineEdit(parent) # defaultInputWidget
        inputWidget.setObjectName("txl" + parent.objectName() + self.attribute.name)
        inputWidget.textChanged.connect(self.registerChange)
        return inputWidget

    def manageChk(self,  thisValue):
        '''check/uncheck the null checkbox depending on the value and
        the attribute's notNull property'''

        if self.attribute.notNull: # uncheck in order to make inputWidget editable
            self.chk.setChecked(False)
        else:
            self.chk.setChecked(thisValue == None)

    # public methods
    def setValue(self,  thisValue):
        '''sets thisValue into the input widget'''
        self.manageChk(thisValue)

        if thisValue == None:
            thisValue = ""

        self.inputWidget.setText(unicode(thisValue))

    def getValue(self):
        if self.chk.isChecked():
            thisValue = None
        else:
            thisValue = self.inputWidget.text()

            if thisValue == "":
                thisValue = None

        #QtGui.QMessageBox.information(None,  "DdLineEdit",  "getValue " + self.attribute.label  + " " + str(thisValue))
        return thisValue

    def setupUi(self,  parent,  db):
        '''setup the label and add the inputWidget to parents formLayout'''
        #QtGui.QMessageBox.information(None,  "DdLineEdit",  "setupUi " + self.attribute.name)
        self.label = self.createLabel(parent)
        self.inputWidget = self.createInputWidget(parent)
        self.inputWidget.setToolTip(self.attribute.comment)
        hLayout = QtGui.QHBoxLayout(parent)
        hLayout.addWidget(self.inputWidget)
        self.chk = QtGui.QCheckBox(QtGui.QApplication.translate("DdInfo", "Null", None,
                                                           QtGui.QApplication.UnicodeUTF8),  parent)
        self.chk.setObjectName("chk" + parent.objectName() + self.attribute.name)
        self.chk.setToolTip(QtGui.QApplication.translate("DdInfo", "Check this if you want to save an empty (or null) value.", None,
                                                           QtGui.QApplication.UnicodeUTF8))
        self.chk.stateChanged.connect(self.chkStateChanged)
        self.chk.setVisible(not self.attribute.notNull)
        hLayout.addWidget(self.chk)
        parent.layout().addRow(self.label,  hLayout)

    def chkStateChanged(self,  newState):
        '''slot: disables the input widget if the null checkbox is checked and vice versa'''
        self.inputWidget.setEnabled(newState == QtCore.Qt.Unchecked)
        self.hasChanges = True

    def initialize(self,  layer,  feature,  db):
        thisValue = self.getFeatureValue(layer,  feature,  db)
        self.setValue(thisValue)
        self.hasChanges = (feature.id() < 0) # register this change only for new feature

    def checkInput(self):
        thisValue = self.getValue()
        #QtGui.QMessageBox.information(None, "checkInput",  self.attribute.name + " " + str(thisValue))
        if self.attribute.notNull and not thisValue:
            QtGui.QMessageBox.warning(None, self.label.text(),  QtGui.QApplication.translate("DdWarning", "Field must not be empty!", None,
                                                           QtGui.QApplication.UnicodeUTF8) )
            return False
        else:
            return True

    def getFieldIndex(self,  layer):
        '''return the field index for this DdInputWidget's attribute's name in this layer'''
        #QtGui.QMessageBox.information(None, "getFieldIndex",  "layer: " + layer.name() + " attribute: " + self.attribute.name)
        if layer:
            fieldIndex = layer.fieldNameIndex(self.attribute.name)
        else:
            fieldIndex = self.attribute.num

        if fieldIndex == -1:
            DdError(QtGui.QApplication.translate("DdError", "Field not found in layer: ", None,
                                                           QtGui.QApplication.UnicodeUTF8) + layer.name() + "." + self.attribute.name)
        return fieldIndex

    def save(self,  layer,  feature,  db):
        thisValue = self.getValue()
        fieldIndex = self.getFieldIndex(layer)

        if self.hasChanges:
            layer.changeAttributeValue(feature.id(),  fieldIndex,  thisValue,  False)

        return self.hasChanges

class QInt64Validator(QtGui.QValidator):
    '''a QValidator for int64 values'''
    def __init__(self,  parent = None):
        QtGui.QValidator.__init__(self,  parent)
        self.min = -9223372036854775808
        self.max = 9223372036854775807

    def validate(self, input, pos):
        thisLong = int(input)

        if self.min < thisLong and self.max > thisLong:
            return QtGui.QValidator.Acceptable,  pos
        else:
            return QtGui.QValidator.Invalid,  pos


class DdLineEditInt(DdLineEdit):
    '''input widget (QLineEdit) for an IntegerValue'''

    def __init__(self,  attribute):
        DdLineEdit.__init__(self,  attribute)

    def __str__(self):
        return "<ddui.DdLineEditInt %s>" % str(self.attribute.name)

    def getFeatureValue(self,  layer,  feature,  db):
        fieldIndex = self.getFieldIndex(layer)
        thisValue = feature[fieldIndex]

        if feature.id() < 0 and thisValue == None: # new feature and no value set
            if self.attribute.hasDefault:
                thisValue = self.attribute.default
            else:
                if self.attribute.isPK :
                    thisValue = self.getMaxValueFromTable(self.attribute.table.schemaName,  self.attribute.table.tableName,  db) + 1
                    thisValue = str(thisValue)

        return thisValue

    def setValidator(self):
        '''sets an appropriate QValidator for the QLineEdit
        if this DdInputWidget's attribute has min/max values validator is set to them'''
        if self.attribute.min != None or self.attribute.max != None:
            validator = QtGui.QIntValidator(self.attribute.min,  self.attribute.max,  self.inputWidget)
        else:
            validator = QInt64Validator(self.inputWidget)

        self.inputWidget.setValidator(validator)

    def initialize(self,  layer,  feature,  db):
        DdLineEdit.initialize(self,  layer,  feature,  db)
        thisValue = self.getValue()

        if thisValue == None:
            self.setValidator()
        else:
            isInt = isinstance(thisValue,  int)

            if not  isInt: # could be a Longlong, or a serial, i.e. a nextval(sequence) expression
                isInt = isinstance(thisValue,  long)

                if not  isInt:
                    self.inputWidget.setValidator(None) # remove the validator

            self.setValue(thisValue)

            if isInt:
                self.setValidator()

class DdLineEditDouble(DdLineEdit):
    '''input widget (QLineEdit) for a DoubleValue'''

    def __init__(self,  attribute):
        DdLineEdit.__init__(self,  attribute)
        #QtGui.QMessageBox.information(None,  "DdLineEditDouble",  "init " + self.attribute.name)

    def __str__(self):
        return "<ddui.DdLineEditDouble %s>" % str(self.attribute.name)

    def setValue(self,  thisValue):
        self.manageChk(thisValue)

        if thisValue == None:
            thisValue = ""
        else:
            # convert double to a locale string representation
            thisDouble,  ok = thisValue.toDouble()

            if ok:
                loc = QtCore.QLocale.system()
                thisValue = loc.toString(thisDouble)
            else:
                thisValue = ""

        self.inputWidget.setText(thisValue)

    def getValue(self):
        if self.chk.isChecked():
            thisValue = None
        else:
            thisValue = self.inputWidget.text()

            if thisValue == "":
                thisValue = None
            else:
                loc = QtCore.QLocale.system()
                thisDouble = loc.toDouble(thisValue)

                if thisDouble[1]:
                    thisValue = str(thisDouble[0])
                else:
                    thisValue = None

        return thisValue

    def setValidator(self):
        '''sets an appropriate QValidator for the QLineEdit
        if this DdInputWidget's attribute has min/max values validator is set to them'''
        validator = QtGui.QDoubleValidator(self.inputWidget)

        if self.attribute.min != None:
            validator.setBottom(self.attribute.min)

        if self.attribute.max != None:
            validator.setTop(self.attribute.max)

        validator.setNotation(QtGui.QDoubleValidator.StandardNotation)
        validator.setLocale(QtCore.QLocale.system())
        self.inputWidget.setValidator(validator)

    def __textChanged(self,  thisValue):
        loc = QtCore.QLocale.system()
        thisDouble = loc.toDouble(thisValue)

        if not thisDouble[1]:
            QtGui.QMessageBox.warning(None, self.label.text(),  QtGui.QApplication.translate("DdWarning", "Input in Field is not a double according to local settings! ", None,
                                                           QtGui.QApplication.UnicodeUTF8))

    def setupUi(self,  parent,  db):
        #QtGui.QMessageBox.information(None,  "DdLineEditFloat",  "setupUi " + self.attribute.name)
        DdLineEdit.setupUi(self,  parent,  db)
        self.setValidator()
        self.inputWidget.textChanged.connect(self.__textChanged)

class DdLineEditChar(DdLineEdit):
    '''input widget (QLineEdit) for a char or varchar'''

    def __init__(self,  attribute):
        DdLineEdit.__init__(self,  attribute)

    def __str__(self):
        return "<ddui.DdLineEditChar %s>" % str(self.attribute.name)

    def checkInput(self):
        ok = DdLineEdit.checkInput()

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

    def __str__(self):
        return "<ddui.DdComboBox %s>" % str(self.attribute.name)

    def getFeatureValue(self,  layer,  feature,  db):
        '''returns a value representing the value in this field for this feature'''

        fieldIndex = self.getFieldIndex(layer)
        thisValue = feature[fieldIndex] #returns None if empty

        if  feature.id() < 0 and thisValue == None: # new feature and no value set
            if self.attribute.hasDefault:
                if self.attribute.isTypeInt():
                    thisValue = int(self.attribute.default)
                elif self.attribute.isTypeChar():
                    thisValue = self.attribute.default

        return thisValue

    def createInputWidget(self,  parent):
        inputWidget = QtGui.QComboBox(parent) # defaultInputWidget
        inputWidget.setObjectName("cbx" + parent.objectName() + self.attribute.name)
        inputWidget.currentIndexChanged.connect(self.registerChange)
        return inputWidget

    def fill(self,  db):
        '''fill the QComboBox with values according to the attribute from the db'''
        query = QtSql.QSqlQuery(db)
        query.prepare(self.attribute.queryForCbx)
        query.exec_()

        if query.isActive():
            self.inputWidget.clear()

            while query.next(): # returns false when all records are done
                sValue = query.value(0)

                if not isinstance(sValue,  unicode):
                    sValue = str(sValue)

                keyValue = query.value(1)
                self.inputWidget.addItem(sValue, keyValue)

            query.finish()
        else:
            DbError(query)

    def setValue(self,  thisValue):
        self.manageChk(thisValue)

        if not thisValue:
            self.inputWidget.setCurrentIndex(0)
        else:
            for i in range(self.inputWidget.count()):
                if self.inputWidget.itemData(i) == thisValue:
                    self.inputWidget.setCurrentIndex(i)
                    break

    def getValue(self):
        if self.chk.isChecked():
            thisValue = None
        else:
            thisValue = self.inputWidget.itemData(self.inputWidget.currentIndex())

        return thisValue

    def setupUi(self,  parent,  db):
        #QtGui.QMessageBox.information(None,  "DdLineEdit",  "setupUi " + self.attribute.name)
        DdLineEdit.setupUi(self,  parent,  db)
        self.fill(db)

class DdDateEdit(DdLineEdit):
    '''input widget (QDateEdit) for a date field'''

    def __init__(self,  attribute):
        DdLineEdit.__init__(self,  attribute)

    def __str__(self):
        return "<ddui.DdDateEdit %s>" % str(self.attribute.name)

    def getFeatureValue(self,  layer,  feature,  db):
        '''returns a QDate representing the value in this field for this feature'''

        fieldIndex = self.getFieldIndex(layer)
        thisValue = feature[fieldIndex]

        if thisValue == None:
            if feature.id() < 0 and self.attribute.hasDefault:
                thisValue = self.attribute.default.toDate()
            else:
                if self.attribute.notNull:
                    thisValue = QtCore.QDate.currentDate()

        return thisValue

    def createInputWidget(self,  parent):
        inputWidget = QtGui.QDateEdit(parent)
        inputWidget.setCalendarPopup(True)
        inputWidget.setDisplayFormat("dd.MM.yyyy")
        inputWidget.setObjectName("dat" + parent.objectName() + self.attribute.name)
        inputWidget.setToolTip(self.attribute.comment)
        inputWidget.dateChanged.connect(self.registerChange)
        return inputWidget

    def setValue(self,  thisValue):
        self.manageChk(thisValue)

        if not thisValue: # i.e. None
            self.inputWidget.setDate(QtCore.QDate.currentDate())
        else:
            self.inputWidget.setDate(thisValue)

    def getValue(self):
        if self.chk.isChecked():
            thisValue = None
        else:
            thisValue = self.inputWidget.date()

        return thisValue

class DdCheckBox(DdLineEdit):
    '''input widget (QCheckBox) for a boolean field'''

    def __init__(self,  attribute):
        DdLineEdit.__init__(self,  attribute)

    def __str__(self):
        return "<ddui.DdCheckBox %s>" % str(self.attribute.name)

    def getFeatureValue(self,  layer,  feature,  db):
        '''returns a boolean representing the value in this field for this feature'''

        fieldIndex = self.getFieldIndex(layer)
        thisValue = feature[fieldIndex]

        if thisValue:
            if thisValue == "f" or thisValue == "false" or thisValue == "False":
                thisValue = False
            else:
                thisValue = True

        if feature.id() < 0 and thisValue == None: # new feature and no value set
            if self.attribute.hasDefault:
                thisValue = bool(self.attribute.default)

        return thisValue

    def createInputWidget(self,  parent):
        inputWidget = QtGui.QCheckBox(parent)
        inputWidget.setObjectName("chk" + parent.objectName() + self.attribute.name)
        inputWidget.stateChanged.connect(self.registerChange)
        return inputWidget

    def setValue(self,  thisValue):
        self.manageChk(thisValue)

        if None == thisValue: #handle Null values
            self.inputWidget.setCheckState(0) # false
        else:
            self.inputWidget.setChecked(thisValue)

    def stateChanged(self,  newState):
        '''slot if this QCheckBox' state has changed'''
        if self.inputWidget.isTristate() and newState != 1:
            self.inputWidget.setTristate(False)

    def getValue(self):
        if self.chk.isChecked():
            thisValue = None
        else:
            state = self.inputWidget.checkState()
            #QtGui.QMessageBox.information(None, "", str(state))
            if state == 0:
                thisValue = False

            elif state == 2:
                thisValue = True

        return thisValue

    def checkInput(self):
        thisValue = self.getValue()

        if self.attribute.notNull and thisValue == None:
            QtGui.QMessageBox.warning(None, self.label.text(),  QtGui.QApplication.translate("DdWarning", "Field must not be empty!", None,
                                                           QtGui.QApplication.UnicodeUTF8) )
            return False
        else:
            return True

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
        return inputWidget

    def setValue(self,  thisValue):
        self.manageChk(thisValue)

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
        self.featureId = None
        self.forEdit = False

    def setupUi(self,  parent,  db):
        label = self.createLabel(parent)
        self.inputWidget = self.createInputWidget(parent)
        self.inputWidget.setToolTip(self.attribute.comment)
        parent.layout().addRow(label)
        parent.layout().addRow(self.inputWidget)
        pParent = parent

        while (True):
            pParent = pParent.parentWidget()

            if isinstance(pParent,  DdDialog):
                self.parentDialog = pParent
                break

    def initializeLayer(self,  layer,  feature,  db,  doShowParents = False):
        # find the layer in the project
        self.tableLayer = self.parentDialog.ddManager.findPostgresLayer(db,  self.attribute.table)

        if not self.tableLayer:
            # load the layer into the project
            self.tableLayer = self.parentDialog.ddManager.loadPostGISLayer(db,  self.attribute.table)

        #QtGui.QMessageBox.information(None, "setupUi",  self.attribute.name + ": " + self.tableLayer.name())
        # create a DdUi for the layer without the featureIdField it it has not yet been created
        try:
            self.parentDialog.ddManager.ddLayers[self.tableLayer.id()]
        except KeyError:
            self.parentDialog.ddManager.initLayer(self.tableLayer,  skip = [self.attribute.relationFeatureIdField],  showParents = doShowParents)

        self.featureId = feature.id()

        # reduce the features in self.tableLayer to those related to feature
        subsetString = self.attribute.subsetString
        subsetString += str(self.featureId)
        #QtGui.QMessageBox.information(None, "",  subsetString + "\n" + self.attribute.name)
        self.tableLayer.setSubsetString(subsetString)
        self.tableLayer.reload()

        self.forEdit = self.featureId > 0
        if self.forEdit:
            self.forEdit = layer.isEditable()
            if self.forEdit:
                self.forEdit = self.tableLayer.isEditable()

                if not self.forEdit:
                    self.forEdit = self.tableLayer.startEditing()

                    if not self.forEdit:
                        QtGui.QMessageBox.Warning(None,  "", QtGui.QApplication.translate("DdInfo", "Layer cannot be edited: ", None,
                                                                   QtGui.QApplication.UnicodeUTF8) + self.tableLayer.name())

    def createFeature(self, fid = None):
        '''create a new QgsFeature for the relation table with this fid'''
        if fid:
            newFeature = QgsFeature(fid)
        else:
            newFeature = QgsFeature() # gid wird automatisch vergeben

        provider = self.tableLayer.dataProvider()
        fields = self.tableLayer.pendingFields()
        newFeature.initAttributes(fields.count())
        for i in range(fields.count()):
            newFeature.setAttribute(i,provider.defaultValue(i))

        return newFeature

    def save(self,  layer,  feature,  db):
        if self.hasChanges:
            if self.tableLayer.isEditable():
                if self.tableLayer.isModified():
                    if self.tableLayer.commitChanges():
                        return True
                    else:
                        DdError(QtGui.QApplication.translate("DdError", "Could not save changes to layer: ", None,
                                                                   QtGui.QApplication.UnicodeUTF8)  + self.tableLayer.name())
                        self.discard()
                else:
                    self.discard()
        else:
            self.discard()
        return False

    def discard(self):
        if self.tableLayer.isEditable():
            if not self.tableLayer.rollBack():
                DdError(QtGui.QApplication.translate("DdError", "Could not discard changes for layer:", None,
                                                   QtGui.QApplication.UnicodeUTF8) + self.tableLayer.name())
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

            if thisItem.checkState(0) == 2:
                feat = self.createFeature()
                feat.setAttribute(featureIdField,  self.featureId)
                feat.setAttribute(relatedIdField,  itemId)
                self.tableLayer.addFeature(feat,  False)
            else:
                self.tableLayer.selectAll()

                for aFeature in self.tableLayer.selectedFeatures():
                    if aFeature[featureIdField] == self.featureId:
                        if aFeature[relatedIdField] == itemId:
                            idToDelete = aFeature.id()
                            self.tableLayer.deleteFeature(idToDelete)
                            break
            self.hasChanges = True

    def createInputWidget(self,  parent):
        inputWidget = QtGui.QListWidget(parent) # defaultInputWidget
        inputWidget.setObjectName("lst" + parent.objectName() + self.attribute.name)
        inputWidget.itemChanged.connect(self.registerChange)
        return inputWidget

    def initialize(self,  layer,  feature,  db):
        self.initializeLayer(layer,  feature,  db)
        query = QtSql.QSqlQuery(db)
        query.prepare(self.attribute.displayStatement)
        query.bindValue(":featureId", feature.id())
        query.exec_()

        if query.isActive():
            self.inputWidget.clear()
            self.inputWidget.itemChanged.disconnect(self.registerChange)
            while query.next(): # returns false when all records are done
                parentId = int(query.value(0))
                parent = unicode(query.value(1))
                checked = int(query.value(2))
                parentItem = QtGui.QListWidgetItem(parent)
                parentItem.id = parentId
                parentItem.setCheckState(checked)
                self.inputWidget.addItem(parentItem)
            query.finish()
            self.inputWidget.itemChanged.connect(self.registerChange)
        else:
            DbError(query)

class DdN2mTreeWidget(DdN2mWidget):
    '''input widget (clickable QTreeWidget) for n2m relations with more than one additional field in the related table
    TreeWidget is initialized directly from the DB'''

    def __init__(self,  attribute):
        DdN2mWidget.__init__(self,  attribute)

    def __str__(self):
        return "<ddui.DdN2mTreeWidget %s>" % str(self.attribute.name)

    def registerChange(self,  thisItem,  thisColumn):
        if self.forEdit:
            if thisColumn == 0:
                featureIdField = self.tableLayer.fieldNameIndex(self.attribute.relationFeatureIdField)
                relatedIdField = self.tableLayer.fieldNameIndex(self.attribute.relationRelatedIdField)
                itemId = thisItem.id

                if thisItem.checkState(0) == 2:
                    feat = self.createFeature()
                    feat.setAttribute(featureIdField,  self.featureId)
                    feat.setAttribute(relatedIdField,  itemId)
                    self.tableLayer.addFeature(feat,  False)
                else:
                    self.tableLayer.selectAll()

                    for aFeature in self.tableLayer.selectedFeatures():
                        if aFeature[featureIdField] == self.featureId:
                            if aFeature[relatedIdField] == itemId:
                                idToDelete = aFeature.id()
                                self.tableLayer.deleteFeature(idToDelete)
                                break
                self.hasChanges = True

    def createInputWidget(self,  parent):
        inputWidget = QtGui.QTreeWidget(parent)
        inputWidget.setEditTriggers(QtGui.QAbstractItemView.NoEditTriggers)
        inputWidget.setHeaderHidden(True)
        inputWidget.setColumnCount(1)
        inputWidget.setObjectName("tre" + parent.objectName() + self.attribute.name)
        inputWidget.itemChanged.connect(self.registerChange)
        return inputWidget

    def initialize(self,  layer,  feature,  db):
        self.initializeLayer(layer,  feature,  db)
        query = QtSql.QSqlQuery(db)
        query.prepare(self.attribute.displayStatement)
        query.bindValue(":featureId", self.featureId)
        query.exec_()

        if query.isActive():
            self.inputWidget.clear()
            self.inputWidget.itemChanged.disconnect(self.registerChange)

            while query.next(): # returns false when all records are done
                parentId = int(query.value(0))
                parent = unicode(query.value(1))
                checked = int(query.value(2))
                parentItem = QtGui.QTreeWidgetItem(self.inputWidget)
                parentItem.id = parentId
                parentItem.setCheckState(0,  checked)
                parentItem.setText(0,  parent)

                for i in range(len(self.attribute.fieldList)):
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

class DdN2mTableWidget(DdN2mWidget):
    '''a input widget for n-to-m relations with more than one field in the relation table
    The input widget consists of a QTableWidget and an add (+) and a remove (-) button'''

    def __init__(self,  attribute):
        DdN2mWidget.__init__(self,  attribute)
        self.fkValues = {}

    def __str__(self):
        return "<ddui.DdN2mTableWidget %s>" % str(self.attribute.name)

    def createInputWidget(self,  parent):
        inputWidget = QtGui.QTableWidget(parent)
        inputWidget.setEditTriggers(QtGui.QAbstractItemView.NoEditTriggers)
        inputWidget.setColumnCount(len(self.attribute.attributes))
        fieldNames =  []

        for anAtt in self.attribute.attributes:
            fieldNames.append(anAtt.name)
        horizontalHeaders = fieldNames

        inputWidget.setHorizontalHeaderLabels(horizontalHeaders)
        inputWidget.setSelectionMode(QtGui.QAbstractItemView.SingleSelection)
        inputWidget.setSelectionBehavior(QtGui.QAbstractItemView.SelectRows)
        inputWidget.setEditTriggers(QtGui.QAbstractItemView.NoEditTriggers)
        inputWidget.setSortingEnabled(True)
        inputWidget.cellDoubleClicked.connect(self.doubleClick)
        inputWidget.itemSelectionChanged.connect(self.selectionChanged)
        inputWidget.setObjectName("tbl" + parent.objectName() + self.attribute.name)
        return inputWidget

    def initialize(self,  layer,  feature,  db):
        self.initializeLayer(layer,  feature,  db,  self.attribute.showParents)
        #self.inputWidget.clear()

        if not self.forEdit:
            self.addButton.setEnabled(False)
        else:
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

            # display the features in the QTableWidget
            self.tableLayer.removeSelection()
            self.tableLayer.invertSelection()

            for aFeat in self.tableLayer.selectedFeatures():
                self.appendRow(aFeat)

            self.tableLayer.removeSelection()

            if self.attribute.maxRows:
                self.addButton.setEnabled(self.inputWidget.rowCount()  < self.attribute.maxRows)

    def fillRow(self, thisRow, thisFeature):
        '''fill thisRow with values from thisFeature'''
        #QtGui.QMessageBox.information(None,'',str(thisRow))

        for i in range(len(self.attribute.attributes)):
            anAtt = self.attribute.attributes[i]
            aValue = thisFeature[self.tableLayer.fieldNameIndex(anAtt.name)]

            if anAtt.isFK:
                values = self.fkValues[anAtt.name]
                try:
                    aValue = values[aValue]
                except KeyError:
                    aValue = 'NULL'

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
        self.inputWidget = self.createInputWidget(frame)
        self.inputWidget.setToolTip(self.attribute.comment)
        verticalLayout = QtGui.QVBoxLayout(frame)
        verticalLayout.setObjectName("vlayout" + parent.objectName() + self.attribute.name)
        horizontalLayout = QtGui.QHBoxLayout( )
        horizontalLayout.setObjectName("hlayout" + parent.objectName() + self.attribute.name)
        horizontalLayout.addWidget(label)
        spacerItem = QtGui.QSpacerItem(40, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        horizontalLayout.addItem(spacerItem)
        self.addButton = QtGui.QPushButton(QtGui.QApplication.translate("DdInput", "Add", None,
                                                           QtGui.QApplication.UnicodeUTF8) ,  frame)
        self.removeButton = QtGui.QPushButton(QtGui.QApplication.translate("DdInput", "Remove", None,
                                                           QtGui.QApplication.UnicodeUTF8) ,  frame)
        self.addButton.clicked.connect(self.add)
        self.removeButton.clicked.connect(self.remove)
        self.removeButton.setEnabled(False)
        horizontalLayout.addWidget(self.addButton)
        horizontalLayout.addWidget(self.removeButton)
        verticalLayout.addLayout(horizontalLayout)
        verticalLayout.addWidget(self.inputWidget)
        parent.layout().addRow(frame)
        pParent = parent

        while (True):
            pParent = pParent.parentWidget()

            if isinstance(pParent,  DdDialog):
                self.parentDialog = pParent
                break





    # SLOTS
    def selectionChanged(self):
        '''slot to be called when the QTableWidget's selection has changed'''
        self.removeButton.setEnabled(len(self.inputWidget.selectedItems()) > 0)

    def doubleClick(self,  thisRow,  thisColumn):
        '''slot to be called when the user double clicks on the QTableWidget'''
        featureItem = self.inputWidget.item(thisRow,  0)
        thisFeature = featureItem.feature
        result = self.parentDialog.ddManager.showFeatureForm(self.tableLayer,  thisFeature)

        if result == 1: # user clicked OK
            # make sure user did not change parentFeatureId
            self.tableLayer.changeAttributeValue(thisFeature.id(),  self.tableLayer.fieldNameIndex(self.attribute.relationFeatureIdField),  self.featureId)
            # refresh thisFeature with the new values
            self.tableLayer.getFeatures(QgsFeatureRequest().setFilterFid(thisFeature.id()).setFlags(QgsFeatureRequest.NoGeometry)).nextFeature(thisFeature)

            self.fillRow(thisRow,  thisFeature)
            self.hasChanges = True

    def add(self):
        '''slot to be called when the user clicks on the add button'''
        thisFeature = self.createFeature()
        # set the parentFeature's id
        thisFeature[self.tableLayer.fieldNameIndex(self.attribute.relationFeatureIdField)] =  self.featureId

        if self.tableLayer.addFeature(thisFeature,  False):
            result = self.parentDialog.ddManager.showFeatureForm(self.tableLayer,  thisFeature)

            if result == 1: # user clicked OK
                self.tableLayer.getFeatures(QgsFeatureRequest().setFilterFid(thisFeature.id()).setFlags(QgsFeatureRequest.NoGeometry)).nextFeature(thisFeature)
                self.appendRow(thisFeature)
                self.hasChanges = True
            else:
                self.tableLayer.deleteFeature(thisFeature.id())

    def remove(self):
        '''slot to be called when the user clicks on the remove button'''
        thisRow = self.inputWidget.currentRow()
        featureItem = self.inputWidget.takeItem(thisRow,  0)
        thisFeature = featureItem.feature
        self.tableLayer.deleteFeature(thisFeature.id())
        self.inputWidget.removeRow(thisRow)
        self.hasChanges = True

        if self.attribute.maxRows:
            self.addButton.setEnabled(self.inputWidget.rowCount()  < self.attribute.maxRows)

class DdPushButton(DdInputWidget):
    '''abstract class, needs subclassing'''

    def __init__(self,  attribute):
        DdInputWidget.__init__(self,  attribute)

    def __str__(self):
        return "<ddui.DdPushButton %s>" % str(self.attribute.label)

    def setupUi(self,  parent,  db):
        self.label = self.getLabel()
        self.inputWidget = QtGui.QPushButton(self.label,  parent)
        self.inputWidget.setToolTip(self.attribute.comment)
        self.inputWidget.clicked.connect(self.clicked)
        parent.layout().addWidget(self.inputWidget)

    def clicked(self):
        QtGui.QMessageBox.information(None,  "",  self.label + " has been clicked")

    def initialize(self,  layer,  feature,  db):
        '''must be implemented in child class'''
        pass

    def save(self,  layer,  feature,  db):
        '''must be implemented in child class'''
        pass


