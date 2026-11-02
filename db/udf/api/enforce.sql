-- One call per request: rate limit, membership (RBAC), then bind the transaction to the user and workspace
-- so row-level security only shows that workspace's rows. A missing workspace and a non-member both get TM403,
-- so callers cannot probe which workspace ids exist.
create or replace function api.enforce(p_user_id uuid, p_workspace_id uuid, p_permission text, p_rate_limit integer)
returns table (role text)
language plpgsql as $$
#variable_conflict use_column
declare
    v_role text;
    v_recent integer;
begin
    if p_user_id is null or p_permission is null or p_rate_limit is null then
        raise exception 'api.enforce: user, permission and rate limit are required' using errcode = 'TM400';
    end if;
    perform set_config('app.user_id', p_user_id::text, true);

    with recent as (
        select count(*) as n from app.request_log l
        where l.user_id = p_user_id and l.created_at > now() - interval '1 minute'
    )
    select recent.n into v_recent from recent;
    if v_recent >= p_rate_limit then
        raise exception 'rate limit of % requests per minute reached', p_rate_limit using errcode = 'TM429';
    end if;
    insert into app.request_log (user_id, permission) values (p_user_id, p_permission);

    if p_workspace_id is null then
        if not exists (select 1 from app.role_permissions rp where rp.role = '*' and rp.permission = p_permission) then
            raise exception 'permission % needs a workspace', p_permission using errcode = 'TM403';
        end if;
        return query select null::text;
        return;
    end if;

    with member as (
        select m.role from app.memberships m where m.workspace_id = p_workspace_id and m.user_id = p_user_id
    )
    select member.role into v_role from member;
    if v_role is null then
        raise exception 'not a member of this workspace' using errcode = 'TM403';
    end if;
    if not exists (select 1 from app.role_permissions rp
                   where rp.role in (v_role, '*') and rp.permission = p_permission) then
        raise exception 'role % lacks permission %', v_role, p_permission using errcode = 'TM403';
    end if;
    perform set_config('app.workspace_id', p_workspace_id::text, true);
    return query select v_role;
end
$$;
