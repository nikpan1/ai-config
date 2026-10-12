create table investor (
    investor_ref text primary key,
    status text not null check (status in ('ACTIVE','PENDING','SUSPENDED','CLOSED'))
);
create table dictionary_code (
    dictionary_name text not null,
    code text not null,
    revision text not null,
    label text not null,
    retired boolean not null default false,
    primary key (dictionary_name, code, revision)
);
create table questionnaire_version (
    version text primary key,
    effective_from timestamptz not null,
    retired boolean not null
);
create table profile_draft (
    draft_id text primary key,
    investor_ref text not null references investor(investor_ref),
    questionnaire_version text not null references questionnaire_version(version),
    status text not null check (status in ('DRAFT','SUBMITTED')),
    answers jsonb,
    consent_revision text,
    consent_at timestamptz,
    revision bigint not null,
    created_at timestamptz not null default now()
);
create unique index one_open_draft_per_investor on profile_draft(investor_ref) where status = 'DRAFT';
create table submission_key (
    idempotency_key text primary key,
    draft_id text not null references profile_draft(draft_id),
    answer_hash text not null
);
create table profile_summary (
    assessment_id text primary key,
    investor_ref text not null references investor(investor_ref),
    draft_id text not null references profile_draft(draft_id),
    questionnaire_version text not null,
    rules_version text not null,
    provider_assessment_id text not null,
    band text not null check (band in ('R1','R2','R3','R4')),
    reason_codes text not null,
    accepted_at timestamptz not null,
    status text not null check (status in ('ACTIVE','EXPIRED','SUPERSEDED')),
    idempotency_key text not null unique references submission_key(idempotency_key)
);
create unique index one_active_profile_per_investor on profile_summary(investor_ref) where status = 'ACTIVE';
