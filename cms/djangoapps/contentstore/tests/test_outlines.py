"""
Test the interaction with the learning_sequences app, where course outlines are
stored.
"""
from datetime import datetime, timezone

from opaque_keys.edx.keys import CourseKey

from openedx.core.djangoapps.content.learning_sequences.data import (
    CourseLearningSequenceData,
    CourseOutlineData,
    CourseSectionData,
    CourseVisibility,
    ExamData,
    VisibilityData,
)
from openedx.core.djangoapps.content.learning_sequences.api import get_course_outline
from xmodule.modulestore import ModuleStoreEnum
from xmodule.modulestore.tests.django_utils import ModuleStoreTestCase
from xmodule.modulestore.tests.factories import CourseFactory, ItemFactory

from ..outlines import get_outline_from_modulestore


class OutlineFromModuleStoreTestCase(ModuleStoreTestCase):
    """
    These tests all set up some sort of course content data in the modulestore
    and extract that data using get_course_outline() to make sure that it
    creates the CourseOutlineData that we expect.

    The learning_sequences app has its own tests to test different scenarios for
    creating the outline. This set of tests only cares about making sure the
    data comes out of the Modulestore in the way we expect.

    Comparisons are done on individual attributes rather than making a complete
    CourseOutline object for comparison, so that more data fields can be added
    later without breaking tests.
    """
    ENABLED_SIGNALS = []
    ENABLED_CACHES = []

    def setUp(self):
        """Create the minimum necessary course for reading outline data."""
        super().setUp()

    def test_empty_course_metadata(self):
        """Courses start empty, and could have a section with no sequences."""
        course_key = CourseKey.from_string("course-v1:TNL+7733+2021-01-22")

        # This CourseFactory will be a reference to data in the *draft* branch.
        draft_course = CourseFactory.create(
            # Course Key
            org=course_key.org,
            course=course_key.course,
            run=course_key.run,

            # Storage Type
            default_store=ModuleStoreEnum.Type.split,

            # Metadata
            display_name="My Course",
        )

        # The learning_sequences app only uses the published branch, which will
        # have slightly different metadata for version and published_at (because
        # it's created a tiny fraction of a second later). Explicitly pull from
        # published branch to make sure we have the right data.
        with self.store.branch_setting(ModuleStoreEnum.Branch.published_only, course_key):
            published_course = self.store.get_course(course_key, depth=2)
        outline = get_outline_from_modulestore(course_key)

        # Check basic metdata...
        assert outline.title == "My Course"

        # published_at
        assert isinstance(outline.published_at, datetime)
        assert outline.published_at == published_course.subtree_edited_on
        assert outline.published_at.tzinfo == timezone.utc

        # published_version
        assert isinstance(outline.published_version, str)
        assert outline.published_version == str(published_course.course_version)  # str, not BSON

        # Misc.
        assert outline.entrance_exam_id == published_course.entrance_exam_id
        assert outline.days_early_for_beta == published_course.days_early_for_beta
        assert outline.self_paced == published_course.self_paced

        # Outline stores an enum for course_visibility, while Modulestore uses strs...
        assert outline.course_visibility.value == published_course.course_visibility

        # Check that the contents are empty.
        assert len(outline.sections) == 0
        assert len(outline.sequences) == 0




    #def test_simple_course_metadata(self):
    #    pass
        #with self.store.bulk_operations(self.course_key):
        #    self.course.

    #def test_visibility(self):
    #    pass

    #def test_exam(self):
    #    pass



class OutlineFromModuleStoreTaskTestCase(ModuleStoreTestCase):
    """
    Test to make sure that the outline is created after course publishing. (i.e.
    that it correctly receives the course_published signal).
    """
    ENABLED_SIGNALS = ['course_published']

    def test_task_invocation(self):
        """Test outline auto-creation after course publish"""
        course_key = CourseKey.from_string("course-v1:TNL+7733+2021-01-21")
        with self.assertRaises(CourseOutlineData.DoesNotExist):
            get_course_outline(course_key)

        course = CourseFactory.create(
            org=course_key.org,
            course=course_key.course,
            run=course_key.run,
            default_store=ModuleStoreEnum.Type.split,
       )
        section = ItemFactory.create(
            parent_location=course.location,
            category="chapter",
            display_name="First Section"
        )
        ItemFactory.create(
            parent_location=section.location,
            category="sequential",
            display_name="First Sequence"
        )
        ItemFactory.create(
            parent_location=section.location,
            category="sequential",
            display_name="Second Sequence"
        )
        self.store.publish(course.location, self.user.id)

        outline = get_course_outline(course_key)
        assert len(outline.sections) == 1
        assert len(outline.sequences) == 2
