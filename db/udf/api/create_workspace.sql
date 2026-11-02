-- New workspace with the caller as owner. Must run after api.enforce('workspace.create') in the same transaction.
create or replace function api.create_workspace(p_user_id uuid, p_name text, p_dbt_project_dir text,
                                                p_warehouse_path text, p_as_of timestamp)
returns table (id uuid, name text, role text, as_of timestamp, created_at timestamptz)
language plpgsql as $$
#variable_conflict use_column
declare
    v_id uuid := gen_random_uuid();
begin
    if p_user_id is null or p_name is null or p_dbt_project_dir is null or p_warehouse_path is null then
        raise exception 'api.create_workspace: user, name and paths are required' using errcode = 'TM400';
    end if;
    perform set_config('app.workspace_id', v_id::text, true);
    insert into app.workspaces (id, name, dbt_project_dir, warehouse_path, as_of, created_by)
    values (v_id, p_name, p_dbt_project_dir, p_warehouse_path, p_as_of, p_user_id);
    insert into app.memberships (workspace_id, user_id, role) values (v_id, p_user_id, 'owner');
    return query
        with created as (select w.id, w.name, w.as_of, w.created_at from app.workspaces w where w.id = v_id)
        select created.id, created.name, 'owner'::text, created.as_of, created.created_at from created;
end
$$;
