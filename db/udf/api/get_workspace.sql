-- Runtime settings of one workspace. Row-level security hides workspaces the caller was not enforced into.
create or replace function api.get_workspace(p_workspace_id uuid)
returns table (id uuid, name text, dbt_project_dir text, warehouse_path text, as_of timestamp)
language plpgsql stable as $$
#variable_conflict use_column
begin
    return query
        with target as (
            select w.id, w.name, w.dbt_project_dir, w.warehouse_path, w.as_of
            from app.workspaces w where w.id = p_workspace_id
        )
        select target.id, target.name, target.dbt_project_dir, target.warehouse_path, target.as_of from target;
    if not found then
        raise exception 'workspace not found' using errcode = 'TM404';
    end if;
end
$$;
