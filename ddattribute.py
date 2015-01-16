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
from PyQt4 import QtGui, QtCore

class DdTable(object):
    '''holds all information for a DB table relation'''
    def __init__(self, oid = None, schemaName = "None", tableName = "None", comment = "", title = None):
        self.oid = oid
        self.schemaName = schemaName
        self.tableName = tableName
        self.comment = comment
        self.title = title

    def __str__(self):
        return "<ddattribute.DdTable %s.%s>" % (self.schemaName, self.tableName)

class DdAttribute(object):
    '''abstract super class for all DdAttributes'''

    def __init__(self, table, type, notNull, name, comment , label,
            min = None, max = None, enableWidget = True):
        self.table = table
        self.type = type
        self.notNull = notNull
        self.name = name
        self.comment = comment
        self.label = label
        self.setMinMax(min, max)
        self.enableWidget = enableWidget

    def __str__(self):
        return "<ddattribute.DdAttribute %s>" % self.name

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

    def setMinMax(self, min, max):
        self.min = None
        self.max = None

        if self.isTypeInt:
            if min != None:
                try:
                    self.min = int(round(float(min)))
                except:
                    self.min = None
            else:
                if self.type == "int2":
                    self.min = -32768
                elif self.type == "int4":
                    self.min = -2147483648
                elif self.type == "int8":
                    self.min = -9223372036854775808

            if max != None:
                try:
                    self.max = int(round(float(max)))
                except:
                    self.max = None
            else:
                if self.type == "int2":
                    self.max = 32767
                elif self.type == "int4":
                    self.max = 2147483647
                elif self.type == "int8":
                    self.max = 9223372036854775807
        elif self.isTypeFloat:
            if min != None:
                try:
                    self.min = float(min)
                except:
                    self.min = None

            if max != None:
                try:
                    self.max = float(max)
                except:
                    self.max = None

    def debug(self, msg):
        QtGui.QMessageBox.information(None, "Debug", msg)

class DdLayerAttribute(DdAttribute):
    '''a DdAttribute for a field in a QGIS layer'''
    def __init__(self, table, type, notNull, name, comment, attNum, isPK, isFK,
            default, hasDefault, length, label = None, min = None, max = None,
            enableWidget = True, isArray = False, arrayDelim = ""):
        DdAttribute.__init__(self, table, type, notNull, name, comment,
            label, min, max, enableWidget)
        self.isPK = isPK
        self.isFK = isFK
        self.default = default
        self.hasDefault = hasDefault
        self.length = length
        self.num = attNum # number of the attribute in the table pg_attribute.attNum
        self.isArray = isArray
        self.arrayDelim = arrayDelim

    def __str__(self):
        return "<ddattribute.DdLayerAttribute %s>" % self.name

class DdDateLayerAttribute(DdLayerAttribute):
    '''a DdAttribute for a date field in a QGIS layer
    if you want to specify today as min or max, simply pass "today"'''
    def __init__(self, table, type, notNull, name, comment, attNum, isPK,
            isFK, default, hasDefault, length, label = None, min = None,
            max = None, dateFormat = "yyyy-MM-dd", enableWidget = True,
            isArray = False, arrayDelim = ""):
        self.dateFormat = dateFormat # set here because DdAttribute calls setMinMax on __init__
        DdLayerAttribute.__init__(self, table, type, notNull, name,
            comment, attNum, isPK, isFK, default, hasDefault, length,
            label, min, max, enableWidget, isArray, arrayDelim)

    def __str__(self):
        return "<ddattribute.DdDateLayerAttribute %s>" % self.name

    def setMinMax(self, min, max):
        '''reimplemented from DdAttribute'''
        self.min = self.formatDate(min)
        self.max = self.formatDate(max)

    def formatDate(self, thisDate):
        '''thisDate may be either a QDate or a string'''
        if thisDate != None:
            if not isinstance(thisDate, QtCore.QDate):
                # we assume a string
                if thisDate.find("today") != -1:
                    if thisDate.find("-") != -1:
                        factor = -1
                        daysToAdd = thisDate.split("-")[1].strip()
                    else:
                        factor = 1

                        if thisDate.find("+") != -1:
                            daysToAdd = thisDate.split("+")[1].strip()
                        else:
                            daysToAdd = "0"

                    returnDate = QtCore.QDate.currentDate().addDays(int(daysToAdd) * factor)
                else:
                    returnDate = QtCore.QDate.fromString(thisDate, self.dateFormat)
                    # returns a null date if string is not formatted as needed by dateFormat

            if returnDate.isNull():
                returnDate = None
        else:
            returnDate = None

        return returnDate

class DdFkLayerAttribute(DdLayerAttribute):
    '''a DdAttribute for field in a QGIS layer that represents a foreign key'''
    def __init__(self, table, type, notNull, name, comment, attNum, isPK,
            default , hasDefault, queryForCbx, label = None, enableWidget = True):
        DdLayerAttribute.__init__(self, table, type, notNull, name, comment,
            attNum, isPK, True, default, hasDefault, -1, label,
            enableWidget = enableWidget)
        self.queryForCbx = queryForCbx

    def __str__(self):
        return "<ddattribute.DdFkLayerAttribute %s>" % self.name


class DdManyToManyAttribute(DdAttribute):
    '''abstract class for any many2many attribute'''
    def __init__(self, relationTable, type, relationFeatureIdField,
            comment, label, enableWidget = True):
        DdAttribute.__init__(self, relationTable, type, False,
            relationTable.tableName, comment, label, enableWidget = enableWidget)

        self.relationFeatureIdField = relationFeatureIdField
        self.setSubsetString()

    def buildSubsetString(self, relationFeatureIdField):
        '''builld the subset string to be applied as filter on the layer'''
        subsetString = "\"" + relationFeatureIdField + "\" = "
        return subsetString

    def setSubsetString(self, subsetString = None):
        if not subsetString:
            subsetString = self.buildSubsetString(self.relationFeatureIdField)

        self.subsetString = subsetString

class DdTableAttribute(DdManyToManyAttribute):
    '''a DdAttribute for a relationTable'''
    def __init__(self, relationTable, comment, label, relationFeatureIdField,
            attributes, maxRows, showParents, pkAttName, enableWidget = True):
        DdManyToManyAttribute.__init__(self, relationTable, "table",
            relationFeatureIdField, comment, label, enableWidget)

        self.attributes = attributes # an array with DdAttributes
        self.pkAttName = pkAttName

        for anAtt in self.attributes:

            #if relationTable.tableName == "auslegungsStartDatum":
                #QtGui.QMessageBox.information(None, "", anAtt.name + " " + self.relationFeatureIdField)
            if anAtt.name == self.relationFeatureIdField:
                self.attributes.remove(anAtt)
                break

        self.maxRows = maxRows
        self.showParents = showParents

class DdN2mAttribute(DdManyToManyAttribute):
    '''a DdAttribute for a n2m relation, subtype can be list or tree
    relationTable and relatedTable are DdTable objects'''
    def __init__(self, relationTable, relatedTable, subType, comment , label,
            relationFeatureIdField, relationRelatedIdField, relatedIdField,
            relatedDisplayField, fieldList = [], relatedForeignKeys = [],
            enableWidget = True):
        DdManyToManyAttribute.__init__(self, relationTable, "n2m",
            relationFeatureIdField, comment, label, enableWidget)

        self.subType = subType
        self.relatedTable = relatedTable
        self.relationRelatedIdField = relationRelatedIdField
        self.relatedIdField = relatedIdField
        self.relatedDisplayField = relatedDisplayField
        self.fieldList = fieldList # an array with fields names
        self.relatedForeignKeys = relatedForeignKeys
        # init statements
        self.setDisplayStatement()
        self.setInsertStatement()
        self.setDeleteStatement()

    def __str__(self):
        return "<ddattribute.DdN2mAttribute %s>" % str(self.name)

    def buildDisplayStatement(self, relationSchema, relationTable, relatedSchema, relatedTable, relationFeatureIdField, \
                              relatedIdField, relatedDisplayField, relationRelatedIdField, fieldList):

        displayStatement ="SELECT disp.\"" + relatedIdField + "\", disp.\"" + relatedDisplayField + "\","
        displayStatement += " CASE COALESCE(lnk.\"" + relationFeatureIdField + "\", 0) WHEN 0 THEN 0 ELSE 2 END as checked"

        # for "list"  this is how it is supposed to look like
        #SELECT disp."id", disp."eigenschaft", CASE COALESCE(lnk."polygon_gid", 0) WHEN 0 THEN 0 ELSE 2 END as checked
        #FROM "alchemy"."eigenschaft" disp
        #LEFT JOIN (SELECT * FROM "alchemy"."polygon_has_eigenschaft" WHERE "polygon_gid" = :featureId) lnk ON disp."id" = lnk."eigenschaft_id"
        #ORDER BY disp."eigenschaft"

        if self.subType ==  "tree":
            for aField in fieldList:
                if aField != relatedDisplayField: # no doubles
                    displayStatement += ", \'" + aField + ": \' || COALESCE(disp.\"" + aField + "\", \'NULL\')"

        if len(self.relatedForeignKeys) > 0:
            for anItem in self.relatedForeignKeys.iteritems():
                aKey = anItem[0]
                aValue = anItem[1]
                displayFieldName = aValue[2]
                self.fieldList.append("fk_" + aKey + ".value")
                displayStatement += ", \'" + displayFieldName + ": \' || fk_" + aKey + ".value"

        displayStatement += " FROM \"" + relatedSchema + "\".\"" + relatedTable + "\" disp"

        if self.enableWidget:
            displayStatement += " LEFT"

        displayStatement += " JOIN (SELECT * FROM \"" + relationSchema + "\".\"" + relationTable + "\""
        displayStatement += " WHERE \"" + relationFeatureIdField + "\" = :featureId) lnk"
        displayStatement += " ON disp.\"" + relatedIdField + "\" = lnk.\"" + relationRelatedIdField + "\""

        if len(self.relatedForeignKeys) > 0:
            for anItem in self.relatedForeignKeys.iteritems():
                aKey = anItem[0]
                aValue = anItem[1]
                fkSelectStatement = aValue[1]
                #example: SELECT my_string as value, id as key FROM my_schema.my_lookup_table;
                fkSelectStatement = fkSelectStatement[: len(fkSelectStatement) -1] # get rid of ;
                displayStatement += " LEFT JOIN (" + fkSelectStatement + ") fk_" + aKey + " ON disp.\""  + aKey + "\" = fk_" + aKey + ".key"

        displayStatement +=  " ORDER BY checked DESC, disp.\"" + relatedDisplayField + "\" NULLS LAST"
        #QtGui.QMessageBox.information(None, "displayStatement", displayStatement)
        return displayStatement

    def buildInsertStatement(self, relationSchema, relationTable, relationFeatureIdField, relationRelatedIdField, fieldList):
        # INSERT INTO "alchemy"."polygon_has_eigenschaft"("polygon_gid", "eigenschaft_id") VALUES (:featureId, :itemId)
        insertStatement = "INSERT INTO \"" + relationSchema + "\".\"" + relationTable + "\""
        insertStatement += "(\"" + relationFeatureIdField + "\", \"" + relationRelatedIdField + "\")"
        insertStatement += " VALUES (:featureId, :itemId)"

        return insertStatement

    def buildDeleteStatement(self, relationSchema, relationTable, relationFeatureIdField):
        # DELETE FROM "alchemy"."polygon_has_eigenschaft" WHERE "polygon_gid" = :featureId
        deleteStatement = "DELETE FROM \"" + relationSchema + "\".\"" + relationTable + "\""
        deleteStatement += " WHERE \"" + relationFeatureIdField + "\" = :featureId"

        return deleteStatement

    def setDisplayStatement(self, displayStatement = None):
        if not displayStatement:
            displayStatement = self.buildDisplayStatement(self.table.schemaName, self.table.tableName, self.relatedTable.schemaName, \
                                                          self.relatedTable.tableName, self.relationFeatureIdField, self.relatedIdField, self.relatedDisplayField, \
                                                          self.relationRelatedIdField, self.fieldList)

        self.displayStatement = displayStatement

    def setInsertStatement(self, insertStatement = None):
        if not insertStatement:
            insertStatement = self.buildInsertStatement(self.table.schemaName, self.table.tableName, self.relationFeatureIdField, self.relationRelatedIdField, self.fieldList)

        self.insertStatement = insertStatement

    def setDeleteStatement(self, deleteStatement = None):
        if not deleteStatement:
            deleteStatement = self.buildDeleteStatement(self.table.schemaName, self.table.tableName, self.relationFeatureIdField)

        self.deleteStatement = deleteStatement

class DdPushButtonAttribute(DdAttribute):
    '''a DdAttribute that draws a pushButton in the mask.
    the button must be implemented as subclass of dduserclass.DdPushButton'''
    def __init__(self, comment , label, enableWidget = True):
        DdAttribute.__init__(self, None, "pushButton", False, "", comment,
            label, enableWidget = enableWidget)
        pass

    def __str__(self):
        return "<ddattribute.DdPushButtonAttribute %s>" % self.name

class DdCheckableTableAttribute(DdN2mAttribute, DdTableAttribute):
    def __init__(self, relationTable, relatedTable, comment, label,
            relationFeatureIdField, relationRelatedIdField,
            relatedIdField, relatedDisplayField, attributes,
            catalogTable = None, relatedCatalogIdField = None,
            catalogIdField = None, catalogDisplayField = None,
            catalogLabel = None, enableWidget = True):
        DdN2mAttribute.__init__(self, relationTable, relatedTable,
            "default", comment, label, relationFeatureIdField,
            relationRelatedIdField, relatedIdField, relatedDisplayField,
            fieldList = [], relatedForeignKeys = [],
            enableWidget = enableWidget)
        DdTableAttribute.__init__(self, relationTable, comment, label,
            relationFeatureIdField, attributes, maxRows = None,
            showParents = False, pkAttName = None)

        self.type = "checkableTable"
        self.catalogTable = catalogTable
        self.relatedCatalogIdField = relatedCatalogIdField
        self.catalogIdField = catalogIdField
        self.catalogDisplayField = catalogDisplayField
        self.catalogLabel = catalogLabel

        if self.catalogLabel == None:
            self.catalogLabel = self.catalogDisplayField


    def __str__(self):
        return "<ddattribute.DdCheckableTableAttribute %s>" % str(self.name)

