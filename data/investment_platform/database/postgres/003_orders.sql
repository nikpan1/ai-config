create table order_record (
    order_ref text primary key,
    account_ref text not null,
    instrument_id text not null,
    amount numeric(18,2) not null check (amount > 0),
    currency text not null check (currency in ('PLN','EUR','USD')),
    state text not null check (state in ('NEW','RESERVED','PLACED','SETTLED','REJECTED','FAILED')),
    reservation_key text not null unique,
    reservation_id text
);
insert into order_record values ('O-901','ACC-100','XS0000000001',101.40,'PLN','NEW','reserve-O-901',null);
