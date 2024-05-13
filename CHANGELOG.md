# Change Log
All notable changes to this project since Version 1.0.0 will be documented in this file.

## [Unreleased](https://github.com/bstroebl/DataDrivenInputMask/compare/v2.5.0...develop)

## [2.5.0](https://github.com/bstroebl/DataDrivenInputMask/compare/v2.4.0...v2.5.0) - 2024-05-13
### Fixed
- catch orphan embedded layers
- add validation for big ints
- Initialize parent
- handle NULL value in doubleValidator properly

### Changed
- Update author and contact information
- Update to new api for creating the layer actio

## [2.4.0](https://github.com/bstroebl/DataDrivenInputMask/compare/v2.3.0...v2.4.0) - 2020-05-19
### Added
- Optionally use another icon than default for action
- Tool to get a feature for its PK value
- Double click on a top-level item in TreeWidget to show its mask
- Optionally use another icon than default for action

### Changed
- Show DB error if connection fails
- Use parameter to decide whether showing mask puts layer into editing mode

### Fixed
- initialize parent class correctly
- define bpchar as char type
- Remove slot decorator causing trouble in newer Qt
- adapt to new api
- Show marker for multipoint features
- Catch error if no feature exists
- do not set related table of TreeWidget editable
- Do not put related table of TreeWidget in editing mode when double clicking in search mode
- Fix query to also work with PostgreSQL 12
- use error text instead of object
- catch error if marker does not exist
- set filter even if layer is editable by stopping edit session before and restarting if after

## [2.3.0](https://github.com/bstroebl/DataDrivenInputMask/compare/v2.2.0...v2.3.0) - 2019-04-05
### Added
- Establish configurable filter option for values being displayed in DdN2mTableWidget and DdN2mTreeWidget
- New functions for layer group handling

### Fixed
- Fix field search in DdN2mCheckableTableWidget
- Properly load layer in Project
- Check if config tables need update at least once per session
- Replace calls to QGIS2 api with calls to QGIS3 api

## [2.2.0](https://github.com/bstroebl/DataDrivenInputMask/compare/v2.1.0...v2.2.0) - 2019-01-17
### Added
- Allow any expression as lookup field in combo, implements #21
- Show referencing field of 1:n realation in label, implements #20
- Establish configurable filter option for lookup tables (DdComboBox)

### Fixed
- Allow spaces in database name
- Replace outdated api calls fixes #15, #17
- Fix field descriptions of field_multiline and lookup_field
- Set table_action to true because default is not applied in db, fixes #18
- Properly create parent forms
- Add space in dialog title, fixes #22

## [2.1.0](https://github.com/bstroebl/DataDrivenInputMask/compare/v2.0.0...v2.1.0) - 2018-10-23

### Added
- Entries in DdN2mTableWidget can be copied, the DDIM of the copied feature is opened
- Configure, if a textBox or a textLine should be used for text or varchar fields, implements #8
- Make lookup field for combo box configurable, implements #10

### Fixed
- Replace calls to QGIS2 api with calls to QGIS3 api

## [2.0.0](https://github.com/bstroebl/DataDrivenInputMask/compare/v1.3.0...v2.0.0) - 2018-10-22

### Changed
- Upgraded to QGIS3
- Code for QGIS2.* resides in QGIS2 branch

## 1.3.4 - 2018-09-24

### Fixed
- Show search mask for n2mTable
- Show char (bpchar) fields in mask
- Manually move layer into DdGroup after loading. Automatic moving resulted in DDIM trying to init non-Postgres layers present in the project.

## 1.3.0 - 2017-09-01
### Added
- DdN2mTableWidget and DdN2mCheckableTableWidget retain user changed column widths upon reopening of the dialog
- Additional layers are loaded with the same ssl-mode as the base layer
- DdN2mCheckableTableWidget now displays foreign key lookup values instead of integers
- DdN2mCheckableTableWidget and DdN2mTableWidget display a translatable string for boolean values
- Plugin now works properly with bigint primary keys in QGIS > 2.14

### Changed
- Bug tracker has been moved to github
- Help files changed by new Sphinx version
- Code for DdN2mTableWidget has been modularized
- DdN2mCheckableTableWidget is now a child of DdN2mTableWidget
- All string conversion is handled by DdInputWidget

## 1.2.2 - 2016-05-12

### Fixed
- Sort items in DdN2mListWidget and DdN2mTreeWidget
- Expand DdN2mListWidget and DdN2mTreeWidget vertically by means of a QFrame (as in DdN2mTableWidget, but invisible)

## 1.2.1 - 2016-03-16

### Fixed
- Fix search, which did not return any results in QGIS 2.14+

## [1.2.0](https://github.com/bstroebl/DataDrivenInputMask/compare/v1.1.0...v1.2.0) - 2016-02-26
### Added
- api method *DdN2mWidget.initializeTableLayer*
- api method *DdN2mWidget.initialize*
- Filter items in ListWidget and TreeWidget to enable user to find his choice quickly
- Use the authentification system introduced in QGIS 2.12: Load additional layers with authCfgId if layer itself has been loaded this way

### Changed
- all n2m widgets are disabled in multi-edit mode
- api method *DdN2mWidget.initialize* must be called by all subclasses upon initialize
- new attribute authcfg for QtSql.QSqlDatabase instances created by DdManager

### Deprecated
 - api method *DdN2mWidget.initializeLayer*

### Fixed
- Fix runtime error in date and bool array widgets
- Show related table with additinoal field

## [1.1.0](https://github.com/bstroebl/DataDrivenInputMask/compare/v1.0.1...v1.1.0) - 2015-09-11
### Added
- DdManager: new api method *createDdTable* to create a DdTable from schema + relation
- multi edit mode: the same data for all selected features can be entered in one go; Input widgets can have more than two modes (until now only search and input)
Currently no multi-edit support for n2m tables
- run different instances of DdManager in the same application
- tooltip is shown at mouseover on labels, too
- new class *DdLineEditBoolean*, replaces *DdCheckBox*

### Changed
- DdN2mTableWidget: geometry field is not shown
- api-method *showFeatureForm* takes an optional additional parameter *multiEdit* (Boolean, defaults to False = without parameter method behaves as before))
- api-method *addAction* takes an optional additional parameter *ddManagerName* (defaults to ddmanager = without parameter method behaves as before)
- DdDialog: constructor takes an optional additional parameter *multiEdit* (Boolean, defaults to False = without parameter method behaves as before)
- DdWidget: initialize takes an optional additional parameter *mode* (integer, defaults to 0 = without parameter method behaves as before)
- display of area/length: label states that value is derived from GIS, display is suppressed if empty geometry
- Widget for boolean fields is a pair of radio buttons labeled with yes/no
- Input widgets are now properly resized when the dialog is resized by the user, NULL checkboxes align to the right

### Deprecated
- class *DdCheckBox*

### Fixed
- DdN2mTableWidget: handle runtime error if field cannot be found, reenable search
- DdN2mCheckableTableWidget: Handle feature only if in edit mode and improve readability of the code
- code leading to warnings chagned

## 1.0.1 - 2015-04-21
### Added
- New userclass *DdRelatedComboBox*: A ComboBox that is refreshed when another ComboBox has
    a currentIndexChanged event, i.e. the user chooses another value.
- DdManager: new api-method *addFormWidget* to manually add a form to an UI

### Changed
- Return area/length at getValue
- enable tableWidget of n2mTable even if attribute is disabled
- all error messages are faded out after 10 seconds, error message for non suitable layer is only displayed in log
- Search dialog: widget is activated with double click on search-operator combo box, too
- DdN2mTableWidget and DdN2mCheckableTableWidget are sortable by numbers and dates

### Fixed
- DdN2mCheckableTableWidget: values in table are represented with localized string
- DdN2mTableWidget: field names with upper-case letters work properly, search for null foreign keys fixed
- Search dialog: widget is activated with double click even if it is not enabled in edit mode

## 1.0.0 - 2015-02-17
### Added
- Support array fields
- Show area/length of polygon/line features in mask

### Changed
- Show last catalog used when reopening a DdN2mCheckableTableWidget

### Fixed
- DB-Password containing `=` works can be used
- DdManager: api-Function addInputWidget works correctly even if dialog contains only one DdFormWidget
- DdManager: api function removeAction fixed
- Do not uncheck null on double click if widget is not enabled


