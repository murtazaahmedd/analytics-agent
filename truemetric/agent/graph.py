import logging

from truemetric.agent.nodes import AnswererNode, DataGuardNode, RouterNode
from truemetric.constants import (
    BLOCKED_TEMPLATE,
    CLARIFY_TEMPLATE,
    ERROR_TEMPLATE,
    REFUSED_TEMPLATE,
    UNSUPPORTED_WHY,
)
from truemetric.interfaces import ISemanticLayer, ITracer
from truemetric.schemas import AgentAnswer, Intent, Outcome, ParsedQuestion

logger = logging.getLogger(__name__)


class AgentGraph:
    """
    #Feature: Agent decision flow
    #Scenario: Fixed path per question: route -> (clarify | refuse | why | guard -> block | answer)
    #Complexity: Time O(parse + checks + query)

    Two gates come before any number: is the data healthy, and does an approved metric define the ask.
    A "no" at either gate ends in a message, never a guessed number.
    """

    def __init__(self, router: RouterNode, guard: DataGuardNode, answerer: AnswererNode,
                 semantic: ISemanticLayer, tracer: ITracer, workspace_id: str) -> None:
        """
        #Feature: Agent decision flow
        #Scenario: Wire the nodes for one workspace
        #Complexity: Time O(1)

        Args:
            router: Routing node.
            guard: Data guard node.
            answerer: Answering node.
            semantic: Semantic layer, for metric labels in messages.
            tracer: Trace recorder.
            workspace_id: Tenant id.
        """
        try:
            self._router, self._guard, self._answerer = router, guard, answerer
            self._semantic, self._tracer, self._workspace_id = semantic, tracer, workspace_id
        except Exception as exc:
            logger.error("AgentGraph init failed: %s", exc, extra={"tenant_id": workspace_id})
            raise

    def _label(self, metric: str) -> str:
        """
        #Feature: Agent decision flow
        #Scenario: Human label for a metric name
        #Complexity: Time O(1)

        Args:
            metric: Metric name.

        Returns:
            Label.
        """
        try:
            return self._semantic.describe_metric(metric).label
        except Exception as exc:
            logger.error("_label failed: %s", exc, extra={"tenant_id": self._workspace_id})
            raise

    def _clarify(self, parsed: ParsedQuestion, trace_id: str) -> AgentAnswer:
        """
        #Feature: Agent decision flow
        #Scenario: Ambiguous question - ask one clarifying question
        #Complexity: Time O(options)
        """
        try:
            labels = [f"{self._label(o)} ({o})" for o in parsed.options]
            options = ", ".join(labels[:-1]) + f" or {labels[-1]}" if len(labels) > 1 else "".join(labels)
            return AgentAnswer(outcome=Outcome.CLARIFY, text=CLARIFY_TEMPLATE.format(options=options),
                               trace_id=trace_id, options=parsed.options)
        except Exception as exc:
            logger.error("_clarify failed: %s", exc, extra={"tenant_id": self._workspace_id, "session_id": trace_id})
            raise

    def _refuse(self, parsed: ParsedQuestion, trace_id: str) -> AgentAnswer:
        """
        #Feature: Agent decision flow
        #Scenario: No approved metric - refuse and log a metric gap for the drafter
        #Complexity: Time O(1)
        """
        try:
            self._tracer.event(trace_id, "metric_gap", {"gap": parsed.gap})
            return AgentAnswer(outcome=Outcome.REFUSED, text=REFUSED_TEMPLATE.format(gap=parsed.gap),
                               trace_id=trace_id)
        except Exception as exc:
            logger.error("_refuse failed: %s", exc, extra={"tenant_id": self._workspace_id, "session_id": trace_id})
            raise

    def _why(self, parsed: ParsedQuestion, trace_id: str) -> AgentAnswer:
        """
        #Feature: Agent decision flow
        #Scenario: Why-question - root-cause step is not enabled yet
        #Complexity: Time O(1)
        """
        try:
            metric = self._label(parsed.query.metric) if parsed.query else "the metric"
            return AgentAnswer(outcome=Outcome.UNSUPPORTED, text=UNSUPPORTED_WHY.format(metric=metric),
                               trace_id=trace_id, metric=parsed.query.metric if parsed.query else None)
        except Exception as exc:
            logger.error("_why failed: %s", exc, extra={"tenant_id": self._workspace_id, "session_id": trace_id})
            raise

    def _guarded_answer(self, parsed: ParsedQuestion, trace_id: str) -> AgentAnswer:
        """
        #Feature: Agent decision flow
        #Scenario: Run the data guard; answer only if every check passed
        #Complexity: Time O(checks + query)
        """
        try:
            query = parsed.query
            run = self._guard.check(query)
            self._tracer.event(trace_id, "data_guard", run.model_dump(mode="json"))
            if not run.passed:
                failures = "\n".join(f"- {f.table} {f.check}: {f.detail}" for f in run.failures)
                text = BLOCKED_TEMPLATE.format(metric=self._label(query.metric), failures=failures)
                return AgentAnswer(outcome=Outcome.BLOCKED, text=text, trace_id=trace_id, metric=query.metric,
                                   query=query, failed_checks=run.failures)
            result, info, text = self._answerer.answer(query)
            self._tracer.event(trace_id, "answer", {"sql": result.sql, "rows": len(result.rows)})
            return AgentAnswer(outcome=Outcome.ANSWERED, text=text, trace_id=trace_id, metric=info.name,
                               definition=info.description, query=result.query, sql=result.sql,
                               columns=result.columns, rows=result.rows)
        except Exception as exc:
            logger.error("_guarded_answer failed: %s", exc,
                         extra={"tenant_id": self._workspace_id, "session_id": trace_id})
            raise

    def ask(self, question: str) -> AgentAnswer:
        """
        #Feature: Agent decision flow
        #Scenario: Answer one question; any unexpected failure ends without a number
        #Complexity: Time O(parse + checks + query)

        Args:
            question: The user's question.

        Returns:
            AgentAnswer with one of the outcomes.

        Raises:
            ValueError: When question is None or blank.
        """
        if question is None or not question.strip():
            raise ValueError("[AgentGraph.ask] 'question' is required and must not be blank.")
        trace_id = self._tracer.start(self._workspace_id, question)
        try:
            parsed = self._router.route(question)
            self._tracer.event(trace_id, "route", parsed.model_dump(mode="json"))
            handlers = {Intent.UNCLEAR: self._clarify, Intent.OUT_OF_SCOPE: self._refuse,
                        Intent.WHY: self._why, Intent.WHAT: self._guarded_answer}
            answer = handlers[parsed.intent](parsed, trace_id).model_copy(update={"routed_by": parsed.source})
        except Exception as exc:
            logger.error("ask failed: %s", exc, extra={"tenant_id": self._workspace_id, "session_id": trace_id})
            answer = AgentAnswer(outcome=Outcome.ERROR, text=ERROR_TEMPLATE.format(trace_id=trace_id),
                                 trace_id=trace_id)
        self._tracer.event(trace_id, "outcome", {"outcome": answer.outcome.value})
        return answer
