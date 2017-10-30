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
from builtins import object
from qgis.PyQt import QtWidgets
from qgis.gui import QgsMessageBar
from qgis.core import QgsMessageLog

class DdError(object):
    '''General error'''
    def __init__(self,  value,  fatal = False,  iface = None,  showInLog = False):
        self.value = value

        if fatal:
            raise FatalError(value)
        else:
            if showInLog:
                QgsMessageLog.logMessage("DdError: " + value,  level=QgsMessageLog.CRITICAL)
            else:
                if iface:
                    iface.messageBar().pushMessage("DdError",
                        value, level=QgsMessageBar.CRITICAL,
                        duration = 10)
                else:
                    QtWidgets.QMessageBox.warning(None, "DdError",  value)

    def __str__(self):
        return repr(self.value)

class DbError(object):
    '''error querying the DB'''
    def __init__(self,  query,  fatal = True):
        self.query = query
        QtWidgets.QMessageBox.warning(None, "DBError",  QtWidgets.QApplication.translate("DBError", "Database Error:") + \
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
