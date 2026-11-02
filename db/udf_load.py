import argparse
import asyncio
import logging
import os
from pathlib import Path

import asyncpg

logger = logging.getLogger(__name__)

DB_DIR = Path(__file__).resolve().parent
APP_ROLE = "truemetric_app"
MIGRATIONS = ["migrations/001_control_plane.sql"]
UDFS = [
    "udf/api/upsert_user.sql",
    "udf/api/enforce.sql",
    "udf/api/create_workspace.sql",
    "udf/api/list_workspaces.sql",
    "udf/api/get_workspace.sql",
    "udf/api/add_member.sql",
    "udf/api/record_ask.sql",
    "udf/api/list_asks.sql",
]


def app_role_sql(password: str) -> str:
    """
    #Feature: Control-plane database
    #Scenario: Create or update the login role the API connects as (not an owner, so row-level security applies)
    #Complexity: Time O(len(password))

    Args:
        password: Password for the app role.

    Returns:
        A DO block; the password is quoted as a SQL literal.

    Raises:
        ValueError: When password is None or empty.
    """
    try:
        if not password:
            raise ValueError("[app_role_sql] 'password' is required. Fix: set TRUEMETRIC_DB_APP_PASSWORD.")
        literal = "'" + password.replace("'", "''") + "'"
        return (f"do $$ begin if not exists (select from pg_roles where rolname = '{APP_ROLE}') then "
                f"create role {APP_ROLE} login password {literal}; "
                f"else alter role {APP_ROLE} login password {literal}; end if; end $$;")
    except Exception as exc:
        logger.error("app_role_sql failed: %s", exc)
        raise


async def load(admin_url: str, app_password: str) -> None:
    """
    #Feature: Control-plane database
    #Scenario: Apply migrations and (re)register every api.* UDF, then grant execute to the app role
    #Complexity: Time O(files)

    Args:
        admin_url: postgresql:// URL of a role that owns the schema.
        app_password: Password for the truemetric_app login role.

    Raises:
        ValueError: When admin_url is None or empty.
    """
    if not admin_url:
        raise ValueError("[load] 'admin_url' is required. Fix: set TRUEMETRIC_ADMIN_DATABASE_URL.")
    conn = await asyncpg.connect(admin_url)
    try:
        await conn.execute(app_role_sql(app_password))
        for name in MIGRATIONS + UDFS:
            await conn.execute((DB_DIR / name).read_text())
        await conn.execute(f"grant execute on all functions in schema api, app to {APP_ROLE};")
    except Exception as exc:
        logger.error("load failed: %s", exc)
        raise
    finally:
        await conn.close()


def main() -> None:
    """
    #Feature: Control-plane database
    #Scenario: CLI entry point (`make db`)
    #Complexity: Time O(files)
    """
    try:
        parser = argparse.ArgumentParser(description="Apply control-plane migrations and api.* UDFs.")
        parser.add_argument("--admin-url", default=os.environ.get("TRUEMETRIC_ADMIN_DATABASE_URL"))
        parser.add_argument("--app-password", default=os.environ.get("TRUEMETRIC_DB_APP_PASSWORD"))
        args = parser.parse_args()
        asyncio.run(load(args.admin_url, args.app_password))
        print("control plane schema and UDFs loaded")
    except Exception as exc:
        logger.error("udf_load failed: %s", exc)
        raise


if __name__ == "__main__":
    main()
