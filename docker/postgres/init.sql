-- ============================================================
-- SafraLog — PostgreSQL Init
-- Executado automaticamente na primeira criação do container.
-- ============================================================

-- Extensões necessárias
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";   -- UUID nativo
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements"; -- Análise de queries
CREATE EXTENSION IF NOT EXISTS "unaccent";    -- Busca sem acentos

-- Configurações de performance para ambiente de desenvolvimento
-- (produção: ajustar via postgresql.conf ou variáveis de ambiente)
ALTER SYSTEM SET shared_preload_libraries = 'pg_stat_statements';
ALTER SYSTEM SET track_activity_query_size = 2048;

-- Collation pt-BR para ordenação correta de strings em português
-- Disponível em PostgreSQL 15+
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_collation WHERE collname = 'pt_BR') THEN
    CREATE COLLATION pt_BR (provider = icu, locale = 'pt-BR');
  END IF;
EXCEPTION
  WHEN OTHERS THEN
    NULL; -- Ignora se não suportado
END
$$;

-- Garante que o banco usa UTF-8
UPDATE pg_database SET datcollate = 'pt_BR.UTF-8', datctype = 'pt_BR.UTF-8'
WHERE datname = current_database()
  AND datcollate != 'pt_BR.UTF-8';

COMMIT;
