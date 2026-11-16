#!/bin/sh
# CorePulse · Inicializa la base de datos web en el contenedor de PostgreSQL.
# Lo ejecuta la imagen oficial de PostgreSQL la primera vez que se crea el volumen
# (carpeta /docker-entrypoint-initdb.d). Aplica el script de base local y luego
# las migraciones en orden de fecha. Si un script falla, la inicialización se detiene.
set -e

carpeta=/corepulse/supabase

echo "CorePulse: aplicando base local"
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
  -f "$carpeta/00000000000000_base_local.sql"

for archivo in $(ls "$carpeta/migraciones/"*.sql | sort); do
  echo "CorePulse: aplicando $(basename "$archivo")"
  psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" -f "$archivo"
done

echo "CorePulse: base de datos lista"
