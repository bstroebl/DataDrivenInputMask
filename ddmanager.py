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
from qgis.gui import *
from dderror import DdError,  DbError
from ddui import DataDrivenUi
from ddattribute import *
from dddialog import DdDialog,  DdSearchDialog

class DdManager(object):
    """DdManager manages all masks in the current project"""

    def __init__(self,  iface):
        self.iface = iface
        self.ddLayers = dict()
        settings = QtCore.QSettings()
        settings.beginGroup("Qgis/digitizing")
        a = settings.value("line_color_alpha",200,type=int)
        b = settings.value("line_color_blue",0,type=int)
        g = settings.value("line_color_green",0,type=int)
        r = settings.value("line_color_red",255,type=int)
        lw = settings.value("line_width",1,type=int)
        settings.endGroup()
        self.rubberBandColor = QtGui.QColor(r, g, b, a)
        self.rubberBandWidth = lw
        self.showConfigInfo = True

    def __debug(self,  title,  str):
        QgsMessageLog.logMessage(title + "\n" + str)

    def __str__(self):
        return "<ddui.DdManager>"

    def highlightFeature(self,  layer,  feature):
        '''highlight the feature if it has a geometry'''
        geomType = layer.geometryType()

        if geomType <= 2:
            if geomType == 0:
                marker = QgsVertexMarker(self.iface.mapCanvas())
                marker.setIconType(3) # ICON_BOX
                marker.setColor(self.rubberBandColor)
                marker.setIconSize(12)
                marker.setPenWidth (3)
                marker.setCenter(feature.geometry().asPoint())
                return marker
            else:
                rubberBand = QgsRubberBand(self.iface.mapCanvas())
                rubberBand.setColor(self.rubberBandColor)
                rubberBand.setWidth(self.rubberBandWidth)
                rubberBand.setToGeometry(feature.geometry(),  layer)
                return rubberBand
        else:
            return None

    def initLayer(self,  layer,  skip = [],  labels = {},  fieldOrder = [],  fieldGroups = {},  minMax = {},  noSearchFields = [],  \
        showParents = True,  createAction = True,  db = None,  inputMask = True,  searchMask = True,  \
        inputUi = None,  searchUi = None,  helpText = ""):
        '''api method initLayer: initialize this layer with a data-driven input mask.
        In case there is configuration for this layer in the database read this
        configuration and apply what is provided there.
        Returns a Boolean stating the success of the initialization
        Parameters:
        WARNING: if config tables are used, the parameters' objects survive
        and are thus applied to the next layer, too. Be sure to also pass ALL optional
        paramerters when calling initLayer()

        - layer [QgsVectorLayer]
        - skip [array [string]]: field names to not show
        - labels [dict] with entries: "fieldname": "label"
        - fieldOrder [array[string]]: containing the field names in the order they should be shown
        - fieldGroups [dict] with entries: fieldName: [tabTitle, tabTooltip] for each group a tab is created and the fields from fieldName onwards (refers to fieldOrder) are grouped in this tab; tabTooltip is optional
        - minMax [dict] with entries: "fieldname": [min, max] - strings; use for numerical or date fields only!
        - noSearchFields [array[string]] with fields not to be shown in the search form, if empty all fields are shown. Skipped fields are never shown in the search form, no matter if they are included here
        - showParents [Boolean] show tabs for 1-to-1 relations (parents)
        - createAction [Boolean]: add an action to the layer's list of actions
        - db [QtSql.QSqlDatabase]
        - inputMask [Boolean]: create a data-edit mask
        - searchMask [Boolean]: create a data-search mask
        - inputUi [ddui.DdDialogWidget]: apply this inputUi
        - searchUi [ddui.DdDialogWidget]: apply this as search ui
        - helpText [string] help text for this mask, may be html formatted'''

        thisSize = None # stores the size of the DdDialog

        if inputUi != None:
            inputMask = False # do not make one but use the one provided

        if searchUi != None:
            searchMask = False # do not make one but use the one provided

        if u'PostgreSQL' != layer.dataProvider().storageType()[0:10] :
            DdError(QtGui.QApplication.translate("DdError", "Layer is not a PostgreSQL layer: ", None,
                                                           QtGui.QApplication.UnicodeUTF8) + layer.name(),  iface = self.iface)
            return False
        else:
            if not db:
                db = self.__createDb(layer)

            thisTable = self.makeDdTable(layer,  db)

            if thisTable == None:
                return False
            else:
                if inputMask or searchMask:
                    # check for config tables
                    ddConfigTable = DdTable(schemaName = "public",  tableName = "dd_table")
                    readConfigTables = self.isAccessible(db,  ddConfigTable,  showError = False)

                    if not readConfigTables:
                        if self.showConfigInfo:
                            self.iface.messageBar().pushMessage(QtGui.QApplication.translate("DdInfo",
                                "Config tables either not found or not accessible, loading default mask", None,
                                QtGui.QApplication.UnicodeUTF8))
                            self.showConfigInfo = False

                    # we want at least one automatically created mask
                    ddui = DataDrivenUi(self.iface)
                    autoInputUi,  autoSearchUi = ddui.createUi(thisTable,  db,  skip,  labels,  fieldOrder,  fieldGroups,  minMax,  \
                                                  noSearchFields, showParents,  True,  inputMask,  searchMask,  helpText,  createAction,  \
                                                  readConfigTables = readConfigTables)

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

                    self.ddLayers[layer.id()] = [thisTable,  db,  inputUi,  searchUi,  showParents,  thisSize]
                    self.__connectSignals(layer)

                    if createAction:
                        self.addAction(layer)

                    return True
                else:
                    # no auto masks, both were provided
                    self.ddLayers[layer.id()] = [thisTable,  db,  inputUi,  searchUi,  showParents,  thisSize]
                    return True

    def makeDdTable(self,  layer,  db = None):
        '''make a DdTable object from the passed in layer, returns None, if layer is not suitable'''
        if 0 != layer.type():   # not a vector layer
            DdError(QtGui.QApplication.translate("DdError", "Layer is not a vector layer: ", None,
                                                           QtGui.QApplication.UnicodeUTF8) + layer.name(),  iface = self.iface)
            return None
        else:
            if u'PostgreSQL' != layer.dataProvider().storageType()[0:10] :
                DdError(QtGui.QApplication.translate("DdError", "Layer is not a PostgreSQL layer: ", None,
                                                               QtGui.QApplication.UnicodeUTF8) + layer.name(),  iface = self.iface)
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
                                                                       QtGui.QApplication.UnicodeUTF8) + layer.name(),  iface = self.iface)
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

    def showFeatureForm(self,  layer,  feature,  showParents = True, title = None,  askForSave = True):
        '''api method showFeatureForm: show the data-driven input mask for a layer and a feature
        if the data provider allows editing the layer is turned into editing mode
        if the user clicks OK all changes to teh feature are committed (no undo!)
        if askForSave is true and the layer has pending changes the user is asked if the changes
        shall be commited before the mask is opened
        returns 1 if user clicked OK, 0 if CANCEL'''

        layerValues = self.__getLayerValues(layer,  inputMask = True,  searchMask = False)

        if layerValues != None:
            parentsInMask = layerValues[4]

            if parentsInMask and not showParents:
                self.initLayer(layer,  showParents = False,  inputMask = True,  searchMask = False,  \
                            skip = [],  labels = {},  fieldOrder = [],  fieldGroups = {},  minMax = {},  noSearchFields = [],  \
                            createAction = True,  db = None,   inputUi = None,  searchUi = None,  helpText = ""
                               )
                layerValues = self.__getLayerValues(layer,  inputMask = True,  searchMask = False)

        if layerValues != None:
            result = 1
            wasEditable = layer.isEditable()

            if wasEditable:
                if layer.isModified() and askForSave:
                    #ask user to save or discard changes
                    reply = QtGui.QMessageBox.question(None, QtGui.QApplication.translate("DdInfo", "Unsaved changes", None,
                        QtGui.QApplication.UnicodeUTF8),
                        QtGui.QApplication.translate("DdInfo", "Do you want to save the changes to layer ", None,
                        QtGui.QApplication.UnicodeUTF8) + layer.name() + "?",
                        QtGui.QMessageBox.Discard | QtGui.QMessageBox.Cancel | QtGui.QMessageBox.Save)

                    if reply == QtGui.QMessageBox.Cancel:
                        result = 0
                    else:
                        if reply == QtGui.QMessageBox.Discard:
                            if not layer.rollBack():
                                DdError(QtGui.QApplication.translate("DdError", "Could not discard changes for layer:", None,
                                   QtGui.QApplication.UnicodeUTF8) + " "+ layer.name(),  iface = self.iface)
                                result = 0
                        elif reply == QtGui.QMessageBox.Save:
                            if not layer.commitChanges():
                                DdError(QtGui.QApplication.translate("DdError", "Could not save changes for layer:", None,
                                    QtGui.QApplication.UnicodeUTF8)  + " " + layer.name(),  iface = self.iface)
                                result = 0

                        if result == 1:
                            layer.startEditing()
            else:
                if self.isEditable(layer):
                    layer.startEditing()

            if result == 1:
                highlightGeom = self.highlightFeature(layer,  feature)
                db = layerValues[1]
                ui = layerValues[2]
                thisSize = layerValues[5]

                dlg = DdDialog(self,  ui,  layer,  feature,  db,  title = title)
                dlg.show()

                if thisSize != None:
                    dlg.resize(thisSize)

                result = dlg.exec_()

                if result == 1:
                    layer.emit(QtCore.SIGNAL('layerModified()'))
                # store size
                thisSize = dlg.size()
                self.ddLayers[layer.id()][5] = thisSize
                #handle highlightGeom
                if highlightGeom != None:
                    self.iface.mapCanvas().scene().removeItem(highlightGeom)
                    highlightGeom = None

                if not wasEditable:
                    layer.rollBack()
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
            thisSize = layerValues[5]
            dlg = DdSearchDialog(self,  searchUi,  layer,  db)
            dlg.show()

            if thisSize != None:
                dlg.resize(thisSize)

            result = dlg.exec_()
            thisSize = dlg.size()
            self.ddLayers[layer.id()][5] = thisSize

            return result

    def showDdForm(self,  fid):
        aLayer = self.iface.activeLayer()

        if aLayer != None:
            feat = QgsFeature()

            if aLayer.geometryType() <= 2: # has geometry
                featureFound = aLayer.getFeatures(QgsFeatureRequest().setFilterFid(fid)).nextFeature(feat)
            else:
                featureFound = aLayer.getFeatures(QgsFeatureRequest().setFilterFid(fid).setFlags(QgsFeatureRequest.NoGeometry)).nextFeature(feat)

            if featureFound:
                self.showFeatureForm(aLayer,  feat)

    def setUi(self,  layer,  ui,  searchUi = None,  showParents = None,  thisSize = None):
        '''api method to exchange the default ui with a custom ui'''

        layerValues = self.__getLayerValues(layer)

        if layerValues != None:
            #QtGui.QMessageBox.information(None, "", str(layerValues[2]))
            thisTable = layerValues[0]
            db = layerValues[1]

            if searchUi == None:
                searchUi = layerValues[3]

            if showParents == None:
                showParents = layerValues[4]

            self.ddLayers[layer.id()] = [thisTable,  db,  ui,  searchUi,  showParents,  thisSize]


    def getDbForLayer(self,  layer):
        return self.__createDb(layer)

    def existsInDb(self,  ddTable,  db):
        return self.__getOid(ddTable,  db) != None

    def setDb(self,  layer,  db):
        '''api method to set the db for a layer'''
        layerValues = self.__getLayerValues(layer)

        if layerValues != None:
            thisTable = layerValues[0]
            oldDb = layerValues[1]
            self.__disconnectDb(oldDb)
            ui = layerValues[2]
            searchUi = layerValues[3]
            showParents = layerValues[4]
            thisSize = layerValues[5]
            self.ddLayers[layer.id()] = [thisTable,  db,  ui,  searchUi,  showParents,  thisSize]

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

    def isEditable(self,  layer):
        '''check if data provider allows editing of table'''
        dp = layer.dataProvider()
        caps = dp.capabilities()
        return (caps & QgsVectorDataProvider.AddFeatures and caps & QgsVectorDataProvider.DeleteFeatures and \
            caps & QgsVectorDataProvider.ChangeAttributeValues)

    def isAccessible(self,  db,  ddTable,  showError = True):
        '''check if user has right to access this table'''
        query = QtSql.QSqlQuery(db)
        sQuery = "SELECT * FROM \"" + ddTable.schemaName + "\".\"" + ddTable.tableName + "\" LIMIT 1;"
        query.prepare(sQuery)
        query.exec_()

        if query.isActive():
            query.finish()
            return True
        else:
            query.finish()

            if showError:
                self.showQueryError(query,  True)
            return False

    def loadPostGISLayer(self,  db, ddTable, displayName = None,
        geomColumn = None, whereClause = None, keyColumn = None,
        intoDdGroup = True):

        if not self.isAccessible(db,  ddTable):
            DdError(QtGui.QApplication.translate("DdError", "Cannot not load table: ", None,
                QtGui.QApplication.UnicodeUTF8) + ddTable.schemaName + "." + ddTable.tableName,  fatal = True,  iface = self.iface)

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
        # double check if layer is valid
        if not vlayer.dataProvider().isValid():
            DdError(QtGui.QApplication.translate("DdError", "Cannot not load table: ", None,
                QtGui.QApplication.UnicodeUTF8) + ddTable.schemaName + "." + ddTable.tableName,  fatal = True,  iface = self.iface)

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

        if layer:
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
            if self.initLayer(layer,  skip = [],  labels = {},  fieldOrder = [],  fieldGroups = {},  minMax = {},  noSearchFields = [],  \
                showParents = True,  createAction = True,  db = None,  inputMask = True,  searchMask = True,  \
                inputUi = None,  searchUi = None,  helpText = ""):
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

    def __executeConfigQuery(self,  db, sQuery):
        '''execute a query for manipulating the config tables
        returns the query or None on error '''
        query = QtSql.QSqlQuery(db)
        query.exec_(sQuery)

        if query.isActive():
            return query
        else:
            query.finish()
            self.showQueryError(query,  True)
            return None


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
                                                 QtGui.QApplication.UnicodeUTF8) + database,  iface = self.iface)
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
                                                 QtGui.QApplication.UnicodeUTF8) + database,  iface = self.iface)
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

    def changeConfigTables(self,  db):
        '''function to update the config tables if anything changes'''
        changeToVersion060 = False
        sQuery = "SELECT t.typname as typ \
        FROM pg_attribute att \
        JOIN pg_type t ON att.atttypid = t.oid \
        JOIN pg_class c ON attrelid = c.oid \
        JOIN pg_namespace n ON c.relnamespace = n.oid \
        WHERE n.nspname = \'public\' AND c.relname = \'dd_field\' \
        AND attname= \'field_min\'"
        query = self.__executeConfigQuery(db,  sQuery)

        if query != None:
            while query.next():
                changeToVersion060 = query.value(0) == "float8"
            query.finish()
        else:
            return False

        if changeToVersion060:
            #recreate table and transfer data
            sQuery = "ALTER TABLE \"public\".\"dd_field\" RENAME \"field_min\" TO \"field_min_old\"; \
            ALTER TABLE \"public\".\"dd_field\" RENAME \"field_max\" TO \"field_max_old\"; \
            ALTER TABLE \"public\".\"dd_field\" ADD COLUMN \"field_min\" VARCHAR(32) NULL; \
            ALTER TABLE \"public\".\"dd_field\" ADD COLUMN \"field_max\" VARCHAR(32) NULL; \
            COMMENT ON COLUMN  \"public\".\"dd_field\".\"field_min\" IS \'min value of the field (only for numeric and date fields). Use point as decimal seperator, format date as \"yyyy-MM-dd\", insert \"today\" to set the min date on the current date.\';\
            COMMENT ON COLUMN  \"public\".\"dd_field\".\"field_max\" IS \'max value of the field (only for numeric and date fields). Use point as decimal seperator, format date as \"yyyy-MM-dd\", insert \"today\" to set the max date on the current date.\'; "
            query = self.__executeConfigQuery(db,  sQuery)

            if query != None:
                query.finish()
            else:
                return False

            sQuery = "UPDATE \"public\".\"dd_field\" SET \"field_min\" = CAST (\"field_min_old\" as varchar) WHERE \"field_min_old\" IS NOT NULL; \
            UPDATE \"public\".\"dd_field\" SET \"field_max\" = CAST (\"field_max_old\" as varchar) WHERE \"field_max_old\" IS NOT NULL;"

            query = self.__executeConfigQuery(db,  sQuery)

            if query != None:
                query.finish()
            else:
                return False

            sQuery = "ALTER TABLE \"public\".\"dd_field\" DROP COLUMN \"field_min_old\"; \
            ALTER TABLE \"public\".\"dd_field\" DROP COLUMN \"field_max_old\";"
            query = self.__executeConfigQuery(db,  sQuery)

            if query != None:
                query.finish()
            else:
                return False

        return True

    def createConfigTables(self,  db):
        sQuery = "CREATE TABLE  \"public\".\"dd_table\" (\
            \"id\" SERIAL NOT NULL,\
            \"table_schema\" VARCHAR(256) NOT NULL,\
            \"table_name\" VARCHAR(256) NOT NULL,\
            \"table_help\" TEXT NULL,\
            \"table_action\" BOOLEAN NOT NULL DEFAULT \'t\',\
            PRIMARY KEY (\"id\"));\
        GRANT SELECT ON TABLE \"public\".\"dd_table\" TO public;\
        COMMENT ON TABLE \"public\".\"dd_table\" IS \'DataDrivenInputMask: contains tables with a configuration for the mask, no need to input tables for which the default data-driven mask is to be shown\';\
        COMMENT ON COLUMN \"public\".\"dd_table\".\"table_schema\" IS \'name of the schema\';\
        COMMENT ON COLUMN \"public\".\"dd_table\".\"table_name\" IS \'name of the table\';\
        COMMENT ON COLUMN \"public\".\"dd_table\".\"table_help\" IS \'Help string to be shown if user clicks the help button, this string can be HTML formatted.\';\
        COMMENT ON COLUMN \"public\".\"dd_table\".\"table_action\" IS \'Create a layer action to show the mask\';\
        INSERT INTO \"public\".\"dd_table\" (\"table_schema\", \"table_name\") VALUES(\'public\', \'dd_table\');\
        INSERT INTO \"public\".\"dd_table\" (\"table_schema\", \"table_name\") VALUES(\'public\', \'dd_tab\');\
        INSERT INTO \"public\".\"dd_table\" (\"table_schema\", \"table_name\") VALUES(\'public\', \'dd_field\');\
        CREATE TABLE  \"public\".\"dd_tab\" (\
            \"id\" SERIAL NOT NULL,\
            \"dd_table_id\" INTEGER NOT NULL,\
            \"tab_alias\" VARCHAR(256) NULL,\
            \"tab_order\" INTEGER NOT NULL DEFAULT 0,\
            \"tab_tooltip\" VARCHAR(256) NULL,\
            PRIMARY KEY (\"id\"),\
            CONSTRAINT \"fk_dd_tab_dd_table\"\
                FOREIGN KEY (\"dd_table_id\")\
                REFERENCES \"public\".\"dd_table\" (\"id\")\
                ON DELETE CASCADE\
                ON UPDATE CASCADE);\
        GRANT SELECT ON TABLE \"public\".\"dd_tab\" TO public;\
        CREATE INDEX \"idx_fk_dd_tab_dd_table_idx\" ON \"public\".\"dd_tab\" (\"dd_table_id\");\
        COMMENT ON TABLE \"public\".\"dd_tab\" IS \'DataDrivenInputMask: contains tabs for tables\';\
        COMMENT ON COLUMN \"public\".\"dd_tab\".\"dd_table_id\" IS \'Table for which this tab is used\';\
        COMMENT ON COLUMN \"public\".\"dd_tab\".\"tab_alias\" IS \'Label the tab with this string, leave empty if you want the data-driven tabs\';\
        COMMENT ON COLUMN \"public\".\"dd_tab\".\"tab_order\" IS \'Order of the tabs in the mask (if a mask contains more than one tabs)\';\
        COMMENT ON COLUMN \"public\".\"dd_tab\".\"tab_tooltip\" IS \'tooltip to be shown for this tab\';\
        INSERT INTO \"public\".\"dd_tab\" (\"dd_table_id\") VALUES(1);\
        INSERT INTO \"public\".\"dd_tab\" (\"dd_table_id\") VALUES(2);\
        INSERT INTO \"public\".\"dd_tab\" (\"dd_table_id\") VALUES(3);\
        CREATE TABLE  \"public\".\"dd_field\" (\
            \"id\" SERIAL NOT NULL,\
            \"dd_tab_id\" INTEGER NOT NULL,\
            \"field_name\" VARCHAR(256) NOT NULL,\
            \"field_alias\" VARCHAR(256) NULL,\
            \"field_skip\" BOOLEAN NOT NULL DEFAULT \'f\',\
            \"field_search\" BOOLEAN NOT NULL DEFAULT \'t\',\
            \"field_order\" INTEGER NOT NULL DEFAULT 0,\
            \"field_min\" VARCHAR(32) NULL,\
            \"field_max\" VARCHAR(32) NULL,\
            PRIMARY KEY (\"id\"),\
            CONSTRAINT \"fk_dd_field_dd_tab\"\
                FOREIGN KEY (\"dd_tab_id\")\
                REFERENCES \"public\".\"dd_tab\" (\"id\")\
                ON DELETE CASCADE\
                ON UPDATE CASCADE);\
        GRANT SELECT ON TABLE \"public\".\"dd_field\" TO public;\
        CREATE INDEX \"idx_fk_dd_field_dd_tab_idx\" ON \"public\".\"dd_field\" (\"dd_tab_id\");\
        COMMENT ON TABLE  \"public\".\"dd_field\" IS \'DataDrivenInputMask: the data-driven mask for fields can be configured here.\';\
        COMMENT ON COLUMN  \"public\".\"dd_field\".\"dd_tab_id\" IS \'All fields not included here will be put in the tab with the highest tab_order. One and the same field should be included in _one_ tab only.\';\
        COMMENT ON COLUMN  \"public\".\"dd_field\".\"field_name\" IS \'Name of the field in the database\';\
        COMMENT ON COLUMN  \"public\".\"dd_field\".\"field_alias\" IS \'Alias of the field to be used in the mask\';\
        COMMENT ON COLUMN  \"public\".\"dd_field\".\"field_skip\" IS \'skip this field in the input and search mask, i.e. hide it from the user\';\
        COMMENT ON COLUMN  \"public\".\"dd_field\".\"field_search\" IS \'include this field in the search mask, if skip is true the field is not shown in the search mask, no matter if search is true\';\
        COMMENT ON COLUMN  \"public\".\"dd_field\".\"field_order\" IS \'order of the fields in the mask\';\
        COMMENT ON COLUMN  \"public\".\"dd_field\".\"field_min\" IS \'min value of the field (only for numeric and date fields). Use point as decimal seperator, format date as \"yyyy-MM-dd\", insert \"today\" to set the min date on the current date or \"today +/- num_days\" for a certain day relative to the current date.\';\
        COMMENT ON COLUMN  \"public\".\"dd_field\".\"field_max\" IS \'max value of the field (only for numeric and date fields). Use point as decimal seperator, format date as \"yyyy-MM-dd\", insert \"today\" to set the max date on the current date or \"today +/- num_days\" for a certain day relative to the current date.\';\
        INSERT INTO \"public\".\"dd_field\" (\"dd_tab_id\", \"field_name\", \"field_skip\") VALUES(1, \'id\', \'t\');\
        INSERT INTO \"public\".\"dd_field\" (\"dd_tab_id\", \"field_name\", \"field_skip\") VALUES(2, \'id\', \'t\');\
        INSERT INTO \"public\".\"dd_field\" (\"dd_tab_id\", \"field_name\", \"field_skip\") VALUES(3, \'id\', \'t\');"

        query = self.__executeConfigQuery(db,  sQuery)

        if query != None:
            query.finish()
            self.iface.messageBar().pushMessage(QtGui.QApplication.translate("DdInfo",
                    "Config tables created! SELECT has been granted to \"public\".", None,
                    QtGui.QApplication.UnicodeUTF8))
            return True
        else:
            return False

    def showQueryError(self, query,  withSql = False):
        self.iface.messageBar().pushMessage("Database Error",  "%(error)s" % {"error": query.lastError().text()}, level=QgsMessageBar.CRITICAL)

        if withSql:
            self.iface.messageBar().pushMessage("Query",  "%(query)s" % {"query": query.lastQuery()}, level=QgsMessageBar.CRITICAL)
