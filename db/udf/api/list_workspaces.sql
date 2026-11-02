-- Workspaces the user belongs to, newest first, with their role in each.
create or replace function api.list_workspaces(p_user_id uuid)
returns table (id uuid, name text, role text, as_of timestamp, created_at timestamptz)
language sql stable as $$
    with mine as (
        select m.workspace_id, m.role from app.memberships m where m.user_id = p_user_id
    )
    select w.id, w.name, (select mine.role from mine where mine.workspace_id = w.id), w.as_of, w.created_at
    from app.workspaces w
    where w.id in (select mine.workspace_id from mine)
    order by w.created_at desc
$$;
