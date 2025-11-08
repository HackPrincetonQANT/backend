-- =====================================================================
-- File: snowflake/00_roles_wh_db.sql
-- Purpose: Create role, warehouse, database, schema, and grants
-- Run as: ACCOUNTADMIN (or equivalent admin role)
-- =====================================================================

-- 0) Safety: create role (idempotent) and grant it to SYSADMIN for visibility
CREATE ROLE IF NOT EXISTS BALANCEIQ_ROLE;
GRANT ROLE BALANCEIQ_ROLE TO ROLE SYSADMIN;

-- 1) Create a small, auto-resuming warehouse for dev
CREATE WAREHOUSE IF NOT EXISTS BALANCEIQ_WH
  WAREHOUSE_SIZE      = 'XSMALL'
  AUTO_SUSPEND        = 60
  AUTO_RESUME         = TRUE
  INITIALLY_SUSPENDED = TRUE
  COMMENT             = 'BalanceIQ dev warehouse';

-- Allow the app role to use the warehouse
GRANT USAGE ON WAREHOUSE BALANCEIQ_WH TO ROLE BALANCEIQ_ROLE;

-- 2) Create database and schema
CREATE DATABASE IF NOT EXISTS BALANCEIQ_DB
  COMMENT = 'BalanceIQ main database';

CREATE SCHEMA IF NOT EXISTS BALANCEIQ_DB.CORE
  COMMENT = 'Core tables, views, UDFs';

-- 3) Basic privileges for the app role
GRANT USAGE ON DATABASE BALANCEIQ_DB           TO ROLE BALANCEIQ_ROLE;
GRANT USAGE ON SCHEMA   BALANCEIQ_DB.CORE      TO ROLE BALANCEIQ_ROLE;

-- Object creation privileges in CORE schema
GRANT CREATE TABLE      ON SCHEMA BALANCEIQ_DB.CORE TO ROLE BALANCEIQ_ROLE;
GRANT CREATE VIEW       ON SCHEMA BALANCEIQ_DB.CORE TO ROLE BALANCEIQ_ROLE;
GRANT CREATE FUNCTION   ON SCHEMA BALANCEIQ_DB.CORE TO ROLE BALANCEIQ_ROLE;
GRANT CREATE PROCEDURE  ON SCHEMA BALANCEIQ_DB.CORE TO ROLE BALANCEIQ_ROLE;
GRANT CREATE STAGE      ON SCHEMA BALANCEIQ_DB.CORE TO ROLE BALANCEIQ_ROLE;
GRANT CREATE SEQUENCE   ON SCHEMA BALANCEIQ_DB.CORE TO ROLE BALANCEIQ_ROLE;
GRANT CREATE FILE FORMAT ON SCHEMA BALANCEIQ_DB.CORE TO ROLE BALANCEIQ_ROLE;

-- (Optional but recommended) Future grants so new objects are selectable by the role
GRANT SELECT           ON FUTURE TABLES IN SCHEMA BALANCEIQ_DB.CORE TO ROLE BALANCEIQ_ROLE;
GRANT SELECT           ON FUTURE VIEWS  IN SCHEMA BALANCEIQ_DB.CORE TO ROLE BALANCEIQ_ROLE;
GRANT USAGE, READ, WRITE ON FUTURE STAGES IN SCHEMA BALANCEIQ_DB.CORE TO ROLE BALANCEIQ_ROLE;

-- 4) (Optional) Create a dedicated application user and grant the role
-- NOTE: Set your own strong password & network policy as needed.
-- CREATE USER IF NOT EXISTS BIQ_APP
--   PASSWORD='REPLACE_ME_Strong_Pwd_#2025'
--   DEFAULT_ROLE        = BALANCEIQ_ROLE
--   DEFAULT_WAREHOUSE   = BALANCEIQ_WH
--   DEFAULT_NAMESPACE   = BALANCEIQ_DB.CORE
--   MUST_CHANGE_PASSWORD = FALSE
--   COMMENT = 'BalanceIQ application user';
-- GRANT ROLE BALANCEIQ_ROLE TO USER BIQ_APP;

-- 5) Set execution context for subsequent scripts
USE ROLE BALANCEIQ_ROLE;
USE WAREHOUSE BALANCEIQ_WH;
USE DATABASE BALANCEIQ_DB;
USE SCHEMA CORE;

-- =====================================================================
-- Verification (run these after the script)
-- =====================================================================
-- SHOW WAREHOUSES LIKE 'BALANCEIQ_WH';
-- SHOW ROLES LIKE 'BALANCEIQ_ROLE';
-- SHOW SCHEMAS LIKE 'CORE' IN DATABASE BALANCEIQ_DB;