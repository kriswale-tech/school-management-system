from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User
from accounts.tests.factories import create_user, set_client_auth_cookies, user_school
from activities.models import Activity
from activities.services import record_activity
from notifications.models import Notification
from notifications.services.emit import notify
from schools.tests.factories import create_active_term


class NotificationInboxAPITests(APITestCase):
    def setUp(self):
        self.admin = create_user(is_active=True, email='admin@test.com')
        self.school = user_school(self.admin)
        self.school.setup_completed = True
        self.school.save(update_fields=['setup_completed', 'updated_at'])
        self.term = create_active_term(self.school)
        self.admin_membership = self.admin.memberships.get(school=self.school)
        set_client_auth_cookies(self.client, self.admin)

        self.staff = create_user(
            phone_number='+233200000040',
            email='staff@test.com',
            school=self.school,
            role=User.RoleChoices.STAFF,
            is_active=True,
        )
        self.staff_membership = self.staff.memberships.get(school=self.school)

        self.list_url = reverse('notification-list')
        self.count_url = reverse('notification-unread-count')
        self.read_all_url = reverse('notification-read-all')

    def test_list_and_mark_read(self):
        row = notify(
            school=self.school,
            recipient=self.admin_membership,
            event_type=Notification.EventType.TERM_OPENED,
            title='New term opened',
            body='First Term is now active.',
            href='/dashboard',
        )
        self.assertIsNotNone(row)

        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['title'], 'New term opened')
        self.assertIsNone(response.data['results'][0]['read_at'])

        count = self.client.get(self.count_url)
        self.assertEqual(count.status_code, status.HTTP_200_OK)
        self.assertEqual(count.data['count'], 1)

        mark = self.client.post(
            reverse('notification-mark-read', kwargs={'notification_id': row.id}),
        )
        self.assertEqual(mark.status_code, status.HTTP_200_OK)
        self.assertIsNotNone(mark.data['read_at'])

        count = self.client.get(self.count_url)
        self.assertEqual(count.data['count'], 0)

    def test_mark_all_read(self):
        for index in range(2):
            notify(
                school=self.school,
                recipient=self.admin_membership,
                event_type=Notification.EventType.STUDENT_ENROLLED,
                title=f'Enrollment {index}',
                body='A student enrolled.',
            )

        response = self.client.post(self.read_all_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['updated'], 2)
        self.assertEqual(
            Notification.objects.filter(
                recipient=self.admin_membership,
                read_at__isnull=True,
            ).count(),
            0,
        )

    def test_inbox_is_membership_scoped(self):
        notify(
            school=self.school,
            recipient=self.staff_membership,
            event_type=Notification.EventType.MEMBER_INVITED,
            title='Added to school',
            body='Welcome.',
        )
        response = self.client.get(self.list_url)
        self.assertEqual(response.data['count'], 0)

        set_client_auth_cookies(self.client, self.staff, school=self.school)
        response = self.client.get(self.list_url)
        self.assertEqual(response.data['count'], 1)

    def test_record_activity_notifies_admins_on_enrollment(self):
        record_activity(
            school=self.school,
            actor=self.admin,
            verb=Activity.Verb.STUDENT_ENROLLED,
            summary='Ama enrolled in JHS 1.',
            href='/students/1',
            term=self.term,
            target_kind='student',
        )
        # Actor (admin) is skipped; staff still receives the enrollment notice.
        self.assertEqual(
            Notification.objects.filter(recipient=self.admin_membership).count(),
            0,
        )
        self.assertEqual(
            Notification.objects.filter(
                recipient=self.staff_membership,
                event_type=Notification.EventType.STUDENT_ENROLLED,
            ).count(),
            1,
        )

    def test_actor_does_not_notify_self(self):
        notify(
            school=self.school,
            recipient=self.admin_membership,
            event_type=Notification.EventType.MEMBER_UPDATED,
            title='Updated',
            body='You changed your own profile.',
            actor=self.admin,
        )
        self.assertEqual(Notification.objects.count(), 0)
