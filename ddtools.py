# -*- coding: utf-8 -*-
"""
ddtools
--------
collection of routines needed throughout the plugin
"""
from __future__ import absolute_import
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
from qgis.PyQt import QtSql, QtCore, QtGui, QtWidgets
from qgis.core import *
from qgis.gui import *
from .dderror import DbError
from .ddattribute import *

def getFeatureForId(layer,  fid,  withGeom = True):
    feat = QgsFeature()
    retValue = None
    request = QgsFeatureRequest()
    uri = QgsDataSourceUri(layer.dataProvider().dataSourceUri())
    pkFieldName = uri.keyColumn()
    request = request.setFilterExpression(
        pkFieldName + " = " + str(fid))

    if not withGeom:
        request = request.setFlags(QgsFeatureRequest.NoGeometry)

    if layer.getFeatures(request).nextFeature(feat):
        retValue = feat

    return retValue

def getOid(thisTable,  db):
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

def getIntValidator(parent, attribute, min = None, max = None):
    '''
    make an Integer validator for this DdAttribute's min and max values
    '''

    thisMin = attribute.min
    # integer attributes always have a min and max corresponding to the min/max values of the pg data type

    if min != None:
        if thisMin != None:
            if isinstance(min, int):
                if min < thisMin:
                    thisMin = min
                    # make sure current value is allowed although attribute's min might be different
        else:
            thisMin = min

    thisMax = attribute.max

    if max != None:
        if thisMax != None:
            if isinstance(max, int):
                if max > thisMax:
                    thisMax = max
                    # make sure current value is allowed although attribute's max might be different
        else:
            thisMax = max

    validator = QtGui.QIntValidator(parent)
    loc = QtCore.QLocale.system()
    loc.setNumberOptions(QtCore.QLocale.RejectGroupSeparator)
    validator.setLocale(loc)

    if isinstance(thisMin,  int):
        validator.setBottom(thisMin)

    if isinstance(thisMax,  int):
        validator.setTop(thisMax)

    return validator

def getDoubleValidator(parent, attribute, min = None, max = None):
    '''
    make a double validator for this DdAttribute's mi and max values
    '''
    validator = QtGui.QDoubleValidator(parent)
    loc = QtCore.QLocale.system()

    # if locale and database decimal separator differ and a db default has been inserted into
    # a new feature we run into trouble if not making sure that min and max are floats

    if attribute.min != None:
        thisMin = attribute.min

        if min != None:
            success = True

            try:
                min = float(min)
            except ValueError:
                min,  succcess = loc.toFloat(min)

            if success:
                if min < thisMin:
                    thisMin = min

        validator.setBottom(thisMin)

    if attribute.max != None:
        thisMax = attribute.max

        if max != None:
            success = True

            try:
                max = float(max)
            except ValueError:
                max,  succcess = loc.toFloat(max)

            if success:
                if max > thisMax:
                    thisMax = max

        validator.setTop(thisMax)

    validator.setNotation(QtGui.QDoubleValidator.StandardNotation)
    loc.setNumberOptions(QtCore.QLocale.RejectGroupSeparator)
    validator.setLocale(loc)
    return validator




