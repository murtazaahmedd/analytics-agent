-- Audit log page for the enforced workspace, newest first.
create or replace function api.list_asks(p_workspace_id uuid, p_limit integer, p_offset integer)
returns table (id uuid, user_email text, question text, outcome text, metric text, trace_id text,
               latency_ms integer, created_at timestamptz)
language sql stable as $$
    with runs as (
        select r.id, r.user_id, r.question, r.outcome, r.metric, r.trace_id, r.latency_ms, r.created_at
        from app.ask_runs r
        where r.workspace_id = p_workspace_id
        order by r.created_at desc
        limit p_limit offset p_offset
    )
    select runs.id, (select u.email from app.users u where u.id = runs.user_id), runs.question, runs.outcome,
           runs.metric, runs.trace_id, runs.latency_ms, runs.created_at
    from runs
    order by runs.created_at desc
$$;
