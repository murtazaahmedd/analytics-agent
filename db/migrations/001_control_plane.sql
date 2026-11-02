-- Control plane: users, workspaces (tenants), memberships, audit of asks, request log for rate limits.
-- Every workspace-scoped table has row-level security forced, so even a query that skips api.enforce
-- only sees rows of the workspace that enforce authorised for the current transaction.

create schema if not exists app;
create schema if not exists api;

create table if not exists app.users (
    id uuid primary key default gen_random_uuid(),
    subject text not null unique,
    email text not null unique,
    created_at timestamptz not null default now()
);

create table if not exists app.workspaces (
    id uuid primary key,
    name text not null check (length(name) between 1 and 100),
    dbt_project_dir text not null,
    warehouse_path text not null,
    as_of timestamp,
    created_by uuid not null references app.users (id),
    created_at timestamptz not null default now()
);

create table if not exists app.memberships (
    workspace_id uuid not null references app.workspaces (id) on delete cascade,
    user_id uuid not null references app.users (id) on delete cascade,
    role text not null check (role in ('owner', 'editor', 'viewer')),
    created_at timestamptz not null default now(),
    primary key (workspace_id, user_id)
);
create index if not exists memberships_user_idx on app.memberships (user_id);

-- role '*' = any signed-in user, for permissions that need no workspace.
create table if not exists app.role_permissions (
    role text not null,
    permission text not null,
    primary key (role, permission)
);
insert into app.role_permissions (role, permission) values
    ('*', 'workspace.create'),
    ('*', 'workspace.read'),
    ('owner', 'member.create'),
    ('owner', 'ask.execute'),
    ('owner', 'audit.read'),
    ('editor', 'ask.execute'),
    ('editor', 'audit.read'),
    ('viewer', 'ask.execute')
on conflict do nothing;

create table if not exists app.ask_runs (
    id uuid primary key default gen_random_uuid(),
    workspace_id uuid not null references app.workspaces (id) on delete cascade,
    user_id uuid not null references app.users (id),
    question text not null,
    outcome text not null,
    metric text,
    trace_id text not null,
    latency_ms integer not null,
    created_at timestamptz not null default now()
);
create index if not exists ask_runs_workspace_idx on app.ask_runs (workspace_id, created_at desc);

create table if not exists app.request_log (
    user_id uuid not null references app.users (id) on delete cascade,
    permission text not null,
    created_at timestamptz not null default now()
);
create index if not exists request_log_user_idx on app.request_log (user_id, created_at desc);

create or replace function app.current_user_id() returns uuid
language sql stable as $$
    select nullif(current_setting('app.user_id', true), '')::uuid
$$;

create or replace function app.current_workspace_id() returns uuid
language sql stable as $$
    select nullif(current_setting('app.workspace_id', true), '')::uuid
$$;

alter table app.workspaces enable row level security;
alter table app.workspaces force row level security;
alter table app.memberships enable row level security;
alter table app.memberships force row level security;
alter table app.ask_runs enable row level security;
alter table app.ask_runs force row level security;
alter table app.request_log enable row level security;
alter table app.request_log force row level security;

drop policy if exists workspaces_member_read on app.workspaces;
create policy workspaces_member_read on app.workspaces for select
    using (id in (select m.workspace_id from app.memberships m where m.user_id = app.current_user_id()));
drop policy if exists workspaces_creator_insert on app.workspaces;
create policy workspaces_creator_insert on app.workspaces for insert
    with check (created_by = app.current_user_id() and id = app.current_workspace_id());

drop policy if exists memberships_read on app.memberships;
create policy memberships_read on app.memberships for select
    using (user_id = app.current_user_id() or workspace_id = app.current_workspace_id());
drop policy if exists memberships_insert on app.memberships;
create policy memberships_insert on app.memberships for insert
    with check (workspace_id = app.current_workspace_id());

drop policy if exists ask_runs_workspace on app.ask_runs;
create policy ask_runs_workspace on app.ask_runs for all
    using (workspace_id = app.current_workspace_id()
           and workspace_id in (select m.workspace_id from app.memberships m where m.user_id = app.current_user_id()))
    with check (workspace_id = app.current_workspace_id()
                and workspace_id in (select m.workspace_id from app.memberships m
                                     where m.user_id = app.current_user_id()));

drop policy if exists request_log_own on app.request_log;
create policy request_log_own on app.request_log for all
    using (user_id = app.current_user_id())
    with check (user_id = app.current_user_id());

grant usage on schema app, api to truemetric_app;
grant select, insert, update on app.users to truemetric_app;
grant select, insert on app.workspaces, app.memberships, app.ask_runs, app.request_log to truemetric_app;
grant select on app.role_permissions to truemetric_app;
