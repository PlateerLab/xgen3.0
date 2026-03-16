#!/bin/bash
# pg_hba.conf를 md5로 강제 변경
sed -i 's/scram-sha-256/md5/g' "$PGDATA/pg_hba.conf"
sed -i 's/host all all all md5/host all all all md5/' "$PGDATA/pg_hba.conf"

# 비밀번호를 md5로 재설정
psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SET password_encryption = 'md5'; ALTER USER $POSTGRES_USER WITH PASSWORD '$POSTGRES_PASSWORD';"
