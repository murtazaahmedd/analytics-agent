"""Generate a deterministic, thelook_ecommerce-shaped dataset into a DuckDB file.

Planted anomalies (ground truth for why-questions):
  - Checkout conversion for browser 'Safari' drops sharply 2026-10-19..2026-10-25.
  - Return rate for country 'Brasil' spikes in September 2026.
"""

import argparse
import bisect
import csv
import logging
import math
import random
import tempfile
import uuid
from datetime import date, datetime, timedelta
from pathlib import Path

import duckdb

logger = logging.getLogger("generate_thelook")

START = date(2023, 1, 1)
END = date(2026, 10, 31)
SCHEMA = "thelook_ecommerce"
COUNTRIES = {"China": 0.33, "United States": 0.22, "Brasil": 0.15, "South Korea": 0.06, "France": 0.05,
             "United Kingdom": 0.05, "Germany": 0.04, "Spain": 0.04, "Japan": 0.03, "Australia": 0.03}
TRAFFIC = {"Search": 0.70, "Organic": 0.15, "Facebook": 0.06, "Email": 0.05, "Display": 0.04}
BROWSERS = {"Chrome": 0.50, "Safari": 0.20, "Firefox": 0.20, "Edge": 0.05, "IE": 0.05}
CATEGORIES = ["Jeans", "Tops & Tees", "Sweaters", "Outerwear & Coats", "Accessories",
              "Shorts", "Swim", "Active", "Dresses", "Intimates"]
BRANDS = ["Calvin Klein", "Levi's", "Carhartt", "Columbia", "Nike", "Allegra K", "Hanes", "Quiksilver"]
DC_NAMES = ["Memphis TN", "Chicago IL", "Houston TX", "Los Angeles CA", "New Orleans LA",
            "Port Authority of New York/New Jersey NY/NJ", "Philadelphia PA", "Mobile AL",
            "Charleston SC", "Savannah GA"]
SAFARI_DROP = (date(2026, 10, 19), date(2026, 10, 25))
BRASIL_RETURN_MONTH = (2026, 9)


def pick(rng: random.Random, weights: dict[str, float]) -> str:
    """
    #Feature: Synthetic data generation
    #Scenario: Draw one categorical value from a weighted distribution
    #Complexity: Time O(k) - linear in number of categories

    Args:
        rng: Seeded random generator.
        weights: Mapping of value to relative weight.

    Returns:
        The chosen value.

    Raises:
        ValueError: When weights is empty.
    """
    try:
        if not weights:
            raise ValueError("[pick] 'weights' must not be empty. Fix: pass at least one category.")
        return rng.choices(list(weights), weights=list(weights.values()))[0]
    except Exception as exc:
        logger.error("pick failed: %s", exc)
        raise


def ts(day: date, rng: random.Random) -> datetime:
    """
    #Feature: Synthetic data generation
    #Scenario: Produce a random timestamp within a given day
    #Complexity: Time O(1)

    Args:
        day: The calendar day.
        rng: Seeded random generator.

    Returns:
        A datetime on that day.
    """
    try:
        return datetime(day.year, day.month, day.day) + timedelta(seconds=rng.randint(0, 86399))
    except Exception as exc:
        logger.error("ts failed for day=%s: %s", day, exc)
        raise


def daily_sessions(day: date) -> int:
    """
    #Feature: Synthetic data generation
    #Scenario: Session volume with growth, weekly and holiday seasonality
    #Complexity: Time O(1)

    Args:
        day: The calendar day.

    Returns:
        Number of sessions to generate for the day.
    """
    try:
        progress = (day - START).days / (END - START).days
        weekly = 1.1 if day.weekday() >= 5 else 1.0
        holiday = 1.4 if day.month in (11, 12) else 1.0
        return int((40 + 50 * progress) * weekly * holiday)
    except Exception as exc:
        logger.error("daily_sessions failed for day=%s: %s", day, exc)
        raise


def make_products(rng: random.Random) -> list[dict]:
    """
    #Feature: Synthetic data generation
    #Scenario: Build the product catalog
    #Complexity: Time O(n) - n products

    Args:
        rng: Seeded random generator.

    Returns:
        List of product rows.
    """
    try:
        rows = []
        for pid in range(1, 301):
            category = CATEGORIES[pid % len(CATEGORIES)]
            retail = round(rng.uniform(8, 150), 2)
            rows.append({"id": pid, "cost": round(retail * rng.uniform(0.35, 0.6), 4), "category": category,
                         "name": f"{category} item {pid}", "brand": rng.choice(BRANDS), "retail_price": retail,
                         "department": "Women" if pid % 2 else "Men", "sku": uuid.UUID(int=rng.getrandbits(128)).hex,
                         "distribution_center_id": 1 + pid % len(DC_NAMES)})
        return rows
    except Exception as exc:
        logger.error("make_products failed: %s", exc)
        raise


def make_users(rng: random.Random, count: int) -> list[dict]:
    """
    #Feature: Synthetic data generation
    #Scenario: Build registered users with growing sign-ups, sorted by created_at
    #Complexity: Time O(n log n) - sort

    Args:
        rng: Seeded random generator.
        count: Number of users.

    Returns:
        Users sorted by created_at.
    """
    try:
        span = (END - START).days
        users = []
        for uid in range(1, count + 1):
            day = START + timedelta(days=int(span * math.sqrt(rng.random())))
            users.append({"id": uid, "first_name": f"First{uid}", "last_name": f"Last{uid}",
                          "email": f"user{uid}@example.com", "age": rng.randint(12, 70),
                          "gender": rng.choice("MF"), "country": pick(rng, COUNTRIES),
                          "traffic_source": pick(rng, TRAFFIC), "created_at": ts(day, rng)})
        return sorted(users, key=lambda u: u["created_at"])
    except Exception as exc:
        logger.error("make_users failed: %s", exc)
        raise


def purchase_probability(day: date, browser: str) -> float:
    """
    #Feature: Synthetic data generation
    #Scenario: Cart-to-purchase probability, including the planted Safari drop
    #Complexity: Time O(1)

    Args:
        day: Session day.
        browser: Session browser.

    Returns:
        Probability that a carted session purchases.
    """
    try:
        if browser == "Safari" and SAFARI_DROP[0] <= day <= SAFARI_DROP[1]:
            return 0.12
        return 0.5
    except Exception as exc:
        logger.error("purchase_probability failed: %s", exc)
        raise


def order_status(rng: random.Random, created: datetime, country: str) -> str:
    """
    #Feature: Synthetic data generation
    #Scenario: Order status by order age, including the planted Brasil return spike
    #Complexity: Time O(1)

    Args:
        rng: Seeded random generator.
        created: Order creation time.
        country: Customer country.

    Returns:
        One of Processing, Shipped, Complete, Returned, Cancelled.
    """
    try:
        age_days = (END - created.date()).days
        if age_days < 3:
            return pick(rng, {"Processing": 0.85, "Cancelled": 0.15})
        returned = 0.10
        if country == "Brasil" and (created.year, created.month) == BRASIL_RETURN_MONTH:
            returned = 0.45
        if age_days < 10:
            return pick(rng, {"Shipped": 0.7, "Processing": 0.15, "Cancelled": 0.15})
        return pick(rng, {"Complete": 0.75 - returned, "Returned": returned, "Cancelled": 0.15, "Shipped": 0.10})
    except Exception as exc:
        logger.error("order_status failed: %s", exc)
        raise


def clamp(moment: datetime) -> datetime | None:
    """
    #Feature: Synthetic data generation
    #Scenario: Drop lifecycle timestamps that fall after the dataset end
    #Complexity: Time O(1)

    Args:
        moment: Candidate timestamp.

    Returns:
        The timestamp, or None when it is after END.
    """
    try:
        return moment if moment.date() <= END else None
    except Exception as exc:
        logger.error("clamp failed: %s", exc)
        raise


def make_item(rng: random.Random, ctx: dict, product: dict, item_id: int) -> dict:
    """
    #Feature: Synthetic data generation
    #Scenario: One order item with lifecycle timestamps driven by its distribution center
    #Complexity: Time O(1)

    Args:
        rng: Seeded random generator.
        ctx: Order context with order_id, user_id, status, created_at.
        product: Product row.
        item_id: Order item id.

    Returns:
        Order item row.
    """
    try:
        status, created = ctx["status"], ctx["created_at"]
        shipped = delivered = returned = None
        if status in ("Shipped", "Complete", "Returned"):
            shipped = clamp(created + timedelta(hours=rng.uniform(4, 12 + 8 * product["distribution_center_id"])))
        if status in ("Complete", "Returned") and shipped:
            delivered = clamp(shipped + timedelta(hours=rng.uniform(24, 120)))
        if status == "Returned" and delivered:
            returned = clamp(delivered + timedelta(days=rng.uniform(1, 14)))
        if status == "Returned" and returned is None:
            status = "Complete"
        return {"id": item_id, "order_id": ctx["order_id"], "user_id": ctx["user_id"], "product_id": product["id"],
                "inventory_item_id": item_id, "status": status, "created_at": created, "shipped_at": shipped,
                "delivered_at": delivered, "returned_at": returned, "sale_price": product["retail_price"]}
    except Exception as exc:
        logger.error("make_item failed for order_id=%s: %s", ctx.get("order_id"), exc)
        raise


def make_order(rng: random.Random, user: dict, created: datetime, products: list[dict], ids: dict) -> tuple[dict, list]:
    """
    #Feature: Synthetic data generation
    #Scenario: One order and its items, created from a purchase session
    #Complexity: Time O(k) - k items

    Args:
        rng: Seeded random generator.
        user: Purchasing user.
        created: Purchase time.
        products: Product catalog.
        ids: Mutable id counters with keys 'order' and 'item'.

    Returns:
        Tuple of (order row, list of item rows).
    """
    try:
        ids["order"] += 1
        ctx = {"order_id": ids["order"], "user_id": user["id"], "created_at": created,
               "status": order_status(rng, created, user["country"])}
        items = []
        for product in rng.sample(products, rng.choices([1, 2, 3, 4], weights=[60, 25, 10, 5])[0]):
            ids["item"] += 1
            items.append(make_item(rng, ctx, product, ids["item"]))
        order = {"order_id": ctx["order_id"], "user_id": user["id"], "status": items[0]["status"],
                 "gender": user["gender"], "created_at": created,
                 "returned_at": max((i["returned_at"] for i in items if i["returned_at"]), default=None),
                 "shipped_at": min((i["shipped_at"] for i in items if i["shipped_at"]), default=None),
                 "delivered_at": max((i["delivered_at"] for i in items if i["delivered_at"]), default=None),
                 "num_of_item": len(items)}
        return order, items
    except Exception as exc:
        logger.error("make_order failed for user_id=%s: %s", user.get("id"), exc)
        raise


def session_events(rng: random.Random, session: dict, ids: dict) -> tuple[list[dict], datetime | None]:
    """
    #Feature: Synthetic data generation
    #Scenario: Funnel events for one session (home/department/product/cart/purchase)
    #Complexity: Time O(e) - e events

    Args:
        rng: Seeded random generator.
        session: Session context with session_id, user_id, start, browser, traffic_source, day.
        ids: Mutable id counters with key 'event'.

    Returns:
        Tuple of (event rows, purchase time or None).
    """
    try:
        steps = [("home", "/")] + [("product", f"/product/{rng.randint(1, 300)}") for _ in range(rng.randint(1, 3))]
        purchase_at = None
        if rng.random() < 0.35:
            steps.append(("cart", "/cart"))
            if session["user_id"] and rng.random() < purchase_probability(session["day"], session["browser"]):
                steps.append(("purchase", "/purchase"))
        events, moment = [], session["start"]
        for seq, (event_type, uri) in enumerate(steps, start=1):
            ids["event"] += 1
            moment = moment + timedelta(seconds=rng.randint(10, 240))
            purchase_at = moment if event_type == "purchase" else purchase_at
            events.append({"id": ids["event"], "user_id": session["user_id"], "sequence_number": seq,
                           "session_id": session["session_id"], "created_at": moment, "ip_address": "0.0.0.0",
                           "city": None, "state": None, "postal_code": None, "browser": session["browser"],
                           "traffic_source": session["traffic_source"], "uri": uri, "event_type": event_type})
        return events, purchase_at
    except Exception as exc:
        logger.error("session_events failed for session_id=%s: %s", session.get("session_id"), exc)
        raise


def generate_day(rng: random.Random, day: date, state: dict) -> None:
    """
    #Feature: Synthetic data generation
    #Scenario: All sessions, events, orders and items for one day
    #Complexity: Time O(s) - s sessions that day

    Args:
        rng: Seeded random generator.
        day: Calendar day.
        state: Accumulator with users, user_times, products, ids, and output lists.
    """
    try:
        registered = bisect.bisect_right(state["user_times"], datetime(day.year, day.month, day.day, 23, 59))
        for _ in range(daily_sessions(day)):
            user = state["users"][rng.randrange(registered)] if registered and rng.random() < 0.7 else None
            session = {"session_id": uuid.UUID(int=rng.getrandbits(128)).hex, "day": day,
                       "user_id": user["id"] if user else None, "start": ts(day, rng),
                       "browser": pick(rng, BROWSERS),
                       "traffic_source": user["traffic_source"] if user else pick(rng, TRAFFIC)}
            events, purchase_at = session_events(rng, session, state["ids"])
            state["events"].extend(events)
            if purchase_at:
                order, items = make_order(rng, user, purchase_at, state["products"], state["ids"])
                state["orders"].append(order)
                state["order_items"].extend(items)
    except Exception as exc:
        logger.error("generate_day failed for day=%s: %s", day, exc)
        raise


def generate(seed: int, user_count: int) -> dict[str, list[dict]]:
    """
    #Feature: Synthetic data generation
    #Scenario: Build every thelook table in memory
    #Complexity: Time O(d * s) - days times sessions per day

    Args:
        seed: Random seed for determinism.
        user_count: Number of registered users.

    Returns:
        Mapping of table name to rows.
    """
    try:
        rng = random.Random(seed)
        users = make_users(rng, user_count)
        state = {"users": users, "user_times": [u["created_at"] for u in users], "products": make_products(rng),
                 "ids": {"order": 0, "item": 0, "event": 0}, "events": [], "orders": [], "order_items": []}
        day = START
        while day <= END:
            generate_day(rng, day, state)
            day += timedelta(days=1)
        centers = [{"id": i, "name": n, "latitude": 0.0, "longitude": 0.0} for i, n in enumerate(DC_NAMES, start=1)]
        return {"users": users, "products": state["products"], "distribution_centers": centers,
                "events": state["events"], "orders": state["orders"], "order_items": state["order_items"]}
    except Exception as exc:
        logger.error("generate failed for seed=%s: %s", seed, exc)
        raise


def write_csv(path: Path, rows: list[dict]) -> None:
    """
    #Feature: Synthetic data generation
    #Scenario: Persist rows as CSV with empty strings for NULL
    #Complexity: Time O(n)

    Args:
        path: Output CSV path.
        rows: Rows with identical keys.
    """
    try:
        with path.open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
    except Exception as exc:
        logger.error("write_csv failed for path=%s: %s", path, exc)
        raise


def load(con: duckdb.DuckDBPyConnection, tables: dict[str, list[dict]]) -> None:
    """
    #Feature: Synthetic data generation
    #Scenario: Replace the thelook_ecommerce schema in the DuckDB warehouse
    #Complexity: Time O(n) - total rows

    Args:
        con: Read-write DuckDB connection to the warehouse.
        tables: Mapping of table name to rows.
    """
    try:
        with tempfile.TemporaryDirectory() as tmp:
            con.execute(f"drop schema if exists {SCHEMA} cascade; create schema {SCHEMA}")
            for name, rows in tables.items():
                csv_path = Path(tmp) / f"{name}.csv"
                write_csv(csv_path, rows)
                con.execute(f"create table {SCHEMA}.{name} as select * from read_csv(?, header=true, nullstr='')",
                            [str(csv_path)])
                logger.info("loaded %s.%s rows=%d", SCHEMA, name, len(rows))
    except Exception as exc:
        logger.error("load failed: %s", exc)
        raise


def main() -> None:
    """
    #Feature: Synthetic data generation
    #Scenario: CLI entry point
    #Complexity: Time O(d * s)
    """
    try:
        parser = argparse.ArgumentParser(description=__doc__)
        parser.add_argument("--db", type=Path, default=Path("data/warehouse.duckdb"))
        parser.add_argument("--seed", type=int, default=42)
        parser.add_argument("--users", type=int, default=15000)
        args = parser.parse_args()
        logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
        args.db.parent.mkdir(parents=True, exist_ok=True)
        with duckdb.connect(str(args.db)) as con:
            load(con, generate(args.seed, args.users))
    except Exception as exc:
        logger.error("main failed: %s", exc)
        raise


if __name__ == "__main__":
    main()
