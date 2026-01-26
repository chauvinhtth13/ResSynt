-- ============================================
-- ResSynt Database Initialization Script
-- ============================================
-- This script runs only on first PostgreSQL container start
-- Creates the management schema in db_management

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================
-- Create Schemas for Management Database
-- ============================================
CREATE SCHEMA IF NOT EXISTS management;

-- ============================================
-- Grant Permissions
-- ============================================
GRANT ALL PRIVILEGES ON SCHEMA management TO ressynt_admin;

-- Note: Study databases will be created via a separate shell script
-- because CREATE DATABASE cannot run inside a transaction block
