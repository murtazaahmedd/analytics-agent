import asyncio
import os
import time
import uuid
from collections.abc import Callable, Iterator
from pathlib import Path

import asyncpg
import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.engine import make_url

from db.udf_load import APP_ROLE, load
from truemetric.main import create_app
from truemetric.schemas import ControlPlaneSettings

SECRET = "test-secret-for-hs256-only-not-for-prod"
APP_PASSWORD = "truemetric-test"
ADMIN_URL = os.environ.get("TRUEMETRIC_TEST_ADMIN_DATABASE_URL")
DEMO = {"dbt_project_dir": "demo_workspaces/thelook", "warehouse_path": "data/warehouse.duckdb",
        "as_of": "2026-11-01T00:00:00"}


def app_url(driver: str) -> str:
    """
    #Feature: Test fixtures
    #Scenario: Same database as the admin URL, but as the non-owner app role so row-level security applies
    #Complexity: Time O(1)
    """
    url = make_url(ADMIN_URL).set(drivername=driver, username=APP_ROLE, password=APP_PASSWORD)
    return url.render_as_string(hide_password=False)


def auth(email: str) -> dict[str, str]:
    """
    #Feature: Test fixtures
    #Scenario: Bearer header for a user identified by email
    #Complexity: Time O(1)
    """
    token = jwt.encode({"sub": f"sub-{email}", "email": email, "exp": int(time.time()) + 600}, SECRET)
    return {"Authorization": f"Bearer {token}"}


def new_email() -> str:
    """
    #Feature: Test fixtures
    #Scenario: A user nobody else in the test run uses
    #Complexity: Time O(1)
    """
    return f"{uuid.uuid4().hex[:10]}@example.com"


async def reset_database() -> None:
    """
    #Feature: Test fixtures
    #Scenario: Load migrations and UDFs, then empty every control-plane table
    #Complexity: Time O(tables)
    """
    await load(ADMIN_URL, APP_PASSWORD)
    conn = await asyncpg.connect(ADMIN_URL)
    try:
        await conn.execute("truncate app.request_log, app.ask_runs, app.memberships, app.workspaces, app.users")
    finally:
        await conn.close()


def make_client(root: Path, rate_limit: int) -> Callable[[], TestClient]:
    """
    #Feature: Test fixtures
    #Scenario: API client with HS256 test tokens and the repository as the workspace root
    #Complexity: Time O(1)
    """
    settings = ControlPlaneSettings(database_url=app_url("postgresql+asyncpg"), jwt_secret=SECRET,
                                    rate_limit_per_minute=rate_limit, workspace_root=root)
    return lambda: TestClient(create_app(settings))


@pytest.fixture(scope="module")
def client(root: Path) -> Iterator[TestClient]:
    """
    #Feature: Test fixtures
    #Scenario: One API process for the module, on a freshly reset control-plane database
    #Complexity: Time O(schema load)
    """
    if not ADMIN_URL:
        pytest.skip("set TRUEMETRIC_TEST_ADMIN_DATABASE_URL to run control-plane tests")
    asyncio.run(reset_database())
    with make_client(root, rate_limit=1000)() as test_client:
        yield test_client


@pytest.fixture
def workspace(client: TestClient, warehouse_path: Path) -> tuple[str, str]:
    """
    #Feature: Test fixtures
    #Scenario: A demo workspace owned by a fresh user
    #Complexity: Time O(1)

    Returns:
        (workspace id, owner email).
    """
    owner = new_email()
    response = client.post("/workspaces", json={"name": "Demo", **DEMO}, headers=auth(owner))
    assert response.status_code == 201, response.text
    return response.json()["id"], owner


def test_health_needs_no_auth(client: TestClient) -> None:
    """
    #Feature: Control plane
    #Scenario: Liveness probe
    #Complexity: Time O(1)
    """
    assert client.get("/health").json() == {"status": "ok"}


def test_missing_or_bad_token_is_401(client: TestClient) -> None:
    """
    #Feature: Authentication
    #Scenario: No token, a token signed with the wrong key, and an expired token are all rejected
    #Complexity: Time O(1)
    """
    wrong_key = jwt.encode({"sub": "x", "email": "x@example.com", "exp": int(time.time()) + 60},
                           "a-different-key-that-is-long-enough")
    expired = jwt.encode({"sub": "x", "email": "x@example.com", "exp": int(time.time()) - 60}, SECRET)
    assert client.get("/workspaces").status_code == 401
    assert client.get("/workspaces", headers={"Authorization": f"Bearer {wrong_key}"}).status_code == 401
    assert client.get("/workspaces", headers={"Authorization": f"Bearer {expired}"}).status_code == 401


def test_owner_asks_and_reads_audit_log(client: TestClient, workspace: tuple[str, str]) -> None:
    """
    #Feature: Ask in plain English
    #Scenario: The owner gets a number from the metric layer, and the question lands in the audit log
    #Complexity: Time O(agent)
    """
    workspace_id, owner = workspace
    listed = client.get("/workspaces", headers=auth(owner)).json()
    assert [w["role"] for w in listed if w["id"] == workspace_id] == ["owner"]
    answer = client.post(f"/workspaces/{workspace_id}/ask", json={"question": "What was net revenue in March 2024?"},
                         headers=auth(owner))
    assert answer.status_code == 200 and answer.json()["outcome"] == "answered"
    assert answer.json()["metric"] == "net_revenue" and answer.json()["rows"]
    log = client.get(f"/workspaces/{workspace_id}/asks", headers=auth(owner)).json()
    assert [(r["user_email"], r["outcome"]) for r in log] == [(owner, "answered")]


def test_non_member_cannot_reach_workspace(client: TestClient, workspace: tuple[str, str]) -> None:
    """
    #Feature: Tenant isolation
    #Scenario: Another user sees nothing and every workspace endpoint answers 403
    #Complexity: Time O(1)
    """
    workspace_id, _ = workspace
    stranger = auth(new_email())
    assert workspace_id not in [w["id"] for w in client.get("/workspaces", headers=stranger).json()]
    assert client.post(f"/workspaces/{workspace_id}/ask", json={"question": "Orders last month"},
                       headers=stranger).status_code == 403
    assert client.get(f"/workspaces/{workspace_id}/asks", headers=stranger).status_code == 403
    assert client.post(f"/workspaces/{workspace_id}/members", json={"email": "a@example.com"},
                       headers=stranger).status_code == 403


def test_unknown_workspace_looks_like_403(client: TestClient) -> None:
    """
    #Feature: Tenant isolation
    #Scenario: A random workspace id is indistinguishable from someone else's workspace
    #Complexity: Time O(1)
    """
    response = client.get(f"/workspaces/{uuid.uuid4()}/asks", headers=auth(new_email()))
    assert response.status_code == 403


def test_viewer_can_ask_but_not_read_audit_or_invite(client: TestClient, workspace: tuple[str, str]) -> None:
    """
    #Feature: Access control
    #Scenario: Role permissions - viewers ask; only owners invite; viewers cannot read the audit log
    #Complexity: Time O(agent)
    """
    workspace_id, owner = workspace
    viewer = new_email()
    client.get("/workspaces", headers=auth(viewer))
    added = client.post(f"/workspaces/{workspace_id}/members", json={"email": viewer}, headers=auth(owner))
    assert added.status_code == 201 and added.json()["role"] == "viewer"
    asked = client.post(f"/workspaces/{workspace_id}/ask", json={"question": "Orders last month"},
                        headers=auth(viewer))
    assert asked.status_code == 200
    assert client.get(f"/workspaces/{workspace_id}/asks", headers=auth(viewer)).status_code == 403
    assert client.post(f"/workspaces/{workspace_id}/members", json={"email": new_email()},
                       headers=auth(viewer)).status_code == 403


def test_member_errors(client: TestClient, workspace: tuple[str, str]) -> None:
    """
    #Feature: Workspaces
    #Scenario: Inviting a user who never signed in is 404; inviting a member twice is 409
    #Complexity: Time O(1)
    """
    workspace_id, owner = workspace
    assert client.post(f"/workspaces/{workspace_id}/members", json={"email": new_email()},
                       headers=auth(owner)).status_code == 404
    editor = new_email()
    client.get("/workspaces", headers=auth(editor))
    body = {"email": editor, "role": "editor"}
    assert client.post(f"/workspaces/{workspace_id}/members", json=body, headers=auth(owner)).status_code == 201
    assert client.post(f"/workspaces/{workspace_id}/members", json=body, headers=auth(owner)).status_code == 409


@pytest.mark.parametrize("field,value", [("dbt_project_dir", "../"), ("dbt_project_dir", "/etc"),
                                         ("warehouse_path", "data/missing.duckdb")])
def test_workspace_paths_must_exist_inside_root(client: TestClient, field: str, value: str) -> None:
    """
    #Feature: Workspaces
    #Scenario: Paths outside the workspace root or that do not exist are rejected before anything is stored
    #Complexity: Time O(1)
    """
    response = client.post("/workspaces", json={"name": "Bad", **DEMO, field: value}, headers=auth(new_email()))
    assert response.status_code == 400


def test_row_level_security_without_membership(client: TestClient, workspace: tuple[str, str]) -> None:
    """
    #Feature: Tenant isolation
    #Scenario: Even if the transaction is bound to a workspace by mistake, a non-member reads no rows
    #Complexity: Time O(1)
    """
    workspace_id, owner = workspace
    client.post(f"/workspaces/{workspace_id}/ask", json={"question": "Orders last month"}, headers=auth(owner))
    stranger = client.get("/workspaces", headers=auth(new_email()))
    assert stranger.status_code == 200

    async def visible_rows(email: str) -> tuple[int, int]:
        conn = await asyncpg.connect(app_url("postgresql"))
        try:
            async with conn.transaction():
                user_id = await conn.fetchval("select id from app.users where email = $1", email)
                await conn.execute("select set_config('app.user_id', $1, true)", str(user_id))
                await conn.execute("select set_config('app.workspace_id', $1, true)", workspace_id)
                runs = await conn.fetchval("select count(*) from app.ask_runs")
                spaces = await conn.fetchval("select count(*) from app.workspaces")
                return runs, spaces
        finally:
            await conn.close()

    outsider = new_email()
    client.get("/workspaces", headers=auth(outsider))
    assert asyncio.run(visible_rows(outsider)) == (0, 0)
    assert asyncio.run(visible_rows(owner))[0] >= 1


def test_rate_limit_is_429(client: TestClient, root: Path) -> None:
    """
    #Feature: Access control
    #Scenario: Requests over the per-minute limit are refused
    #Complexity: Time O(limit)
    """
    with make_client(root, rate_limit=2)() as limited:
        headers = auth(new_email())
        codes = [limited.get("/workspaces", headers=headers).status_code for _ in range(3)]
    assert codes == [200, 200, 429]
