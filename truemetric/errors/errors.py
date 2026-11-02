class TrueMetricError(Exception):
    """
    #Feature: Error taxonomy
    #Scenario: Base class for all TrueMetric errors
    #Complexity: Time O(1)
    """


class _HTTP:
    """
    #Feature: Error taxonomy
    #Scenario: Errors that map directly to HTTP status codes
    #Complexity: Time O(1)
    """

    class BadRequest(TrueMetricError):
        """
        #Feature: Error taxonomy
        #Scenario: Missing or invalid request parameters (400)
        #Complexity: Time O(1)
        """

    class Unauthorized(TrueMetricError):
        """
        #Feature: Error taxonomy
        #Scenario: Missing or invalid credentials (401)
        #Complexity: Time O(1)
        """

    class Forbidden(TrueMetricError):
        """
        #Feature: Error taxonomy
        #Scenario: Authenticated but not permitted (403)
        #Complexity: Time O(1)
        """

    class NotFound(TrueMetricError):
        """
        #Feature: Error taxonomy
        #Scenario: Resource does not exist (404)
        #Complexity: Time O(1)
        """

    class InternalServerError(TrueMetricError):
        """
        #Feature: Error taxonomy
        #Scenario: Unexpected system failure (500)
        #Complexity: Time O(1)
        """


class _Database:
    """
    #Feature: Error taxonomy
    #Scenario: Control-plane database errors
    #Complexity: Time O(1)
    """

    class IntegrityError(TrueMetricError):
        """
        #Feature: Error taxonomy
        #Scenario: Unique or foreign key constraint violation
        #Complexity: Time O(1)
        """


class _Misc:
    """
    #Feature: Error taxonomy
    #Scenario: Domain business-rule violations
    #Complexity: Time O(1)
    """

    class UnknownMetric(TrueMetricError):
        """
        #Feature: Semantic layer
        #Scenario: A metric name is not defined in the workspace semantic layer
        #Complexity: Time O(1)
        """

    class InvalidDimension(TrueMetricError):
        """
        #Feature: Semantic layer
        #Scenario: A group-by or filter dimension is not reachable from the metric
        #Complexity: Time O(1)
        """

    class UnsafeQuery(TrueMetricError):
        """
        #Feature: Warehouse guardrails
        #Scenario: A query is not a single read-only SELECT statement
        #Complexity: Time O(1)
        """

    class QueryLimitExceeded(TrueMetricError):
        """
        #Feature: Warehouse guardrails
        #Scenario: A query returns more rows than the workspace cap
        #Complexity: Time O(1)
        """


class Errors:
    """
    #Feature: Error taxonomy
    #Scenario: Single entry point for raising TrueMetric errors
    #Complexity: Time O(1)
    """

    HTTP = _HTTP
    Database = _Database
    Misc = _Misc
