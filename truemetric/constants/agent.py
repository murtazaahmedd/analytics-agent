METRIC_SYNONYMS: dict[str, str] = {
    "gross revenue": "gross_revenue",
    "gross sales": "gross_revenue",
    "net revenue": "net_revenue",
    "net sales": "net_revenue",
    "returned revenue": "returned_revenue",
    "number of orders": "orders",
    "order count": "orders",
    "orders": "orders",
    "average order value": "average_order_value",
    "avg order value": "average_order_value",
    "aov": "average_order_value",
    "basket size": "average_order_value",
    "units sold": "units_sold",
    "units": "units_sold",
    "items sold": "units_sold",
    "return rate": "return_rate",
    "returns rate": "return_rate",
    "cancellation rate": "cancellation_rate",
    "cancel rate": "cancellation_rate",
    "cancelled orders": "cancelled_orders",
    "gross margin": "gross_margin",
    "margin": "gross_margin",
    "new customers": "new_customers",
    "first time customers": "new_customers",
    "repeat purchase rate": "repeat_purchase_rate",
    "repeat rate": "repeat_purchase_rate",
    "sessions": "sessions",
    "visits": "sessions",
    "session to cart rate": "session_to_cart_rate",
    "add to cart rate": "session_to_cart_rate",
    "cart rate": "session_to_cart_rate",
    "checkout conversion": "checkout_conversion",
    "conversion rate": "checkout_conversion",
    "conversion": "checkout_conversion",
    "fulfilment time": "fulfilment_time_hours",
    "fulfillment time": "fulfilment_time_hours",
    "time to ship": "fulfilment_time_hours",
    "active customers": "active_customers",
}

AMBIGUOUS_TERMS: dict[str, list[str]] = {
    "sales": ["gross_revenue", "net_revenue", "units_sold"],
    "revenue": ["gross_revenue", "net_revenue"],
    "customers": ["active_customers", "new_customers"],
    "business": ["net_revenue", "orders", "checkout_conversion"],
    "performance": ["net_revenue", "orders", "checkout_conversion"],
    "kpis": ["net_revenue", "orders", "checkout_conversion"],
}

OUT_OF_SCOPE_TERMS: list[str] = [
    "lifetime value", "ltv", "clv", "cohort", "retention", "churn", "per session", "per visitor",
    "per customer", "90 day", "60 day", "30 day repeat", "first order category", "marketing spend",
    "ad spend", "cac", "roas", "inventory", "stock level", "refund amount", "forecast", "predict",
]

WHY_MARKERS: list[str] = [
    "why ", "what drove", "what caused", "what explains", "explain the", "root cause",
    " change", " changed", " compare", " compared", " vs ", " versus ", "over week", " drop", " spike",
]

DIMENSION_SYNONYMS: dict[str, str] = {
    "countries": "country",
    "country": "country",
    "markets": "country",
    "categories": "category",
    "category": "category",
    "brands": "brand",
    "brand": "brand",
    "browsers": "browser",
    "browser": "browser",
    "traffic sources": "traffic_source",
    "traffic source": "traffic_source",
    "channels": "traffic_source",
    "channel": "traffic_source",
    "distribution centers": "distribution_center",
    "distribution center": "distribution_center",
    "distribution centres": "distribution_center",
    "distribution centre": "distribution_center",
    "departments": "department",
    "department": "department",
    "order status": "status",
    "status": "status",
    "gender": "gender",
}

VALUE_ALIASES: dict[str, str] = {
    "usa": "United States",
    "america": "United States",
    "uk": "United Kingdom",
    "britain": "United Kingdom",
    "brazil": "Brasil",
    "korea": "South Korea",
    "brazilian": "Brasil",
    "american": "United States",
    "chinese": "China",
    "french": "France",
    "german": "Germany",
    "spanish": "Spain",
    "japanese": "Japan",
    "british": "United Kingdom",
    "korean": "South Korea",
    "australian": "Australia",
}

RATE_WORDS: list[str] = ["share of", "as a share", "percent", "percentage", "%", "proportion", "fraction",
                         "how often", "what rate"]

NUMBER_WORDS: dict[str, int] = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
                                "eight": 8, "nine": 9, "ten": 10}

FILTER_SKIP_DIMENSIONS: set[str] = {"status", "gender"}

GRAIN_WORDS: dict[str, str] = {
    "daily": "day", "by day": "day", "per day": "day", "each day": "day",
    "weekly": "week", "by week": "week", "per week": "week", "each week": "week",
    "monthly": "month", "by month": "month", "per month": "month", "each month": "month", "month over month": "month",
    "quarterly": "quarter", "by quarter": "quarter", "per quarter": "quarter",
    "yearly": "year", "annually": "year", "by year": "year", "per year": "year",
}
