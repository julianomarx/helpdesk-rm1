-- Migration 003: adiciona qualitor_ticket_id à tabela notifications
-- Executar apenas se a coluna ainda não existir (MySQL < 8.0 não suporta ADD COLUMN IF NOT EXISTS)
-- Verificar antes: SELECT COUNT(*) FROM information_schema.COLUMNS WHERE TABLE_SCHEMA='<db>' AND TABLE_NAME='notifications' AND COLUMN_NAME='qualitor_ticket_id';

ALTER TABLE notifications ADD COLUMN qualitor_ticket_id INT NULL;
