-- Add an existing user (they must have signed in once) to the enforced workspace.
create or replace function api.add_member(p_workspace_id uuid, p_email text, p_role text)
returns table (user_id uuid, email text, role text)
language plpgsql as $$
#variable_conflict use_column
declare
    v_user uuid;
begin
    if p_workspace_id is null or p_email is null or p_role is null then
        raise exception 'api.add_member: workspace, email and role are required' using errcode = 'TM400';
    end if;
    with target as (select u.id from app.users u where u.email = lower(p_email))
    select target.id into v_user from target;
    if v_user is null then
        raise exception 'no user with email %; they must sign in once first', lower(p_email) using errcode = 'TM404';
    end if;
    insert into app.memberships (workspace_id, user_id, role) values (p_workspace_id, v_user, p_role);
    return query select v_user, lower(p_email), p_role;
end
$$;
