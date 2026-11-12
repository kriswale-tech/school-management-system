from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from academics.models import ClassSubject, LevelSubject, Subject
from academics.services.curriculum import provision_school_curriculum, seed_ghana_curriculum
from academics.services.curriculum_versions import (
    adopt,
    apply_accepted_curriculum,
    plan_adoption,
    publish_draft,
    save_draft,
    start_draft,
)
from accounts.models import User
from accounts.tests.factories import create_school, create_user, set_client_auth_cookies, user_school
from schools.services.alerts import list_school_alerts
from schools.tests.factories import create_active_term
from teachers.models import TeachingAssignment


class CurriculumVersionTests(APITestCase):
    def setUp(self):
        seed_ghana_curriculum()
        self.school = create_school(name='Coding with Sir Chris', phone_number='+233200111001')
        provision_school_curriculum(self.school)
        self.school.refresh_from_db()
        self.original_id = self.school.provisioned_curriculum_id

    def _rename_rme(self, levels):
        found = False
        for level in levels:
            for subject in level['subjects']:
                if subject['name'] == 'Religious and Moral Education':
                    subject['name'] = 'Religion'
                    found = True
        if not found:
            self.fail('Religious and Moral Education was not in the draft')

    def test_publish_leaves_existing_school_and_alerts_its_admin(self):
        draft = start_draft()
        self._rename_rme(draft['levels'])
        for level in draft['levels']:
            if level['name'] == 'Lower Primary':
                level['subjects'].append({'lineage_id': '', 'name': 'Robotics'})
        save_draft(draft['id'], version=draft['version'], levels=draft['levels'])
        published = publish_draft(draft['id'])

        self.school.refresh_from_db()
        self.assertEqual(self.school.provisioned_curriculum_id, self.original_id)
        self.assertTrue(
            Subject.objects.filter(
                school=self.school,
                name='Religious and Moral Education',
            ).exists(),
        )
        self.assertFalse(
            Subject.objects.filter(school=self.school, name='Robotics').exists(),
        )
        self.assertGreater(published['schools_alerted'], 0)

        admin = create_user(
            phone_number='+233200111002',
            email='curriculum-admin@test.com',
            school=self.school,
            is_active=True,
        )
        membership = admin.memberships.get(school=self.school)
        alerts = list_school_alerts(school=self.school, membership=membership)
        self.assertEqual(alerts[0]['kind'], 'curriculum')
        self.assertIn(published['curriculum']['version'], alerts[0]['summary'])

        fresh = create_school(name='New Academy', phone_number='+233200111003')
        provision_school_curriculum(fresh)
        fresh.refresh_from_db()
        self.assertEqual(str(fresh.provisioned_curriculum_id), str(published['curriculum']['id']))
        self.assertTrue(Subject.objects.filter(school=fresh, name='Robotics').exists())
        self.assertTrue(Subject.objects.filter(school=fresh, name='Religion').exists())

    def test_adopt_keeps_a_taught_subject_name(self):
        draft = start_draft()
        self._rename_rme(draft['levels'])
        save_draft(draft['id'], version='2025', levels=draft['levels'])
        publish_draft(draft['id'])

        class_subject = ClassSubject.objects.select_related('subject', 'class_level').get(
            school=self.school,
            subject__name='Religious and Moral Education',
            class_level__name='Basic 4',
        )
        term = create_active_term(self.school)
        teacher = create_user(
            phone_number='+233200111004',
            email='teacher-rme@test.com',
            school=self.school,
            role=User.RoleChoices.TEACHER,
            is_active=True,
        )
        TeachingAssignment.objects.create(
            teacher=teacher,
            class_subject=class_subject,
            term=term,
        )

        plan = plan_adoption(self.school)
        self.assertFalse(plan['up_to_date'])
        self.assertEqual(plan['applies_on'], 'next_term')
        self.assertTrue(any(change['action'] == 'preserve' for change in plan['changes']))

        scheduled = adopt(self.school)
        self.assertTrue(scheduled['scheduled'])
        self.school.refresh_from_db()
        self.assertNotEqual(self.school.provisioned_curriculum.version, '2025')
        self.assertEqual(self.school.accepted_curriculum.version, '2025')

        apply_accepted_curriculum(self.school)
        self.school.refresh_from_db()
        self.assertEqual(self.school.provisioned_curriculum.version, '2025')
        self.assertTrue(
            Subject.objects.filter(
                school=self.school,
                name='Religious and Moral Education',
            ).exists(),
        )
        religion = Subject.objects.get(school=self.school, name='Religion')
        self.assertTrue(
            LevelSubject.objects.filter(
                school=self.school,
                subject=religion,
                is_system_generated=True,
                is_active=True,
            ).exists(),
        )
        historical = LevelSubject.objects.get(
            school=self.school,
            subject__name='Religious and Moral Education',
            level__name='Upper Primary',
        )
        self.assertFalse(historical.is_system_generated)
        self.assertIsNone(historical.curriculum_subject_id)

    def test_school_admin_can_read_the_adoption_plan(self):
        draft = start_draft()
        save_draft(draft['id'], version=draft['version'], levels=draft['levels'])
        publish_draft(draft['id'])
        admin = create_user(
            phone_number='+233200111005',
            email='school-admin@test.com',
            school=self.school,
            is_active=True,
        )
        set_client_auth_cookies(self.client, admin, school=self.school)

        response = self.client.get(reverse('school-curriculum-adoption'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['up_to_date'])
        self.assertEqual(user_school(admin).id, self.school.id)

    def test_shared_class_subjects_are_not_listed_as_new(self):
        from django.core import mail

        self.school.email = 'office@coding.test'
        self.school.save(update_fields=['email', 'updated_at'])
        draft = start_draft()
        for level in draft['levels']:
            if level['name'] == 'Junior High School':
                level['subjects'].append({'lineage_id': '', 'name': 'Trums'})
        save_draft(draft['id'], version='2025', levels=draft['levels'])
        publish_draft(draft['id'])

        plan = plan_adoption(self.school)
        summaries = [change['summary'] for change in plan['changes']]
        self.assertTrue(any('Trums' in summary for summary in summaries))
        self.assertFalse(any('Creative Activities' in summary for summary in summaries))
        self.assertFalse(any('Pre-Literacy' in summary for summary in summaries))
        self.assertFalse(any('Pre-Numeracy' in summary for summary in summaries))
        self.assertFalse(any('Environmental' in summary for summary in summaries))
        self.assertTrue(mail.outbox)
        self.assertIn('office@coding.test', mail.outbox[0].to)
        self.assertIn('2025', mail.outbox[0].subject)
        self.assertIn('next term', mail.outbox[0].body)
