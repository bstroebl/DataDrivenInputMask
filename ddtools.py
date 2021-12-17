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
from qgis.PyQt import QtSql, QtCore, QtGui
from qgis.PyQt.QtGui import QValidator
from qgis.core import QgsFeature, QgsFeatureRequest, QgsDataSourceUri
from .dderror import DbError

import re


class DDIMIntValidator(QValidator):
    def __init__(self, parent, min=None, max=None):
        QValidator.__init__(parent)
        self.min = min
        self.max = max

    def fixup(self, input):
        return re.sub('\\D', '', input)

    def validate(self, input, pos):
        if input == '':
            return QValidator.Intermediate, input, pos

        try:
            v = int(input)

            if self.min is not None and v < self.min:
                return QValidator.Invalid, input, pos

            if self.max is not None and v > self.max:
                return QValidator.Invalid, input, pos

            return QValidator.Acceptable, input, pos
        except ValueError:
            return QValidator.Invalid, input, pos


def getFeatureForId(layer, fid, withGeom=True):
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


def getOid(thisTable, db):
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


def getIntValidator(parent, attribute, min=None, max=None):
    '''
    make an Integer validator for this DdAttribute's min and max values
    '''

    thisMin = attribute.min
    # integer attributes always have a min and max corresponding to the min/max values of the pg data type

    if min is not None:
        if thisMin is not None:
            if isinstance(min, int):
                if min < thisMin:
                    thisMin = min
                    # make sure current value is allowed although attribute's min might be different
        else:
            thisMin = min

    thisMax = attribute.max

    if max is not None:
        if thisMax is not None:
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

    try:
        if isinstance(thisMin, int):
            validator.setBottom(thisMin)
        if isinstance(thisMax, int):
            validator.setTop(thisMax)
    except OverflowError:
        validator = DDIMIntValidator(parent, thisMin, thisMax)

    return validator


def getDoubleValidator(parent, attribute, min=None, max=None):
    '''
    make a double validator for this DdAttribute's mi and max values
    '''
    validator = QtGui.QDoubleValidator(parent)
    loc = QtCore.QLocale.system()

    # if locale and database decimal separator differ and a db default has been inserted into
    # a new feature we run into trouble if not making sure that min and max are floats

    if attribute.min is not None:
        thisMin = attribute.min

        if min is not None:
            success = True

            try:
                min = float(min)
            except ValueError:
                min, success = loc.toFloat(min)

            if success:
                if min < thisMin:
                    thisMin = min

        validator.setBottom(thisMin)

    if attribute.max is not None:
        thisMax = attribute.max

        if max is not None:
            success = True

            try:
                max = float(max)
            except ValueError:
                max, success = loc.toFloat(max)

            if success:
                if max > thisMax:
                    thisMax = max

        validator.setTop(thisMax)

    validator.setNotation(QtGui.QDoubleValidator.StandardNotation)
    loc.setNumberOptions(QtCore.QLocale.RejectGroupSeparator)
    validator.setLocale(loc)
    return validator
