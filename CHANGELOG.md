# Change Log
All notable changes to this project since Version 1.0.0 will be documented in this file.

## [Unreleased](https://github.com/bstroebl/DataDrivenInputMask/compare/v1.1.0...HEAD)
### Added
- api method *DdN2mWidget.initializeTableLayer*
- api method *DdN2mWidget.initialize*

### Changed
- all n2m widgets are disabled in multi-edit mode
- api method *DdN2mWidget.initialize* must be called by all subclasses upon initialize

### Deprecated
 - api method *DdN2mWidget.initializeLayer*

### Fixed

## 1.1.0 - 2015-09-11
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


