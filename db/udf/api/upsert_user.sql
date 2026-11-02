-- Create the user on first sign-in, keyed by the identity provider's subject; keep the email current.
create or replace function api.upsert_user(p_subject text, p_email text)
returns uuid
language plpgsql as $$
#variable_conflict use_column
declare
    v_id uuid;
begin
    if p_subject is null or p_email is null then
        raise exception 'api.upsert_user: subject and email are required' using errcode = 'TM400';
    end if;
    insert into app.users (subject, email) values (p_subject, lower(p_email))
    on conflict (subject) do update set email = excluded.email
    returning id into v_id;
    return v_id;
end
$$;
