"""
ACE message types for the Enrollments module.
"""
from openedx.core.djangoapps.ace_common.message import BaseMessageType


class ProctoringRequirements(BaseMessageType):
    APP_LABEL = 'enrollments'
    Name = 'proctoringrequirements'

    def __init__(self, *args, **kwargs):
        super(ProctoringRequirements, self).__init__(*args, **kwargs)

        self.options['transactional'] = True
