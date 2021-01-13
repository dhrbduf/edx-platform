"""
Course certificate generation

These create new course certificates, or update existing course certificates. For now, these methods deal primarily
with allowlist certificates, and are part of the V2 certificate revamp.
"""

import logging
import random
from uuid import uuid4

import six
from capa.xqueue_interface import make_hashkey
from xmodule.modulestore.django import modulestore

from common.djangoapps.student.models import CourseEnrollment, UserProfile
from lms.djangoapps.certificates.allowlist import can_generate_allowlist_certificate
from lms.djangoapps.certificates.api import emit_certificate_event
from lms.djangoapps.certificates.models import CertificateStatuses, GeneratedCertificate
from lms.djangoapps.certificates.signals import CERTIFICATE_DELAY_SECONDS
from lms.djangoapps.certificates.tasks import generate_certificate
from lms.djangoapps.grades.api import CourseGradeFactory

log = logging.getLogger(__name__)


def generate_allowlist_certificate_task(user, course_key):
    """
    Create a task to generate an allowlist certificate for this user in this course run.
    """
    if not can_generate_allowlist_certificate(user, course_key):
        log.info(
            u'Cannot generate an allowlist certificate for {user} : {course}'.format(user=user.id, course=course_key))
        return

    log.info(
        u'About to create an allowlist certificate task for {user} : {course}'.format(user=user.id, course=course_key))

    kwargs = {
        'student': six.text_type(user.id),
        'course_key': six.text_type(course_key),
        'allowlist_certificate': True
    }
    generate_certificate.apply_async(countdown=CERTIFICATE_DELAY_SECONDS, kwargs=kwargs)


def generate_allowlist_certificate(user, course_key):
    """
    Generate an allowlist certificate for this user, in this course run. This method should be called from a task.
    """
    cert = _generate_certificate(user, course_key)

    if CertificateStatuses.is_passing_status(cert.status):
        event_data = {
            'user_id': user.id,
            'course_id': six.text_type(course_key),
            'certificate_id': cert.verify_uuid,
            'enrollment_mode': cert.mode
        }
        emit_certificate_event(event_name='created', user=user, course_id=course_key, event_data=event_data)
    return cert.status


def _generate_certificate(user, course_id):
    """
    Generate a certificate for this user, in this course run.
    """
    profile = UserProfile.objects.get(user=user)
    profile_name = profile.name

    course = modulestore().get_course(course_id, depth=0)
    course_grade = CourseGradeFactory().read(user, course)
    enrollment_mode, __ = CourseEnrollment.enrollment_mode_for_user(user, course_id)
    cert_mode = enrollment_mode

    cert, created = GeneratedCertificate.objects.get_or_create(user=user, course_id=course_id)

    cert.mode = cert_mode
    cert.user = user
    cert.grade = course_grade.percent
    cert.course_id = course_id
    cert.name = profile_name
    cert.download_url = ''
    key = make_hashkey(random.random())
    cert.key = key
    cert.status = CertificateStatuses.downloadable
    cert.verify_uuid = uuid4().hex

    cert.save()
    log.info(u'Generated certificate with status {status} for {user} : {course}'.format(status=cert.status,
                                                                                        user=cert.user.id,
                                                                                        course=cert.course_id
                                                                                        ))
    return cert
