-- Estado de la conversación en curso (una fila por chat de Telegram)
create table if not exists sessions (
    chat_id bigint primary key,
    state text not null default 'idle',
    data jsonb not null default '{}'::jsonb,
    updated_at timestamptz not null default now()
);

-- Historial de cotizaciones generadas
create table if not exists quotes (
    id uuid primary key default gen_random_uuid(),
    chat_id bigint not null,
    client jsonb not null,
    items jsonb not null,
    total numeric not null,
    created_at timestamptz not null default now()
);

create index if not exists quotes_chat_id_created_at_idx
    on quotes (chat_id, created_at desc);
