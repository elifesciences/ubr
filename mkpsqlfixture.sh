#!/bin/bash
pg_dump -U root _ubr_testdb --clean --if-exists --no-owner --no-password | gzip > ubr/tests/fixtures/psql_ubr_testdb.psql.gz
