-- Append one question and its outcome to the workspace audit log.
create or replace function api.record_ask(p_workspace_id uuid, p_user_id uuid, p_question text, p_outcome text,
                                          p_metric text, p_trace_id text, p_latency_ms integer)
returns uuid
language plpgsql as $$
#variable_conflict use_column
declare
    v_id uuid;
begin
    if p_workspace_id is null or p_user_id is null or p_question is null or p_outcome is null then
        raise exception 'api.record_ask: workspace, user, question and outcome are required' using errcode = 'TM400';
    end if;
    insert into app.ask_runs (workspace_id, user_id, question, outcome, metric, trace_id, latency_ms)
    values (p_workspace_id, p_user_id, p_question, p_outcome, p_metric, p_trace_id, p_latency_ms)
    returning id into v_id;
    return v_id;
end
$$;
