from nodeconductor.logging.log import EventLogger, event_logger
from nodeconductor.core.models import User
from nodeconductor.structure import models
from nodeconductor.structure.filters import filter_queryset_for_user


class CustomerEventLogger(EventLogger):
    customer = models.Customer

    class Meta:
        event_types = ('customer_deletion_succeeded',
                       'customer_update_succeeded',
                       'customer_creation_succeeded')


class BalanceEventLogger(EventLogger):
    customer = models.Customer
    amount = float

    class Meta:
        event_types = ('customer_account_credited',
                       'customer_account_debited')


class ProjectEventLogger(EventLogger):
    project = models.Project
    project_group = models.ProjectGroup

    class Meta:
        nullable_fields = ['project_group']
        event_types = ('project_deletion_succeeded',
                       'project_update_succeeded',
                       'project_creation_succeeded')


class ProjectGroupEventLogger(EventLogger):
    project_group = models.ProjectGroup

    class Meta:
        event_types = ('project_group_deletion_succeeded',
                       'project_group_update_succeeded',
                       'project_group_creation_succeeded')


class CustomerRoleEventLogger(EventLogger):
    customer = models.Customer
    affected_user = User
    structure_type = basestring
    role_name = basestring

    class Meta:
        event_types = 'role_granted', 'role_revoked'


class ProjectRoleEventLogger(EventLogger):
    project = models.Project
    project_group = models.ProjectGroup
    affected_user = User
    structure_type = basestring
    role_name = basestring

    class Meta:
        nullable_fields = ['project_group']
        event_types = 'role_granted', 'role_revoked'


class ProjectGroupRoleEventLogger(EventLogger):
    project_group = models.ProjectGroup
    affected_user = User
    structure_type = basestring
    role_name = basestring

    class Meta:
        event_types = 'role_granted', 'role_revoked'


class ProjectGroupMembershipEventLogger(EventLogger):
    project = models.Project
    project_group = models.ProjectGroup

    class Meta:
        event_types = 'project_added_to_project_group', 'project_removed_from_project_group'


class UserOrganizationEventLogger(EventLogger):
    affected_user = User
    affected_organization = basestring

    class Meta:
        event_types = ('user_organization_claimed',
                       'user_organization_approved',
                       'user_organization_rejected',
                       'user_organization_removed')


event_logger.register('customer_role', CustomerRoleEventLogger)
event_logger.register('project_role', ProjectRoleEventLogger)
event_logger.register('project_group_role', ProjectGroupRoleEventLogger)
event_logger.register('project_group_membership', ProjectGroupMembershipEventLogger)
event_logger.register('user_organization', UserOrganizationEventLogger)
event_logger.register('customer', CustomerEventLogger)
event_logger.register('project', ProjectEventLogger)
event_logger.register('project_group', ProjectGroupEventLogger)
event_logger.register('balance', BalanceEventLogger)
