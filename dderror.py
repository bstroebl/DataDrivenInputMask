# -*- coding: utf-8 -*-
"""
dderror
-----------------------------------
Error classes
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
from PyQt4 import QtGui

class DdError(object):
    '''General error'''
    def __init__(self,  value,  fatal = False):
        self.value = value

        if fatal:
            raise FatalError(value)
        else:
            QtGui.QMessageBox.warning(None, "DdError",  value)

    def __str__(self):
        return repr(self.value)

class DbError(object):
    '''error querying the DB'''
    def __init__(self,  query,  fatal = True):
        self.query = query
        QtGui.QMessageBox.warning(None, "DBError",  QtGui.QApplication.translate("DBError", "Database Error:", None,
                                                               QtGui.QApplication.UnicodeUTF8) + \
                                                               "%(error)s \n %(query)s" % {"error": query.lastError().text(),  "query": query.lastQuery()})
        if fatal:
            raise FatalError("DBError exiting")
    def __str__(self):
        return repr(self.query.lastError())

class FatalError(Exception):
    def __init__(self,  value):
        self.value = value
    def __str__(self):
        return repr(self.value)
