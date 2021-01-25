"""
This is where Studio interacts with the learning_sequences application, which
is responsible for holding course outline data. Studio _pushes_ that data into
learning_sequences at publish time.
"""
from datetime import timezone

from edx_django_utils.monitoring import function_trace, set_custom_attribute

from openedx.core.djangoapps.content.learning_sequences.api import replace_course_outline
from openedx.core.djangoapps.content.learning_sequences.data import (
    CourseLearningSequenceData,
    CourseOutlineData,
    CourseSectionData,
    CourseVisibility,
    ExamData,
    VisibilityData,
)
from xmodule.modulestore import COURSE_ROOT, LIBRARY_ROOT, ModuleStoreEnum
from xmodule.modulestore.django import modulestore


@function_trace('get_outline_from_modulestore')
def get_outline_from_modulestore(course_key):
    """
    Get a learning_sequence.data.CourseOutlineData for a param:course_key
    """
    def _remove_version_info(usage_key):
        """
        When we ask modulestore for the published branch in the Studio process
        after catching a publish signal, the items that have been changed will
        return UsageKeys that have full version information in their attached
        CourseKeys. This makes them hash and serialize differently. We want to
        strip this information and have everything use a CourseKey with no
        version information attached.

        IF we can verify that this property is still true when running in an
        out-of-process celery task, it might be a path towards optimizing our
        publish updates to only what has changed–but that carries other risks as
        well in terms of correctness (e.g. race conditions).
        """
        return usage_key.map_into_course(course_key)

    def _make_section_data(section):
        sequences_data = []
        for sequence in section.get_children():
            sequences_data.append(
                CourseLearningSequenceData(
                    usage_key=_remove_version_info(sequence.location),
                    title=sequence.display_name,
                    inaccessible_after_due=sequence.hide_after_due,
                    exam=ExamData(
                        is_practice_exam=sequence.is_practice_exam,
                        is_proctored_enabled=sequence.is_proctored_enabled,
                        is_time_limited=sequence.is_timed_exam
                    ),
                    visibility=VisibilityData(
                        hide_from_toc=sequence.hide_from_toc,
                        visible_to_staff_only=sequence.visible_to_staff_only
                    ),
                )
            )

        section_data = CourseSectionData(
            usage_key=_remove_version_info(section.location),
            title=section.display_name,
            sequences=sequences_data,
            visibility=VisibilityData(
                hide_from_toc=section.hide_from_toc,
                visible_to_staff_only=section.visible_to_staff_only
            ),
        )
        return section_data

    store = modulestore()

    with store.branch_setting(ModuleStoreEnum.Branch.published_only, course_key):
        course = store.get_course(course_key, depth=2)
        sections_data = []
        for section in course.get_children():
            section_data = _make_section_data(section)
            sections_data.append(section_data)

        course_outline_data = CourseOutlineData(
            course_key=course_key,
            title=course.display_name,

            # subtree_edited_on has a tzinfo of bson.tz_util.FixedOffset (which
            # maps to UTC), but for consistency, we're going to use the standard
            # python timezone.utc (which is what the learning_sequence app will
            # return from MySQL). They will compare as equal.
            published_at=course.subtree_edited_on.replace(tzinfo=timezone.utc),

            published_version=str(course.course_version),  # .course_version is a BSON obj
            entrance_exam_id=course.entrance_exam_id,
            days_early_for_beta=course.days_early_for_beta,
            sections=sections_data,
            self_paced=course.self_paced,
            course_visibility=CourseVisibility(course.course_visibility),
        )
    return course_outline_data


def update_outline_from_modulestore(course_key):
    """
    Update the CourseOutlineData for course_key in the learning_sequences with
    ModuleStore data (i.e. what was most recently published in Studio).
    """
    # Set the course_id attribute first so that if getting the information
    # from the modulestore errors out, we still have the course_key reported in
    # New Relic for easier trace debugging.
    set_custom_attribute('course_id', str(course_key))

    course_outline_data = get_outline_from_modulestore(course_key)
    set_custom_attribute('num_sequences', len(course_outline_data.sequences))
    replace_course_outline(course_outline_data)
