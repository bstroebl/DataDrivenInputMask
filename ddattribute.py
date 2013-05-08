# -*- coding: utf-8 -*-
"""
ddattribute
---------------------
Each DdAttribute corresponds to an input widget in the mask or each input widget is based on exactly one DdAttribute.

General rules:
```````````````````````
#) every field has an input widget suitable for its type
#) no ARRAY typees are supported
#) supported types are: int4, int8, float, date, boolean, char, varchar, text
#) foreign keys are represented as comboboxes and are only supported if based on one field (exactly one fk field in the table references exactly one pk field in the referenced table)
#) the table referenced by a foreign key should have at least one field wit a notNull constraint apart from the primary key. This field will be used as display field in the combobox
#) if a varchar field is present in a table referenced by a foreign key it is used as display field in the combobox, if there are several the one defined earlier is used
#) if no varchar field is present any char field is used
#) if no varchar or char fields are available the pk field is used for display
#) table inheritance is not covered
#) if a table's pk is a fk to another table's pk the other table's mask is shown in a second tab
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

from PyQt4 import QtCore

class DdTable(object):
    '''holds all information for a DB table relation'''
    def __init__(self,  oid = None,  schemaName = "None", tableName = "None",  comment = "",  title = None):
        self.oid = oid
        self.schemaName = QtCore.QString(schemaName)
        self.tableName = QtCore.QString(tableName)
        self.comment = QtCore.QString(comment)
        self.title = title

    def __str__(self):
        return "<ddattribute.DdTable %s.%s>" % (str(self.schemaName),  str(self.tableName))

class DdAttribute(object):
    '''abstract super class for all DdAttributes'''

    def __init__(self,  table,  type,  notNull,  name,  comment ,  label,  min = None,  max = None):
        self.table = table
        self.type = QtCore.QString(type)
        self.notNull = notNull
        self.name = QtCore.QString(name)
        self.comment = QtCore.QString(comment)
        self.label = label
        self.setMinMax(min,  max)

    def __str__(self):
        return "<ddattribute.DdAttribute %s>" % str(self.name)

    def isTypeInt(self):
        return (self.type == "int2") or (self.type == "int4") or (self.type == "int8")

    def isTypeFloat(self):
        return (self.type == "float4") or (self.type == "float8")

    def isTypeChar(self):
        return (self.type == "char") or (self.type == "varchar")

    def getLabel(self):
        if self.label:
            labelString = self.label
        else:
            labelString = self.name

        return labelString
        
    def setMinMax(self,  min,  max):
        self.min = None
        self.max = None
        
        if self.isTypeInt:
            if min != None:
                self.min = int(round(min))
            else:
                if self.type == "int2":
                    self.min = -32768
                elif self.type == "int4":
                    self.min = -2147483648
           
            if max != None:
                self.max = int(round(max))
            else:
                if self.type == "int2":
                    self.max = 32767
                elif self.type == "int4":
                    self.max = 2147483647
        elif self.isTypeFloat:
            if min != None:
                self.min = float(min)
            
            if max != None:
                self.max = float(max)
            
class DdLayerAttribute(DdAttribute):
    '''a DdAttribute for a field in a QGIS layer'''
    def __init__(self,  table,  type,  notNull,  name,  comment,  attNum,  isPK , isFK,  default,  hasDefault,  length,  label = None,  min = None,  max = None):
        DdAttribute.__init__(self,  table,  type,  notNull,  name,  comment,  label,  min,  max)
        self.isPK = isPK
        self.isFK = isFK
        self.default = default
        self.hasDefault = hasDefault
        self.length = length
        self.num = attNum # number of the attribute in the table pg_attribute.attNum

    def __str__(self):
        return "<ddattribute.DdLayerAttribute %s>" % str(self.name)

class DdFkLayerAttribute(DdLayerAttribute):
    '''a DdAttribute for field in a QGIS layer that represents a foreign key'''
    def __init__(self,  table,  type,  notNull,  name,  comment,  attNum,  isPK,  default ,  hasDefault,  queryForCbx,  label = None):
        DdLayerAttribute.__init__(self,  table,  type,  notNull,  name,  comment,  attNum,  isPK,  True,  default,  hasDefault,  -1,  label)
        self.queryForCbx = QtCore.QString(queryForCbx)

    def __str__(self):
        return "<ddattribute.DdFkLayerAttribute %s>" % str(self.name)

class DdTableAttribute(DdAttribute):
    '''a DdAttribute for a relationTable'''
    def __init__(self,  relationTable, comment ,  label,   \
                 relationFeatureIdField,  attributes,  maxRows,  showParents):
        DdAttribute.__init__(self,  relationTable,  "table",  False,  relationTable.tableName,  comment,  label)
        self.relationFeatureIdField = relationFeatureIdField
        self.attributes = attributes # an array with DdAttributes

        for anAtt in self.attributes:

            #if relationTable.tableName == "auslegungsStartDatum":
                #QtGui.QMessageBox.information(None, "",  anAtt.name + " " + self.relationFeatureIdField)
            if anAtt.name == self.relationFeatureIdField:
                self.attributes.remove(anAtt)
                break

        self.maxRows = maxRows
        self.showParents = showParents
        # init statements
        self.setSubsetString()

    def buildSubsetString(self,  relationFeatureIdField):
        ''''''
        subsetString = QtCore.QString("\"").append(relationFeatureIdField).append("\" = ")
        return subsetString

    def setSubsetString(self,  subsetString = None):
        if not subsetString:
            subsetString = self.buildSubsetString(self.relationFeatureIdField)

        self.subsetString = subsetString


class DdN2mAttribute(DdAttribute):
    '''a DdAttribute for a n2m relation, subtype can be list, tree or table
    relationTable and relatedTable are DdTable objects'''
    def __init__(self,  relationTable,  relatedTable,  subType,  comment ,  label,   \
                 relationFeatureIdField, relationRelatedIdField,  relatedIdField,  relatedDisplayField,  fieldList = []):
        DdAttribute.__init__(self,  relationTable,  "n2m",  False,  relationTable.tableName,  comment,  label)
        self.subType = QtCore.QString(subType)
        self.relatedTable = relatedTable
        self.relationFeatureIdField = relationFeatureIdField
        self.relationRelatedIdField = relationRelatedIdField
        self.relatedIdField = relatedIdField
        self.relatedDisplayField = relatedDisplayField
        self.fieldList = fieldList # an array with fields names
        # init statements
        self.setDisplayStatement()
        self.setInsertStatement()
        self.setDeleteStatement()


    def __str__(self):
        return "<ddattribute.DdN2mAttribute %s>" % str(self.name)

    def buildDisplayStatement(self,  relationSchema,  relationTable, relatedSchema,  relatedTable,  relationFeatureIdField, \
                              relatedIdField,  relatedDisplayField,  relationRelatedIdField,  fieldList):

        displayStatement = QtCore.QString("SELECT disp.\"").append(relatedIdField).append("\", disp.\"").append(relatedDisplayField).append("\",")
        displayStatement.append(" CASE COALESCE(lnk.\"").append(relationFeatureIdField).append("\", 0) WHEN 0 THEN 0 ELSE 2 END as checked")

        # for "list"  this is how it is supposed to look like
        #SELECT disp."id", disp."eigenschaft", CASE COALESCE(lnk."polygon_gid", 0) WHEN 0 THEN 0 ELSE 2 END as checked
        #FROM "alchemy"."eigenschaft" disp
        #LEFT JOIN (SELECT * FROM "alchemy"."polygon_has_eigenschaft" WHERE "polygon_gid" = :featureId) lnk ON disp."id" = lnk."eigenschaft_id"
        #ORDER BY disp."eigenschaft"

        if self.subType ==  QtCore.QString("tree"):
            for aField in fieldList:
                displayStatement.append(", \'").append(aField).append(": \' || COALESCE(disp.\"").append(aField).append("\", \'NULL\')")

        displayStatement.append(" FROM \"").append(relatedSchema).append("\".\"").append(relatedTable).append("\" disp")
        displayStatement.append(" LEFT JOIN (SELECT * FROM \"").append(relationSchema).append("\".\"").append(relationTable).append("\"")
        displayStatement.append(" WHERE \"").append(relationFeatureIdField).append("\" = :featureId) lnk")
        displayStatement.append(" ON disp.\"").append(relatedIdField).append("\" = lnk.\"") .append(relationRelatedIdField).append("\"")
        displayStatement.append( " ORDER BY checked DESC, disp.\"").append(relatedDisplayField).append("\"")

        return displayStatement

    def buildInsertStatement(self,  relationSchema,  relationTable,  relationFeatureIdField,  relationRelatedIdField,  fieldList):
        # INSERT INTO "alchemy"."polygon_has_eigenschaft"("polygon_gid", "eigenschaft_id") VALUES (:featureId, :itemId)
        insertStatement = QtCore.QString("INSERT INTO \"").append(relationSchema).append("\".\"").append(relationTable).append("\"")
        insertStatement.append("(\"").append(relationFeatureIdField).append("\", \"").append(relationRelatedIdField).append("\")")
        insertStatement.append(" VALUES (:featureId, :itemId)")

        return insertStatement

    def buildDeleteStatement(self,  relationSchema,  relationTable, relationFeatureIdField):
        # DELETE FROM "alchemy"."polygon_has_eigenschaft" WHERE "polygon_gid" = :featureId
        deleteStatement = QtCore.QString("DELETE FROM \"").append(relationSchema).append("\".\"").append(relationTable).append("\"")
        deleteStatement.append(" WHERE \"").append(relationFeatureIdField).append("\" = :featureId")

        return deleteStatement

    def setDisplayStatement(self,  displayStatement = None):
        if not displayStatement:
            displayStatement = self.buildDisplayStatement(self.table.schemaName,  self.table.tableName, self.relatedTable.schemaName,  \
                                                          self.relatedTable.tableName, self.relationFeatureIdField, self.relatedIdField,  self.relatedDisplayField,  \
                                                          self.relationRelatedIdField,  self.fieldList)

        self.displayStatement = displayStatement

    def setInsertStatement(self,  insertStatement = None):
        if not insertStatement:
            insertStatement = self.buildInsertStatement(self.table.schemaName,  self.table.tableName, self.relationFeatureIdField, self.relationRelatedIdField,  self.fieldList)

        self.insertStatement = insertStatement

    def setDeleteStatement(self,  deleteStatement = None):
        if not deleteStatement:
            deleteStatement = self.buildDeleteStatement(self.table.schemaName,  self.table.tableName, self.relationFeatureIdField)

        self.deleteStatement = deleteStatement

class DdPushButtonAttribute(DdAttribute):
    '''a DdAttribute that draws a pushButton in the mask. 
    the button must be implemented as subclass of ddui.DdPushButton'''
    def __init__(self,  comment ,  label):
        DdAttribute.__init__(self,  None,  "pushButton",  False,  "",  comment,  label)
        pass

    def __str__(self):
        return "<ddattribute.DdPushButtonAttribute %s>" % str(self.name)
