-- Creates the test database used by pytest
SELECT 'CREATE DATABASE quila_test_db'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'quila_test_db')\gexec
