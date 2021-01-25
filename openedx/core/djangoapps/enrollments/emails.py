"""
ACE emails for Enrollments app
"""
import logging

from django.contrib.sites.models import Site
from edx_ace import ace
from edx_ace.recipient import Recipient

from openedx.core.djangoapps.ace_common.template_context import get_base_template_context
from openedx.core.djangoapps.enrollments.message_types import ProctoringRequirements
from openedx.core.djangoapps.lang_pref import LANGUAGE_KEY
from openedx.core.djangoapps.user_api.preferences.api import get_user_preference
from openedx.core.lib.celery.task_utils import emulate_http_request

log = logging.getLogger(__name__)


def send_proctoring_requirements_email(context):
    """Send an email with proctoring requirements for a course enrollment"""
    site = Site.objects.get_current()
    message_context = get_base_template_context(site)
    message_context.update(context)
    user = context['user']
    try:
        with emulate_http_request(site=site, user=user):
            msg = ProctoringRequirements(context=message_context).personalize(
                recipient=Recipient(user.username, user.email),
                language=get_user_preference(user, LANGUAGE_KEY),
                user_context={'full_name': user.profile.name}
            )
            ace.send(msg)
            log.info('Proctoring requirements email sent to user: %r', user.username)
            return True
    except Exception:  # pylint: disable=broad-except
        log.exception('Could not send email for proctoring requirements to user %s', user.username)
        return False
