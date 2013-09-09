# -*- coding: utf-8 -*-
"""
ddmanager
--------
Class that steers the DataDrivenUI
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
from ddui import DataDrivenUi
from ddattribute import *
from dddialog import DdDialog,  DdSearchDialog

class DdManager(object):
    """DdManager manages all masks in the current project"""

    def __init__(self,  iface):
        self.iface = iface
        self.ddLayers = dict()

    def __debug(self,  title,  str):
        QgsMessageLog.logMessage(title + "\n" + str)

    def __str__(self):
        return "<ddui.DdManager>"

    def initLayer(self,  layer,  skip = [],  labels = {},  fieldOrder = [],  minMax = {},  searchFields = [],  \
        showParents = True,  createAction = True,  db = None,  inputMask = True,  searchMask = True,  \
        inputUi = None,  searchUi = None):
        '''api method initLayer: initialize the layer with a data-driven input mask
        Returns a Boolean stating the success of the initialization
        Paramters: see also ddui.DataDrivenUi.createUi()
        createAction [Boolean]: add an action to the layer's list of actions
        db [QtSql.QSqlDatabase]
        inputUi [ddui.DdDialogWidget]: apply this inputUi
        searchUi [ddui.DdDialogWidget]: apply this as search ui'''

        self.__debug("initLayer",  layer.name() + " showParents: " + str(showParents))
        if inputUi != None:
            inputMask = False # do not make one but use the one provided

        if searchUi != None:
            searchMask = False # do not make one but use the one provided

        if u'PostgreSQL' != layer.dataProvider().storageType()[0:10] :
            DdError(QtGui.QApplication.translate("DdError", "Layer is not a PostgreSQL layer: ", None,
                                                           QtGui.QApplication.UnicodeUTF8) + layer.name())
            return False
        else:
            if not db:
                db = self.__createDb(layer)

            thisTable = self.makeDdTable(layer,  db)

            if thisTable == None:
                return False
            else:
                if inputMask or searchMask:
                    # we want at least one automatically created mask
                    ddui = DataDrivenUi(self.iface)
                    autoInputUi,  autoSearchUi = ddui.createUi(thisTable,  db,  skip,  labels,  fieldOrder,  minMax,  \
                                                  searchFields, showParents,  True,  inputMask,  searchMask)

                    if inputUi == None:
                        # use the automatically created mask if none has been provided
                        inputUi = autoInputUi

                    if searchUi == None:
                        searchUi = autoSearchUi

                    if not inputMask or not searchMask:
                        # at least one mask shall not be initialized
                        try:
                            layerValues = self.ddLayers[layer.id]
                            # see if the layer has been initialized already
                        except KeyError:
                            layerValues = None

                        if layerValues != None:
                            # layer has been initialized before!
                            if not inputMask and inputUi == None:
                                # user did not provide a mask
                                inputUi = layerValues[2] # keep current
                            if not searchMask and searchUi == None:
                                searchUi = layerValues[3] # keep current
                    #else:
                        #self.ddLayers.pop(layer.id(),  None) # remove entries if they exist

                    self.ddLayers[layer.id()] = [thisTable,  db,  inputUi,  searchUi,  showParents]
                    self.__connectSignals(layer)

                    if createAction:
                        self.addAction(layer)

                    return True
                else:
                    # no auto masks, both were provided
                    self.ddLayers[layer.id()] = [thisTable,  db,  inputUi,  searchUi,  showParents]
                    return True

    def makeDdTable(self,  layer,  db = None):
        '''make a DdTable object from the passed in layer, returns None, if layer is not suitable'''
        if 0 != layer.type():   # not a vector layer
            DdError(QtGui.QApplication.translate("DdError", "Layer is not a vector layer: ", None,
                                                           QtGui.QApplication.UnicodeUTF8) + layer.name())
            return None
        else:
            if u'PostgreSQL' != layer.dataProvider().storageType()[0:10] :
                DdError(QtGui.QApplication.translate("DdError", "Layer is not a PostgreSQL layer: ", None,
                                                               QtGui.QApplication.UnicodeUTF8) + layer.name())
                return None
            else:
                if not db:
                    db = self.__createDb(layer)

                layerSrc = self.__analyzeSource(layer)
                relation = layerSrc["table"].split('"."')
                schema = relation[0].replace('"', '')
                table = relation[1].replace('"', '')
                thisTable = DdTable(schemaName = schema,  tableName = table,  title = layer.name())
                thisTable.oid = self.__getOid(thisTable,  db)
                comment = self.__getComment(thisTable,  db)

                if comment:
                    thisTable.comment = comment

                if not self.__isTable(thisTable,  db):
                    DdError(QtGui.QApplication.translate("DdError", "Layer is not a PostgreSQL table: ", None,
                                                                       QtGui.QApplication.UnicodeUTF8) + layer.name())
                    return None
                else:
                    return thisTable

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

    def showFeatureForm(self,  layer,  feature,  showParents = True):
        '''api method showFeatureForm: show the data-driven input mask for a layer and a feature
        returns 1 if user clicked OK, 0 if CANCEL'''

        layerValues = self.__getLayerValues(layer,  inputMask = True,  searchMask = False)

        if layerValues != None:
            parentsInMask = layerValues[4]

            if parentsInMask and not showParents:
                self.initLayer(layer,  showParents = False,  inputMask = True,  searchMask = False)
                layerValues = self.__getLayerValues(layer,  inputMask = True,  searchMask = False)

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

    def showSearchForm(self,  layer):
        '''api method showSearchForm: show the data-driven search mask for a layer
        returns 1 if user clicked OK, 0 if CANCEL'''
        layerValues = self.__getLayerValues(layer,  inputMask = False,  searchMask = True)

        if layerValues != None:
            #QtGui.QMessageBox.information(None, "", str(layerValues[2]))
            db = layerValues[1]
            searchUi = layerValues[3]
            dlg = DdSearchDialog(self,  searchUi,  layer,  db)
            dlg.show()
            result = dlg.exec_()

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
            searchUi = layerValues[3]
            self.ddLayers[layer.id()] = [thisTable,  db,  ui,  searchUi]

    def setDb(self,  layer,  db):
        '''api method to set the db for a layer'''
        layerValues = self.__getLayerValues(layer)

        if layerValues != None:
            thisTable = layerValues[0]
            oldDb = layerValues[1]
            self.__disconnectDb(oldDb)
            ui = layerValues[2]
            searchUi = layerValues[3]
            self.ddLayers[layer.id()] = [thisTable,  db,  ui,  searchUi]

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

    def __getLayerValues(self,  layer,  inputMask = True,  searchMask = True):
        '''Get this layer's values from ddLayers or create them'''

        try:
            layerValues = self.ddLayers[layer.id()]
        except KeyError:
            if self.initLayer(layer,  skip = []):
                layerValues = self.ddLayers[layer.id()]
            else:
                layerValues = None

        if layerValues != None:
            # check if needed masks are initialized
            inputMask = (inputMask and layerValues[2] == None)
            searchMask = (searchMask and layerValues[3] == None)

            if inputMask or searchMask:
                if self.initLayer(layer,  skip = [],  inputMask = inputMask,  searchMask = searchMask):
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
