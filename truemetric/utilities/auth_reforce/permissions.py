class WorkspacePermissions:
    """
    #Feature: Access control
    #Scenario: Permissions on workspaces (granted to every signed-in user)
    #Complexity: Time O(1)
    """

    create = "workspace.create"
    read = "workspace.read"


class MemberPermissions:
    """
    #Feature: Access control
    #Scenario: Permissions on workspace memberships (owners only)
    #Complexity: Time O(1)
    """

    create = "member.create"


class AskPermissions:
    """
    #Feature: Access control
    #Scenario: Asking questions (every member)
    #Complexity: Time O(1)
    """

    execute = "ask.execute"


class AuditPermissions:
    """
    #Feature: Access control
    #Scenario: Reading the audit log (owners and editors)
    #Complexity: Time O(1)
    """

    read = "audit.read"


workspace = WorkspacePermissions()
member = MemberPermissions()
ask = AskPermissions()
audit = AuditPermissions()
