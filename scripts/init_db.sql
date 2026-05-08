-- Inicialização do banco JusBot
-- Script executado automaticamente na primeira inicialização do PostgreSQL

-- Extensão vector: necessária para indexar e buscar embeddings de alta dimensão
-- Usada na Camada 1 (Ingestão) e Camada 3 (RAG) para armazenar embeddings do corpus jurídico
CREATE EXTENSION IF NOT EXISTS vector;

-- Extensão pg_trgm: suporte para busca lexical trigram (substring matching)
-- Usada na Camada 3 (RAG) para busca BM25 e full-text search em trechos jurídicos
CREATE EXTENSION IF NOT EXISTS pg_trgm;
