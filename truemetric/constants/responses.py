CLARIFY_TEMPLATE = "That could mean a few different metrics. Did you mean {options}?"

REFUSED_TEMPLATE = (
    "I can't answer that yet: no approved metric defines {gap}. I won't estimate it with a different "
    "metric. I've logged it as a metric gap so it can be drafted and reviewed."
)

BLOCKED_TEMPLATE = (
    "I'm not answering this because the data behind {metric} failed health checks:\n{failures}\n"
    "Once the data is fixed I can answer."
)

UNSUPPORTED_WHY = (
    "Comparisons and why-questions (root-cause analysis) are not enabled yet, so I won't answer with a "
    "single number. Ask for {metric} for each period separately, or by a dimension."
)

ERROR_TEMPLATE = "Something went wrong while answering, so I'm not returning a number. Trace: {trace_id}."

UNIT_FORMATS: dict[str, str] = {
    "currency": "${:,.2f}",
    "percent": "{:.2%}",
    "count": "{:,.0f}",
    "hours": "{:,.1f} hours",
    "number": "{:,.2f}",
}
