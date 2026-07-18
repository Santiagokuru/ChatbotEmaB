-- Tiempo estimado de realización del trabajo, cargado por el cliente en el chat
alter table quotes
    add column if not exists estimated_time text not null default '';
