# -*- coding: utf-8 -*-
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
 This script initializes the plugin, making it known to QGIS.
"""
def name():
    return "Data-driven Input Mask"
def description():
    return "Applies a data-driven input mask to any PostGIS-Layer"
def version():
    return "Version 0.1.2"
def icon():
    return "icon.png"
def qgisMinimumVersion():
    return "1.8"
def classFactory(iface):
    # load DataDrivenInputMask class from file DataDrivenInputMask
    from datadriveninputmask import DataDrivenInputMask
    return DataDrivenInputMask(iface)
