#!/bin/bash
docker cp schema.sql gmao-postgres:/schema.sql
docker cp seed.sql gmao-postgres:/seed.sql
docker exec -i gmao-postgres psql -U gmao_user -d gmao_db -f /schema.sql
docker exec -i gmao-postgres psql -U gmao_user -d gmao_db -f /seed.sql
echo "✅ Base de données initialisée !"