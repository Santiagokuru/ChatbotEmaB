-- Numeración autoincremental de presupuestos (para mostrar N° en el PDF)
alter table quotes
    add column if not exists quote_number bigserial;
