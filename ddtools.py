# -*- coding: utf-8 -*-
"""
ddtools
--------
collection of routines needed throughout the plugin
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
from PyQt4 import QtSql
from qgis.core import *
from qgis.gui import *
from dderror import DdError,  DbError
from ddattribute import *

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

