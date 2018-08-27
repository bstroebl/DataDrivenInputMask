

-- -----------------------------------------------------
-- Table \"public\".\"dd_table\"
-- -----------------------------------------------------
CREATE TABLE  \"public\".\"dd_table\" (
  \"id\" SERIAL NOT NULL,
  \"table_catalog\" VARCHAR(256) NULL,
  \"table_schema\" VARCHAR(256) NOT NULL,
  \"table_name\" VARCHAR(256) NOT NULL,
  \"table_help\" TEXT NULL,
  \"with_action\" BOOLEAN NOT NULL DEFAULT \'t\',
  PRIMARY KEY (\"id\"));

COMMENT ON TABLE \"public\".\"dd_table\" IS \'DataDrivenInputMask: contains tables with a configuration for the mask, no need to input tables for which the default data-driven mask is to be shown\';
COMMENT ON COLUMN \"public\".\"dd_table\".\"table_catalog\" IS \'name of the database\';
COMMENT ON COLUMN \"public\".\"dd_table\".\"table_schema\" IS \'name of the schema\';
COMMENT ON COLUMN \"public\".\"dd_table\".\"table_name\" IS \'name of the table\';
COMMENT ON COLUMN \"public\".\"dd_table\".\"table_help\" IS \'Help string to be shown if user clicks the help button, this string can be HTML formatted.\';
COMMENT ON COLUMN \"public\".\"dd_table\".\"with_action\" IS \'Create a layer action to show the mask\';

-- -----------------------------------------------------
-- Table \"public\".\"dd_tab\"
-- -----------------------------------------------------
CREATE TABLE  \"public\".\"dd_tab\" (
  \"id\" SERIAL NOT NULL,
  \"dd_table_id\" INTEGER NOT NULL,
  \"tab_alias\" VARCHAR(256) NULL,
  \"tab_order\" INTEGER NOT NULL DEFAULT 0,
  \"tab_tooltip\" VARCHAR(256) NULL,
  PRIMARY KEY (\"id\"),
  CONSTRAINT \"fk_dd_tab_dd_table\"
    FOREIGN KEY (\"dd_table_id\")
    REFERENCES \"public\".\"dd_table\" (\"id\")
    ON DELETE CASCADE
    ON UPDATE CASCADE);

CREATE INDEX \"idx_fk_dd_tab_dd_table_idx\" ON \"public\".\"dd_tab\" (\"dd_table_id\");
COMMENT ON TABLE \"public\".\"dd_tab\" IS \'DataDrivenInputMask: contains tabs for tables\';
COMMENT ON COLUMN \"public\".\"dd_tab\".\"dd_table_id\" IS \'Table for wich this tab is used\';
COMMENT ON COLUMN \"public\".\"dd_tab\".\"tab_alias\" IS \'Label the tab with this string, leave empty if you want the data-driven tabs\';
COMMENT ON COLUMN \"public\".\"dd_tab\".\"tab_order\" IS \'Order of the tabs in the mask (if a tab contains more than one mask)\';
COMMENT ON COLUMN \"public\".\"dd_tab\".\"tab_tooltip\" IS \'tooltip to be shown for this tab\';

-- -----------------------------------------------------
-- Table \"public\".\"dd_field\"
-- -----------------------------------------------------
CREATE TABLE  \"public\".\"dd_field\" (
  \"id\" SERIAL NOT NULL,
  \"dd_tab_id\" INTEGER NOT NULL,
  \"field_name\" VARCHAR(256) NOT NULL,
  \"field_alias\" VARCHAR(256) NULL,
  \"field_skip\" BOOLEAN NOT NULL DEFAULT \'f\',
  \"field_order\" INTEGER NULL,
  \"field_min\" FLOAT NULL,
  \"field_max\" FLOAT NULL,
  PRIMARY KEY (\"id\"),
  CONSTRAINT \"fk_dd_field_dd_tab\"
    FOREIGN KEY (\"dd_tab_id\")
    REFERENCES \"public\".\"dd_tab\" (\"id\")
    ON DELETE CASCADE
    ON UPDATE CASCADE);

CREATE INDEX \"idx_fk_dd_field_dd_tab_idx\" ON \"public\".\"dd_field\" (\"dd_tab_id\");
COMMENT ON TABLE  \"public\".\"dd_field\" IS \'DataDrivenInputMask: the data-driven mask for fields can be configured here.\';
COMMENT ON COLUMN  \"public\".\"dd_field\".\"dd_tab_id\" IS \'All fields not included here will be put in the tab with the highest tab_order. One and the same field should be included in _one_ tab only.\';
COMMENT ON COLUMN  \"public\".\"dd_field\".\"field_name\" IS \'Name of the field in the database\';
COMMENT ON COLUMN  \"public\".\"dd_field\".\"field_alias\" IS \'Alias of the field in the mask\';
COMMENT ON COLUMN  \"public\".\"dd_field\".\"field_skip\" IS \'skip this field in the mask, i.e. hide it from the user\';
COMMENT ON COLUMN  \"public\".\"dd_field\".\"field_order\" IS \'order of the fields in the mask\';
COMMENT ON COLUMN  \"public\".\"dd_field\".\"field_min\" IS \'min value of the field (only for numeric fields)\';
COMMENT ON COLUMN  \"public\".\"dd_field\".\"field_max\" IS \'max value of the field (only for numeric fields)\';
