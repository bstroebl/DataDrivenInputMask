# -*- coding: utf-8 -*-
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
from dderror import DdError
from ddattribute import *
from dddialog import DdDialog

class DdManager(object):
    def __init__(self,  iface):
        self.iface = iface
        self.ddLayers = dict()

    def __debug(self,  title,  str):
        QtGui.QMessageBox.information(None,  title,  str)

    def __str__(self):
        return "<ddui.DdManager>"

    def initLayer(self,  layer):
        '''api method initLayer: initialize the layer with a data-driven input mask'''
        if 0 != layer.type():   # not a vector layer
            raise DdError(str(QtGui.QApplication.translate("DdError", "Layer is not a vector layer:", None,
                                                           QtGui.QApplication.UnicodeUTF8) + " %s"% layer.name()))
        else:
            if QtCore.QString(u'PostgreSQL') != layer.dataProvider().storageType().left(10) :
                raise DdError(str(QtGui.QApplication.translate("DdError", "Layer is not a PostgreSQL layer:", None,
                                                               QtGui.QApplication.UnicodeUTF8) + " %s"% layer.name()))
            else:
                db = self.__createDb(layer)
                layerSrc = self.__analyzeSource(layer)
                relation = layerSrc[QtCore.QString(u"table")].split('"."')
                schema = relation[0].replace('"', '')
                table = relation[1].replace('"', '')
                #QtGui.QMessageBox.information(None, "",  schema + '.' + table)
                thisTable = DdTable(schemaName = schema,  tableName = table)
                thisTable.oid = self.__getOid(thisTable,  db)

                if not self.__isTable(thisTable,  db):
                    raise DdError(str(QtGui.QApplication.translate("DdError", "Layer is not a PostgreSQL table:", None,
                                                                       QtGui.QApplication.UnicodeUTF8) + " %s"% layer.name()))

                ddui = DataDrivenUi()
                ui = ddui.createUi(thisTable,  db)
                self.ddLayers[layer.id()] = [thisTable,  db,  ui]
                self.__connectSignals(layer)
                #TODO: Action in Layer einbauen

    def showFeatureForm(self,  layer,  feature):
        '''api method showFeatureForm: show the data-driven input mask for a layer and a feature'''
        try:
            layerValues = self.ddLayers[layer.id()]
        except KeyError:
            self.initLayer(layer)
            layerValues = self.ddLayers[layer.id()]

        #QtGui.QMessageBox.information(None, "", str(layerValues[2]))
        db = layerValues[1]
        ui = layerValues[2]
        dlg = DdDialog(self.iface,  ui,  layer,  feature,  db)
        dlg.show()
        result = dlg.exec_()

        if result == 1:
            layer.setModified()

    def setUi(self,  layer,  ui):
        '''api method to exchange the default ui with a custom ui'''
        try:
            layerValues = self.ddLayers[layer.id()]
        except KeyError:
            self.initLayer(layer)
            layerValues = self.ddLayers[layer.id()]

        #QtGui.QMessageBox.information(None, "", str(layerValues[2]))
        thisTable = layerValues[0]
        db = layerValues[1]
        self.ddLayers[layer.id()] = [thisTable,  db,  ui]

    def setDb(self,  layer,  db):
        '''api method to set the db for a layer'''
        try:
            layerValues = self.ddLayers[layer.id()]
        except KeyError:
            self.initLayer(layer)
            layerValues = self.ddLayers[layer.id()]

        thisTable = layerValues[0]
        ui = layerValues[2]
        self.ddLayers[layer.id()] = [thisTable,  db,  ui]

    #Slots
    def editingStarted(self):
        layer = self.iface.activeLayer()
        db = self.ddLayers[layer.id()][1]

        if not db:
            db = self.__ceateDb(layer)
            self.setDb(layer,  db)

        if not db.transaction():
            raise DdError(str(QtGui.QApplication.translate("DdError", "Error starting transaction on DB ", None,
                                                           QtGui.QApplication.UnicodeUTF8) + "%s %s" % db.hostName(),  db.databaseName()))

    def editingStopped(self):
        layer = self.iface.activeLayer()
        db = self.ddLayers[layer.id()][1]

        if layer.isModified():
            if not db.rollback():
                raise DdError(str(QtGui.QApplication.translate("DdError", "Error rolling back transaction on DB ", None,
                                                           QtGui.QApplication.UnicodeUTF8) + "%s %s" % db.hostName(),  db.databaseName()))
        else:
            if not db.commit():
                raise DdError(str(QtGui.QApplication.translate("DdError", "Error committing transaction on DB ", None,
                                                           QtGui.QApplication.UnicodeUTF8) + "%s %s" % db.hostName(),  db.databaseName()))

        # better keep the connection, if too many connections exist we must change this
        #self.__disconnectDb(db)
        #self.setDb(layer,  None)

    def __getOid(self,  thisTable,  db):
        ''' query the DB to get a table's oid'''
        query = QtSql.QSqlQuery(db)
        sQuery = "SELECT c.oid FROM pg_class c \
        JOIN pg_namespace n ON c.relnamespace = n.oid \
        WHERE n.nspname = :schema AND c.relname = :table"
        query.prepare(sQuery)
        query.bindValue(":schema", QtCore.QVariant(thisTable.schemaName))
        query.bindValue(":table", QtCore.QVariant(thisTable.tableName))
        query.exec_()

        oid = None

        if query.isActive():
            if query.size() == 0:
                query.finish()
            else:
                while query.next():
                    oid = query.value(0).toInt()[0]
                    break
                query.finish()
        else:
            self.__raiseDbError(query)

        return oid

    def __isTable(self,  thisTable,  db):
        '''checks if the given relation is a table'''

        query = QtSql.QSqlQuery(db)
        sQuery = "SELECT * FROM pg_tables WHERE schemaname = :schema AND tablename = :table"
        query.prepare(sQuery)
        query.bindValue(":schema", QtCore.QVariant(thisTable.schemaName))
        query.bindValue(":table", QtCore.QVariant(thisTable.tableName))
        query.exec_()

        if query.isActive():
            if query.size() == 0:
                query.finish()
                return False
            else:
                query.finish()
                return True
        else:
            self.__raiseDbError(query)
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

    def __connectDb(self,  host,  database,  port,  username,  passwd):
        '''connect to the PostgreSQL DB'''
        db = QtSql.QSqlDatabase.addDatabase ("QPSQL")
        db.setHostName(host)
        db.setPort(port)
        db.setDatabaseName(database)
        db.setUserName(username)
        db.setPassword(passwd)
        ok = db.open()

        if not ok:
            raise DdError(str(QtGui.QApplication.translate("DdError", "Could not connect to PostgreSQL database:", None, QtGui.QApplication.UnicodeUTF8) + " %s"% database))
            return None
        else:
            return db

    def __createDb(self,  layer):
        '''create a QtSql.QSqlDatabase object  for the DB-connection this layer comes from'''
        layerSrc = self.__analyzeSource(layer)
        db = self.__connectDb(layerSrc[QtCore.QString(u"host")],  layerSrc[QtCore.QString(u"dbname")],
            layerSrc[QtCore.QString(u"port")].toInt()[0],  layerSrc[QtCore.QString(u"user")],
            layerSrc[QtCore.QString(u"password")])
        return db

    def __disconnectDb(self,  db):
        '''disconnect from the DB'''
        if db:
            db.close()
            db = None

class DataDrivenUi(object):
    '''when subclassing this class, you want to rewrite createUi and use DdManager's setUi
    method to apply your custom ui to the layer'''

    def __init__(self):
        pass

    def __str__(self):
        return "<ddui.DataDrivenUi>"

    def createUi(self,  thisTable,  db,  skip = [],  labels = {"polygon_has_eigenschaft": "testlabel"}):
        '''creates a default ui for this table (DdTable instance)'''

        ddTables = []

        while True: # use a loop to query all parent tables
            if thisTable.oid:
                ddTables.append(thisTable)
                thisTable = self.getParent(thisTable,  db)
            else:
                break

        ui = DdDialogWidget()

        # now loop through all tables
        while len(ddTables) > 0:
            thisTable = ddTables.pop()
            ddAttributes = self.getAttributes(thisTable, db,  labels)

            for anAtt in ddAttributes:
                if anAtt.isPK:
                    n2mAttributes = self.getN2mAttributes(db,  thisTable,  anAtt.name,  anAtt.num,  labels)
                    ddAttributes = ddAttributes + n2mAttributes

            #check if we need a QToolBox
            needsToolBox = (len(ddAttributes) > 5)

            oneLineAttributes = []
            largeAttributes = []

            # loop through the attributes and get one-line types (QLineEdit, QComboBox) first
            for anAttribute in ddAttributes:
                nextAtt = False
                 #check if this attribute is supposed to be skipped
                for skipName in skip:
                    if skipName == anAttribute.name:
                        nextAtt = True
                        break

                if nextAtt:
                    continue # skip it

                if anAttribute.type == "text" or anAttribute.type == "n2m":
                    needsToolBox = True
                    largeAttributes.append(anAttribute)
                else:
                    oneLineAttributes.append(anAttribute)

            #QtGui.QMessageBox.information(None, "needsToolBox",  str(needsToolBox))
            ddFormWidget = DdFormWidget(thisTable.tableName,  needsToolBox)

            for anAttribute in oneLineAttributes:

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

            for anAttribute in largeAttributes:
                if anAttribute.type == "text":
                    ddInputWidget = DdTextEdit(anAttribute)
                elif anAttribute.type == "n2m":

                    if anAttribute.subType == "list":
                        ddInputWidget = DdN2mListWidget(anAttribute)
                    elif anAttribute.subType == "tree":
                        #ddInputWidget = DdN2mTreeWidget(anAttribute)
                        pass
                    elif anAttribute.subType == "table":
                        #ddInputWidget = DdN2mTableWidget(anAttribute)
                        pass

                ddFormWidget.addInputWidget(ddInputWidget)

            ui.addFormWidget(ddFormWidget)

        return ui

    def getParent(self,  thisTable,  db):
        ''' query the DB to get a table's parent if any'''

        query = QtSql.QSqlQuery(db)
        sQuery = "SELECT c.oid, n.nspname, c.relname \
        FROM pg_inherits i \
        JOIN pg_class c ON i.inhparent = c.oid \
        JOIN pg_namespace n ON c.relnamespace = n.oid \
        WHERE i.inhrelid = :oid"
        query.prepare(sQuery)
        query.bindValue(":oid", QtCore.QVariant(thisTable.oid))
        query.exec_()

        parentTable = DdTable()

        if query.isActive():
            if query.size() == 0:
                query.finish()
            else:
                while query.next():
                    oid = query.value(0).toInt()[0]
                    schema = query.value(1).toString()
                    table = query.value(2).toString()
                    parentTable.oid = oid
                    parentTable.schemaName = schema
                    parentTable.tableName = table
                    break
                query.finish()
        else:
            self.raiseDbError(query)

        return parentTable

    def getN2mAttributes(self,  db,  thisTable,  attName,  attNum,  labels):
        # find those tables where our pk is a fk
        n2mAttributes = []
        pkQuery = QtSql.QSqlQuery(db)
        sPkQuery = "SELECT array_length(pk.conkey, 1), att.attname, att.attnum, c.oid as table_oid,n.nspname,c.relname, f.numfields, COALESCE(d.description,'') as comment \
            FROM pg_attribute att \
                JOIN (SELECT * FROM pg_constraint WHERE contype = 'f') fk ON att.attrelid = fk.conrelid AND att.attnum = ANY (fk.conkey) \
                JOIN (SELECT * FROM pg_constraint WHERE contype = 'p') pk ON pk.conrelid = fk.conrelid \
                JOIN pg_class c ON fk.conrelid = c.oid \
                JOIN pg_namespace n ON c.relnamespace = n.oid \
                LEFT JOIN pg_description d ON c.oid = d.objoid \
                JOIN(SELECT attrelid, count(attrelid) as numfields \
                     FROM pg_attribute \
                     WHERE attnum > 0 \
                        AND attisdropped = false \
                     GROUP BY attrelid) f ON c.oid = f.attrelid \
            WHERE fk.confrelid = :oid \
                AND :attNum = ANY(fk.confkey)"
        pkQuery.prepare(sPkQuery)
        pkQuery.bindValue(":oid", QtCore.QVariant(thisTable.oid))
        pkQuery.bindValue(":attNum", QtCore.QVariant(attNum))
        pkQuery.exec_()

        if pkQuery.isActive():
            while pkQuery.next():
                numPkFields = pkQuery.value(0).toInt()[0]
                relationFeatureIdField = pkQuery.value(1).toString()
                fkAttNum = pkQuery.value(2).toString()
                relationOid = pkQuery.value(3).toString()
                relationSchema = pkQuery.value(4).toString()
                relationTable = pkQuery.value(5).toString()
                numFields = pkQuery.value(6).toInt()[0]
                relationComment = pkQuery.value(7).toString()

                if numPkFields == 1:
                    subType = "table"
                elif numPkFields > 1:
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
                        # we do not want the table where we came from in the results, therefore :attNum != ANY(conkey)
                        relatedQuery.prepare(sRelatedQuery)
                        relatedQuery.bindValue(":relationOid", QtCore.QVariant(relationOid))
                        relatedQuery.bindValue(":attNum1", QtCore.QVariant(attNum))
                        relatedQuery.bindValue(":attNum2", QtCore.QVariant(attNum))
                        relatedQuery.exec_()

                        if relatedQuery.isActive():
                            if relatedQuery.size() != 1:
                                relatedQuery.finish()
                                continue

                            while relatedQuery.next():
                                relatedOid = relatedQuery.value(0).toInt()[0]
                                relatedSchema = relatedQuery.value(1).toString()
                                relatedTable = relatedQuery.value(2).toString()
                                relationRelatedIdField = relatedQuery.value(3).toString()
                            relatedQuery.finish()

                            relatedFieldsQuery = QtSql.QSqlQuery(db)
                            relatedFieldsQuery.prepare(self.__attributeQuery("att.attnum"))
                            relatedFieldsQuery.bindValue(":oid", QtCore.QVariant(relatedOid))
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

                                while relatedFieldsQuery.next():
                                    relatedAttName = relatedFieldsQuery.value(0).toString()
                                    relatedAttNum = relatedFieldsQuery.value(1).toInt()[0]
                                    relatedAttNotNull = relatedFieldsQuery.value(2).toBool()
                                    relatedAttHasDefault = relatedFieldsQuery.value(3).toBool()
                                    relatedAttIsChild = relatedFieldsQuery.value(4).toBool()
                                    relatedAttLength = relatedFieldsQuery.value(5).toInt()[0]
                                    relatedAttTyp = relatedFieldsQuery.value(6).toString()
                                    relatedAttComment = relatedFieldsQuery.value(7).toString()
                                    relatedAttDefault = relatedFieldsQuery.value(8).toString()
                                    relatedAttConstraint = relatedFieldsQuery.value(9).toString()

                                    if relatedAttConstraint == QtCore.QString("p"): # PK of the related table
                                        relatedIdField = relatedAttName

                                    if relatedAttTyp == QtCore.QString("varchar") or relatedAttTyp == QtCore.QString("char"):

                                        if not relatedDisplayCandidate:
                                            relatedDisplayCandidate = relatedAttName # we use the first string field

                                        if relatedAttNotNull and not relatedDisplayField: # we use the first one
                                            relatedDisplayField = relatedAttName

                                relatedFieldsQuery.finish()

                                if not relatedDisplayCandidate: # there wa sno string field
                                    relatedDisplayCandidate = relatedIdField

                                if not relatedDisplayField: # there was no notNull string field
                                    relatedDisplayField = relatedDisplayCandidate

                                if subType == "list":

                                    try:
                                        attLabel = labels[str(relationTable)]
                                    except KeyError:
                                        attLabel = None
                                        QtGui.QMessageBox.information(None, "KeyError", relationTable)

                                    ddAtt = DdN2mAttribute(DdTable(relationOid,  relationSchema,  relationTable),  \
                                                           DdTable(relatedOid,  relatedSchema,  relatedTable),  subType,  relationComment,  attLabel,  \
                                                           relationFeatureIdField, relationRelatedIdField,  relatedIdField,  relatedDisplayField)

                                n2mAttributes.append(ddAtt)
                            else:
                                self.raiseDbError(relatedFieldsQuery)
                        else:
                            self.raiseDbError(relatedQuery)

                    elif numFields > 2:
                        subType = "table"
            pkQuery.finish()
        else:
            self.raiseDbError(pkQuery)

        return n2mAttributes


    def getAttributes(self,  thisTable, db,  labels):
        ''' query the DB and create DdAttributes'''
        ddAttributes = []

        query = QtSql.QSqlQuery(db)
        sQuery = self.__attributeQuery()

        query.prepare(sQuery)
        query.bindValue(":oid", QtCore.QVariant(thisTable.oid))
        query.exec_()

        retValue = dict()

        if query.isActive():
            if query.size() == 0:
                query.finish()
            else:
                foreignKeys = self.getForeignKeys(thisTable,  db)

                while query.next():
                    attName = query.value(0).toString()
                    attNum = query.value(1).toInt()[0]
                    attNotNull = query.value(2).toBool()
                    attHasDefault = query.value(3).toBool()
                    attIsChild = query.value(4).toBool()
                    attLength = query.value(5).toInt()[0]
                    attTyp = query.value(6).toString()
                    attComment = query.value(7).toString()
                    attDefault = query.value(8).toString()

                    if not self.isSupportedType(attTyp):
                        continue

                    if attHasDefault:
                        attDefault = attDefault.split("::")[0]

                    attConstraint = query.value(9).toString()
                    constrainedAttNums = query.value(10).toList()
                    isPK = QtCore.QString("p") # PrimaryKey

                    if attIsChild:
                        continue

                    try: # is this attribute a FK
                        fk = foreignKeys[attNum]

                        try:
                            attLabel = labels[str(attName)]
                        except KeyError:
                            attLabel = fk[2]

                        ddAtt = DdFkLayerAttribute(thisTable,  attTyp,  attNotNull,  attName,  attComment,  attNum,  isPK, attDefault,  attHasDefault,  fk[1],  attLabel)
                    except KeyError:
                        # no fk defined

                        try:
                            attLabel = labels[str(attName)]
                        except KeyError:
                            attLabel = None

                        ddAtt = DdLayerAttribute(thisTable,  attTyp,  attNotNull,  attName,  attComment,  attNum,  isPK, False,  attDefault,  attHasDefault,  attLength,  attLabel)

                    ddAttributes.append(ddAtt)

                query.finish()
        else:
            self.raiseDbError(query)

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
        attnum: [QString: Type of the lookup field, QString: sql to query lookup values, QString: Name of the value field in the lookup table]'''
        query = QtSql.QSqlQuery(db)
        sQuery = "SELECT \
        att.attnum, \
        t.typname as typ, \
        CAST(valatt.attnotnull as integer) as notnull, \
        valatt.attname, \
        ((((((('SELECT ' || quote_ident(valatt.attname)) || ' as value, ')  || quote_ident(refatt.attname)) || ' as key FROM ') || quote_ident(ns.nspname)) || '.') || quote_ident(c.relname)) || ';' AS sql_key, \
        ((((((('SELECT ' || quote_ident(refatt.attname)) || ' as value, ')  || quote_ident(refatt.attname)) || ' as key FROM ') || quote_ident(ns.nspname)) || '.') || quote_ident(c.relname)) || ';' AS default_sql \
        FROM pg_attribute att \
        JOIN (SELECT * FROM pg_constraint WHERE contype = 'f') con ON att.attrelid = con.conrelid AND att.attnum = ANY (con.conkey) \
        JOIN pg_class c ON con.confrelid = c.oid \
        JOIN pg_namespace ns ON c.relnamespace = ns.oid \
        JOIN pg_attribute refatt ON con.confrelid = refatt.attrelid AND con.confkey[1] = refatt.attnum \
        JOIN pg_attribute valatt ON con.confrelid = valatt.attrelid \
        JOIN pg_type t ON valatt.atttypid = t.oid \
        WHERE att.attnum > 0 \
        AND att.attisdropped = false \
        AND valatt.attnum > 0 \
        AND valatt.attisdropped = false \
        AND valatt.attnum != con.confkey[1] \
        AND att.attrelid = :oid \
        ORDER BY att.attnum, valatt.attnum"
        query.prepare(sQuery)
        query.bindValue(":oid", QtCore.QVariant(thisTable.oid))
        query.exec_()

        foreignKeys = dict()

        if query.isActive():
            while query.next():
                attNum = query.value(0).toInt()[0]
                fieldType = query.value(1).toString()
                notNull = query.value(2).toBool()
                valAttName = query.value(3).toString()
                keySql = query.value(4).toString()
                defaultSql = query.value(5).toString()
                #QtGui.QMessageBox.information(None, "",  str(attNum) + ": " + fieldType + " " + valAttName + " " + keySql)
                try:
                    fk = foreignKeys[attNum]
                    if fk[0] != QtCore.QString("varchar"): # we do not already have a varchar field as value field
                    # find a field with a suitable type
                        if notNull and (fieldType == QtCore.QString("varchar") or fieldType == QtCore.QString("char")):
                            foreignKeys[attNum] = [fieldType,  keySql,  valAttName]
                except KeyError:
                    if notNull and (fieldType == QtCore.QString("varchar") or fieldType == QtCore.QString("char")):
                        foreignKeys[attNum] = [fieldType,  keySql,  valAttName]
                    else: # put the first in
                        foreignKeys[attNum] = [fieldType,  defaultSql,  valAttName]

            query.finish()
        else:
            self.raiseDbError(query)

        return foreignKeys

    def __attributeQuery(self,  order = "att.attname"):
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

    def raiseDbError(self,  query):
        raise DdError(unicode(QtGui.QApplication.translate("DBError", "Database Error:", None,
                                                               QtGui.QApplication.UnicodeUTF8) + \
                                                               QtCore.QString("%1 \n %2").arg(query.lastError().text()).arg(query.lastQuery())))


class DdWidget(object):
    '''abstract class'''

    def __init__(self):
        pass

    def __str__(self):
        return "<ddui.DdWidget>"

    def checkInput(self):
       return True

    def setupUi(self,  parent,  db):
        raise NotImplementedError("Should have implemented setupUi")

    def initialize(self,  layer,  feature,  db):
        raise NotImplementedError("Should have implemented initialize")

    def save(self,  layer,  feature,  db):
        raise NotImplementedError("Should have implemented save")

    def raiseDbError(self,  query):
        raise DdError(unicode(QtGui.QApplication.translate("DBError", "Database Error:", None,
                                                               QtGui.QApplication.UnicodeUTF8) + \
                                                               QtCore.QString("%1 \n %2").arg(query.lastError().text()).arg(query.lastQuery())))

class DdDialogWidget(DdWidget):
    def __init__(self):
        DdWidget.__init__(self)
        self.forms = []

    def __str__(self):
        return "<ddui.DdDialogWidget>"

    def setupUi(self,  DataDrivenInputMask,  db): # DataDrivenInputMask is a QDialog
        self.layout = QtGui.QVBoxLayout(DataDrivenInputMask)
        self.layout.setObjectName("layout")
        self.mainTab = QtGui.QTabWidget(DataDrivenInputMask)
        self.mainTab.setObjectName("mainTab")
        DataDrivenInputMask.setObjectName("DataDrivenInputMask")
        DataDrivenInputMask.setWindowModality(QtCore.Qt.ApplicationModal)
        #DataDrivenInputMask.resize(400, 487)

        for i in range(len(self.forms)):
            aTab = QtGui.QWidget()
            aTab.setObjectName("tab" + str(i))
            aForm = self.forms[i]

            if aForm.hasToolBox:
                tabLayout = QtGui.QVBoxLayout(aTab)
            else:
                tabLayout = QtGui.QFormLayout(aTab)

            tabLayout.setObjectName("tabLayout" + str(i))
            aForm.setupUi(aTab,  db)
            self.mainTab.addTab(aTab,  aForm.tabName)

        self.layout.addWidget(self.mainTab)
        self.buttonBox = QtGui.QDialogButtonBox(DataDrivenInputMask)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtGui.QDialogButtonBox.Cancel|QtGui.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName("buttonBox")
        self.layout.addWidget(self.buttonBox)

        self.mainTab.setCurrentIndex(0)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL("accepted()"), DataDrivenInputMask.accept)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL("rejected()"), DataDrivenInputMask.reject)
        QtCore.QMetaObject.connectSlotsByName(DataDrivenInputMask)

    def addFormWidget(self,  ddFormWidget):
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
        for aForm in self.forms:
            aForm.save(layer,  feature,  db)

class DdFormWidget(DdWidget):
    '''class arranges its input widgets either in a QToolBox or int the DdDialogWidget's current tab'''
    def __init__(self,  tabName, hasToolBox = False):
        DdWidget.__init__(self)
        self.tabName = tabName
        self.hasToolBox = hasToolBox
        self.inputWidgets = []

    def __str__(self):
        return "<ddui.DdFormWidget>"

    def setupUi(self,  parent,  db):
        #QtGui.QMessageBox.information(None, "DdFormWidget setupUi", parent.objectName())
        if self.hasToolBox:
            self.toolBox = QtGui.QToolBox(parent)
            self.toolBox.setObjectName(parent.objectName() + "_toolBox")
            hasPendingPage = False

            for i in range(len(self.inputWidgets)):
                ddInputWidget = self.inputWidgets[i]
                #QtGui.QMessageBox.information(None, "",  str(ddInputWidget))
                typ = ddInputWidget.attribute.type

                if typ == "n2m" or typ == "text":
                    if hasPendingPage:
                        # add a page if threre is one pending
                        self.__addToolBoxPage(toolBoxPage,  firstAttName,  lastAttName)
                        hasPendingPage = False

                    toolBoxPage = QtGui.QWidget() # create a new toolBoxPage
                    #toolBoxPage.setGeometry(QtCore.QRect(0, 0, 360, 326))
                    toolBoxPage.setObjectName(self.toolBox.objectName() + "_page" + str(i))
                    gridLayout= QtGui.QGridLayout(toolBoxPage)
                    gridLayout.setObjectName(self.toolBox.objectName() + "_gridLayout")
                    ddInputWidget.setupUi(toolBoxPage,  db)
                    self.toolBox.addItem(toolBoxPage,  ddInputWidget.getLabel())
                else:
                    #QtGui.QMessageBox.information(None, str(i), ddInputWidget.attribute.name)
                    if i % 5 == 0 and i  != 0:
                        #QtGui.QMessageBox.information(None, "add toolBoxPage", ddInputWidget.attribute.name)
                        self.__addToolBoxPage(toolBoxPage,  firstAttName,  lastAttName) # add the current page to the toolBox
                        hasPendingPage = False
                    if i % 5 == 0:
                        toolBoxPage = QtGui.QWidget() # create a new toolBoxPage
                        #toolBoxPage.setGeometry(QtCore.QRect(0, 0, 360, 326))
                        toolBoxPage.setObjectName(self.toolBox.objectName() + "_page" + str(i))
                        formLayout = QtGui.QFormLayout(toolBoxPage)
                        formLayout.setObjectName(self.toolBox.objectName() + "_formLayout")
                        hasPendingPage = True
                        #firstAttName = ddInputWidget.attribute.name
                        firstAttName = ddInputWidget.getLabel()

                    lastAttName = ddInputWidget.getLabel()
                    ddInputWidget.setupUi(toolBoxPage,  db)

            if hasPendingPage:
                self.__addToolBoxPage(toolBoxPage,  firstAttName,  lastAttName)

            parent.layout().addWidget(self.toolBox)
            self.toolBox.setCurrentIndex(0)
        else:
            for i in range(len(self.inputWidgets)):
                ddInputWidget = self.inputWidgets[i]
                ddInputWidget.setupUi(parent,  db)

    def __addToolBoxPage(self,  toolBoxPage,  firstAttName,  lastAttName):
        if firstAttName == lastAttName:
            newName = firstAttName
        else:
            newName = firstAttName + " ... " + lastAttName
        self.toolBox.addItem(toolBoxPage,  newName)

    def addInputWidget(self,  ddInputWidget):
        #QtGui.QMessageBox.information(None,  "addInputWidget",  ddInputWidget.attribute.name)
        self.inputWidgets.append(ddInputWidget)

    def initialize(self,  layer,  feature,  db):
        for anInputWidget in self.inputWidgets:
            anInputWidget.initialize(layer,  feature,  db)

    def checkInput(self):
        inputOk = True
        for anInputWidget in self.inputWidgets:
            if not anInputWidget.checkInput():
                inputOk = False
                break

        return inputOk

    def save(self,  layer,  feature,  db):
        for anInputWidget in self.inputWidgets:
            anInputWidget.save(layer,  feature,  db)

class DdInputWidget(DdWidget):
    '''abstract super class for all input widgets'''
    def __init__(self,  attribute):
        DdWidget.__init__(self)
        self.attribute = attribute

    def __str__(self):
        return "<ddui.DdInputWidget %s>" % str(self.attribute.name)

    def getLabel(self):
        labelString = self.attribute.getLabel()

        return labelString

    def getMaxValueFromTable(self,  schemaName,  tableName,  db):
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
                return query.value(0).toString().toInt()[0]
            else:
                return 0

            query.finish()

        else:
            self.raiseDbError(query)

class DdLineEdit(DdInputWidget):
    '''abstract class for all Input Widgets that can be represented in one line,
    creates a QLineEdit as default InputWidget, adds a label and the inputWidget
    to a QFormLayout. Methods implemented
    in this class can be overridden by implementations in child classes'''

    def __init__(self,  attribute):
        DdInputWidget.__init__(self,  attribute)

    def __str__(self):
        return "<ddui.DdOneLineInputWidget %s>" % str(self.attribute.name)

    def getFeatureValue(self,  layer,  feature,  db):
        '''returns a QString representing the value in this field for this feature;
        if it is a new feature the default value is returned
        default implementation for a QLineEdit'''

        if feature.id() >= 0:
            fieldIndex = self.getFieldIndex(layer)
            thisValue = feature.attributeMap().get(fieldIndex,  "").toString()
        else: # new feature
            if self.attribute.hasDefault:
                thisValue = self.attribute.default.toString()
            else:
                thisValue = QtCore.QString()

        return thisValue

    def createLabel(self,  parent):
        labelString = self.getLabel()

        if self.attribute.notNull:
            labelString = labelString + "*" # mark attribute as must

        label = QtGui.QLabel(labelString,  parent)
        label.setObjectName("lbl" + parent.objectName() + self.attribute.name)
        return label

    def createInputWidget(self,  parent):
        inputWidget = QtGui.QLineEdit(parent) # defaultInputWidget
        inputWidget.setObjectName("txl" + parent.objectName() + self.attribute.name)
        return inputWidget

    # public methods
    def setValue(self,  thisValue):
        self.inputWidget.setText(thisValue)

    def getValue(self):
        thisValue = self.inputWidget.text()

        if thisValue.isEmpty():
            thisValue = None

        return thisValue

    def setupUi(self,  parent,  db):
        '''setup the label and add the inputWidget to parents formLayout'''
        #QtGui.QMessageBox.information(None,  "DdLineEdit",  "setupUi " + self.attribute.name)
        self.label = self.createLabel(parent)
        self.inputWidget = self.createInputWidget(parent)
        self.inputWidget.setToolTip(self.attribute.comment)
        parent.layout().addRow(self.label,  self.inputWidget)

    def initialize(self,  layer,  feature,  db):
        thisValue = self.getFeatureValue(layer,  feature,  db)
        self.setValue(thisValue)

    def checkInput(self):
        thisValue = self.getValue()

        if self.attribute.notNull and thisValue.isEmpty():
            QtGui.QMessageBox.warning(None, "",  str(QtGui.QApplication.translate("DdWarning", "Field must not be empty: ", None,
                                                           QtGui.QApplication.UnicodeUTF8) + " %s"% str(self.label.text())))
            return False
        else:
            return True

    def getFieldIndex(self,  layer):
        if layer:
            fieldIndex = layer.fieldNameIndex(self.attribute.name)
        else:
            fieldIndex = self.attribute.num

        if fieldIndex == -1:
            raise DdError(str(QtGui.QApplication.translate("DdError", "Field not found in layer:", None,
                                                           QtGui.QApplication.UnicodeUTF8)) + " %s"% str(self.attribute.name))

        return fieldIndex

    def save(self,  layer,  feature,  db):
        thisValue = self.getValue()
        fieldIndex = self.getFieldIndex(layer)
        layer.changeAttributeValue(feature.id(),  fieldIndex,  QtCore.QVariant(thisValue),  False)

class DdLineEditInt(DdLineEdit):
    '''QLineEdit for an IntegerValue'''

    def __init__(self,  attribute):
        DdLineEdit.__init__(self,  attribute)

    def __str__(self):
        return "<ddui.DdLineEditInt %s>" % str(self.attribute.name)

    def getFeatureValue(self,  layer,  feature,  db):
        if feature.id() >= 0:
            fieldIndex = self.getFieldIndex(layer)
            thisValue = feature.attributeMap().get(fieldIndex,  "").toString()
        else: # new feature
            if self.attribute.hasDefault:
                thisValue = self.attribute.default.toString()
            else:
                if self.attribute.isPK :
                        thisValue = QtCore.QString(self.getMaxValueFromTable(self.attribute.schemaName,  self.attribute.tableName,  db) + 1)
                else:
                    thisValue = QtCore.QString()

        return thisValue

    def setValidator(self):
        if self.attribute.type == QtCore.QString("int2"):
            min = -32768
            max = 32767
        elif self.attribute.type == QtCore.QString("int4"):
            min = -2147483648
            max = 2147483647
        elif self.attribute.type == QtCore.QString("int8"):
            min = -9223372036854775808
            max = 9223372036854775807

        validator = QtGui.QIntValidator(min,  max,  self.inputWidget)
        self.inputWidget.setValidator(validator)

    def setupUi(self,  parent,  db):
        DdLineEdit.setupUi(self,  parent,  db)
        self.setValidator()

    def initialize(self,  layer,  feature,  db):
        thisValue = self.getFeatureValue(layer,  feature,  db)
        isInt = thisValue.toInt()[1]

        if not  isInt: # could be a serial, i.e. a nextval(sequence) expression
            self.inputWidget.setValidator(None) # remove the validator

        self.setValue(thisValue)

        if not  isInt:
            self.setValidator()

    def save(self,  layer,  feature,  db):
        thisValue = self.getValue()

        if self.attribute.hasDefault:
            isInt = thisValue.toInt()[1]

            if not isInt and thisValue == self.attribute.default:
                thisValue = QtCore.QString()

        fieldIndex = self.getFieldIndex(layer)
        layer.changeAttributeValue(feature.id(),  fieldIndex,  QtCore.QVariant(thisValue),  False)

class DdLineEditDouble(DdLineEdit):
    '''QLineEdit for an IntegerValue'''

    def __init__(self,  attribute):
        DdLineEdit.__init__(self,  attribute)
        #QtGui.QMessageBox.information(None,  "DdLineEditDouble",  "init " + self.attribute.name)

    def __str__(self):
        return "<ddui.DdLineEditDouble %s>" % str(self.attribute.name)

    def setValidator(self):
        validator = QtGui.QDoubleValidator(self.inputWidget)
        self.inputWidget.setValidator(validator)

    def __textChanged(self,  newText):
        if not newText.toDouble()[1]:
            newValue = newText.replace(QtCore.QString(","),  QtCore.QString("."))
            self.setValue(newValue)

    def setupUi(self,  parent,  db):
        #QtGui.QMessageBox.information(None,  "DdLineEditFloat",  "setupUi " + self.attribute.name)
        DdLineEdit.setupUi(self,  parent,  db)
        self.setValidator()
        self.inputWidget.textChanged.connect(self.__textChanged)

class DdLineEditChar(DdLineEdit):
    '''QLineEdit for a char or varchar'''

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
                QtGui.QMessageBox.warning(None, "",  str(QtGui.QApplication.translate("DdWarning", "Input in Field is too long: ", None,
                                                           QtGui.QApplication.UnicodeUTF8) + " %s"% str(self.label.text())))
                return False

            if self.attribute.type == "char" and size != self.attribute.length:
                QtGui.QMessageBox.warning(None, "",  str(QtGui.QApplication.translate("DdWarning", "Input in Field is too short: ", None,
                                                           QtGui.QApplication.UnicodeUTF8) + " %s"% str(self.label.text())))
                return False

        return ok

class DdComboBox(DdLineEdit):
    '''QComboBox for a foreign key'''

    def __init__(self,  attribute):
        DdLineEdit.__init__(self,  attribute)

    def __str__(self):
        return "<ddui.DdComboBox %s>" % str(self.attribute.name)

    def getFeatureValue(self,  layer,  feature,  db):
        '''returns a value representing the value in this field for this feature'''

        if feature.id() >= 0:
            fieldIndex = self.getFieldIndex(layer)

            if self.attribute.isTypeInt():
                thisValue = feature.attributeMap().get(fieldIndex,  -9999).toInt()[0]
            elif self.attribute.isTypeChar():
                thisValue = feature.attributeMap().get(fieldIndex,  "-9999").toString()

        else: # new feature
            if self.attribute.hasDefault:
                if self.attribute.isTypeInt():
                    thisValue = QtCore.QVariant(self.attribute.default).toInt()[0]
                elif self.attribute.isTypeChar():
                    thisValue = QtCore.QVariant(self.attribute.default).toString()
            else:
                if self.attribute.isTypeInt():
                    thisValue = -9999
                elif self.attribute.isTypeChar():
                    thisValue = QtCore.QString("-9999")

        return thisValue

    def createInputWidget(self,  parent):
        inputWidget = QtGui.QComboBox(parent) # defaultInputWidget
        inputWidget.setObjectName("cbx" + parent.objectName() + self.attribute.name)
        return inputWidget

    def fill(self,  db):
        query = QtSql.QSqlQuery(db)
        query.prepare(self.attribute.queryForCbx)
        query.exec_()

        if query.isActive():
            self.inputWidget.clear()

            if not self.attribute.notNull:
                #nullString = QtGui.QApplication.translate("DdInput", "Please choose", None, QtGui.QApplication.UnicodeUTF8)
                nullString = QtCore.QString()

                if self.attribute.isTypeChar():
                    self.inputWidget.addItem(nullString, "-9999")
                elif self.attribute.isTypeInt():
                    self.inputWidget.addItem(nullString, -9999)

            while query.next(): # returns false when all records are done
                sValue = QtCore.QString(query.value(0).toString())
                keyValue = query.value(1)

                if self.attribute.isTypeChar():
                    keyValue = keyValue.toString()
                elif self.attribute.isTypeInt():
                    keyValue = keyValue.toInt()[0]

                self.inputWidget.addItem(sValue, keyValue)

            query.finish()
        else:
            self.raiseDbError(query)

    def setValue(self,  thisValue):
        if not thisValue:
            self.inputWidget.setCurrentIndex(0)
        else:
            for i in range(self.inputWidget.count()):
                if self.inputWidget.itemData(i) == thisValue:
                    self.inputWidget.setCurrentIndex(i)
                    break

    def getValue(self):
        thisValue = self.inputWidget.itemData(self.inputWidget.currentIndex())

        if QtCore.QString("-9999") == thisValue.toString(): # Null selected
            thisValue = None

        return thisValue

    def setupUi(self,  parent,  db):
        '''setup the label and add the inputWidget to parents formLayout'''
        #QtGui.QMessageBox.information(None,  "DdLineEdit",  "setupUi " + self.attribute.name)
        self.label = self.createLabel(parent)
        self.inputWidget = self.createInputWidget(parent)
        self.fill(db)
        parent.layout().addRow(self.label,  self.inputWidget)

class DdDateEdit(DdLineEdit):
    '''QDateEdit for a date field'''

    def __init__(self,  attribute):
        DdLineEdit.__init__(self,  attribute)

    def __str__(self):
        return "<ddui.DdDateEdit %s>" % str(self.attribute.name)

    def getFeatureValue(self,  layer,  feature,  db):
        '''returns a QDate representing the value in this field for this feature'''

        if feature.id() >= 0:
            fieldIndex = self.getFieldIndex(layer)
            thisValue = feature.attributeMap().get(fieldIndex,  "").toString()

            if thisValue.isEmpty():
                thisValue = None
            else:
                thisValue = feature.attributeMap().get(fieldIndex,  "").toDate()
        else: # new feature
            if self.attribute.hasDefault:
                thisValue = QtCore.QVariant(self.attribute.default).toDate()
            else:
                thisValue = None

        return thisValue

    def createInputWidget(self,  parent):
        inputWidget = QtGui.QDateEdit(parent) # defaultInputWidget
        inputWidget.setCalendarPopup(True)
        inputWidget.setDisplayFormat("dd.MM.yyyy")
        inputWidget.setObjectName("dat" + parent.objectName() + self.attribute.name)
        return inputWidget

    def setValue(self,  thisValue):
        if not thisValue:
            self.inputWidget.setDate(QtCore.QDate.currentDate())
        else:
            self.inputWidget.setDate(thisValue)

    def getValue(self):
        thisValue = self.inputWidget.date()
        return thisValue

class DdCheckBox(DdLineEdit):
    '''QCheckBox for a date field'''

    def __init__(self,  attribute):
        DdLineEdit.__init__(self,  attribute)

    def __str__(self):
        return "<ddui.DdCheckBox %s>" % str(self.attribute.name)

    def getFeatureValue(self,  layer,  feature,  db):
        '''returns a boolean representing the value in this field for this feature'''

        if feature.id() >= 0:
            fieldIndex = self.getFieldIndex(layer)
            thisValue = feature.attributeMap().get(fieldIndex,  "").toString()

            if thisValue.isEmpty():
                thisValue = None
            elif thisValue == QtCore.QString("f") or thisValue == QtCore.QString("false") or thisValue == QtCore.QString("False"):
                thisValue = False
            else:
                thisValue = True
        else: # new feature
            if self.attribute.hasDefault:
                thisValue = QtCore.QVariant(self.attribute.default).toBool()
            else:
                thisValue = None

        return thisValue

    def createInputWidget(self,  parent):
        inputWidget = QtGui.QCheckBox(parent)
        inputWidget.setObjectName("chk" + parent.objectName() + self.attribute.name)
        return inputWidget

    def setValue(self,  thisValue):
        if None == thisValue: #handle Null values
            self.inputWidget.setTristate(True)
            self.inputWidget.setCheckState(1)
        else:
            self.inputWidget.setChecked(thisValue)

    def stateChanged(self,  newState):
        if self.inputWidget.isTristate() and newState != 1:
            self.inputWidget.setTristate(False)

    def getValue(self):
        state = self.inputWidget.checkState()
        #QtGui.QMessageBox.information(None, "", str(state))
        if state == 0:
            thisValue = False
        elif state == 1:
            thisValue = None
        elif state == 2:
            thisValue = True

        return thisValue

class DdTextEdit(DdLineEdit):
    '''QTextEdit  for a date field'''

    def __init__(self,  attribute):
        DdLineEdit.__init__(self,  attribute)

    def __str__(self):
        return "<ddui.DdTextEdit %s>" % str(self.attribute.name)

    def createInputWidget(self,  parent):
        inputWidget = QtGui.QTextEdit(parent)
        inputWidget.setObjectName("txt" + parent.objectName() + self.attribute.name)
        return inputWidget

    def setupUi(self,  parent,  db):
        '''setup the label and add the inputWidget to parents formLayout'''
        self.inputWidget = self.createInputWidget(parent)
        self.inputWidget.setToolTip(self.attribute.comment)
        parent.layout().addWidget(self.inputWidget)

    def setValue(self,  thisValue):
        self.inputWidget.setPlainText(thisValue)

    def getValue(self):
        thisValue = self.inputWidget.toPlainText()

        if thisValue.isEmpty():
            thisValue = None

        return thisValue

class DdN2mListWidget(DdInputWidget):
    '''a clickable tree widget for simple n2m relations'''

    def __init__(self,  attribute):
        DdInputWidget.__init__(self,  attribute)

    def __str__(self):
        return "<ddui.DdN2mTreeWidget %s>" % str(self.attribute.name)

    def createInputWidget(self,  parent):
        inputWidget = QtGui.QListWidget(parent) # defaultInputWidget
        inputWidget.setObjectName("lst" + parent.objectName() + self.attribute.name)
        return inputWidget

    def initialize(self,  layer,  feature,  db):
        query = QtSql.QSqlQuery(db)
        query.prepare(self.attribute.displayStatement)
        query.bindValue(":featureId", QtCore.QVariant(feature.id()))
        query.exec_()

        if query.isActive():
            self.inputWidget.clear()

            while query.next(): # returns false when all records are done
                parentId = int(query.value(0).toString())
                parent = unicode(query.value(1).toString())
                checked = int(query.value(2).toString())
                #QtGui.QMessageBox.information(None,"debug",str(parentId) + ": " + parent + " checked = " + str(checked))
                parentItem = QtGui.QListWidgetItem(QtCore.QString(parent))
                parentItem.id = parentId
                parentItem.setCheckState(checked)
                self.inputWidget.addItem(parentItem)
            query.finish()
        else:
            self.raiseDbError(query)

    def setupUi(self,  parent,  db):
        '''setup the label and add the inputWidget to parents formLayout'''
        self.inputWidget = self.createInputWidget(parent)
        self.inputWidget.setToolTip(self.attribute.comment)
        parent.layout().addWidget(self.inputWidget)

    def save(self,  layer,  feature,  db):
        featureId = feature.id()
        deleteQuery = QtSql.QSqlQuery(db)
        deleteQuery.prepare(self.attribute.deleteStatement)
        deleteQuery.bindValue(":featureId", QtCore.QVariant(featureId))
        deleteQuery.exec_()

        if deleteQuery.isActive():
            for i in range(self.inputWidget.count()):
                item = self.inputWidget.item(i)

                if item.checkState() == 2:
                    itemId = item.id
                    insertQuery = QtSql.QSqlQuery(db)
                    insertQuery.prepare(self.attribute.insertStatement)
                    insertQuery.bindValue(":featureId", QtCore.QVariant(featureId))
                    insertQuery.bindValue(":itemId", QtCore.QVariant(itemId))
                    insertQuery.exec_()

                    if insertQuery.isActive():
                        insertQuery.finish()
                    else:
                        self.raiseDbError(insertQuery)

            deleteQuery.finish()
        else:
            self.raiseDbError(deleteQuery)

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



