"""
Course certificate allowlist

The allowlist contains users and the course runs in which they have explicitly been granted certificates. It is V2 of
the certificate whitelist.
"""

import logging

from edx_toggles.toggles import LegacyWaffleFlagNamespace

from lms.djangoapps.certificates.models import (
    CertificateStatuses,
    CertificateInvalidation,
    CertificateWhitelist,
    GeneratedCertificate
)
from openedx.core.djangoapps.certificates.api import auto_certificate_generation_enabled
from openedx.core.djangoapps.waffle_utils import CourseWaffleFlag

log = logging.getLogger(__name__)

WAFFLE_FLAG_NAMESPACE = LegacyWaffleFlagNamespace(name='certificates_revamp')

CERTIFICATES_USE_ALLOWLIST = CourseWaffleFlag(
    waffle_namespace=WAFFLE_FLAG_NAMESPACE,
    flag_name=u'use_allowlist',
    module_name=__name__,
)


def can_generate_allowlist_certificate(user, course_key):
    """
    Check if an allowlist certificate can be generated (created if it doesn't already exist, or updated if it does
    exist) for this user, in this course run.
    """
    if not auto_certificate_generation_enabled():
        # Automatic certificate generation is globally disabled
        return False

    if CertificateInvalidation.has_certificate_invalidation(user, course_key):
        # The invalidation list overrides the allowlist
        return False

    if not _is_using_certificate_allowlist(course_key):
        # This course run is not using the allowlist feature
        return False

    if CertificateWhitelist.objects.filter(user=user, course_id=course_key, whitelist=True).exists():
        log.info(u'{user} : {course} is on the certificate allowlist'.format(
            user=user.id,
            course=course_key
        ))
        cert = GeneratedCertificate.certificate_for_student(user, course_key)
        return _can_generate_allowlist_certificate_for_status(cert)

    return False


def _is_using_certificate_allowlist(course_key):
    """
    Check if the course run is using the allowlist, aka V2 of certificate whitelisting
    """
    return CERTIFICATES_USE_ALLOWLIST.is_enabled(course_key)


def _can_generate_allowlist_certificate_for_status(cert):
    """
    Check if the user's certificate status allows certificate generation
    """
    if cert is None:
        return True

    if cert.status == CertificateStatuses.downloadable:
        log.info(u'Certificate with status {status} already exists for {user} : {course}, and is NOT eligible for '
                 u'allowlist generation'.format(status=cert.status,
                                                user=cert.user.id,
                                                course=cert.course_id
                                                ))
        return False

    log.info(u'Certificate with status {status} already exists for {user} : {course}, and is eligible for '
             u'allowlist generation'.format(status=cert.status,
                                            user=cert.user.id,
                                            course=cert.course_id
                                            ))
    return True
