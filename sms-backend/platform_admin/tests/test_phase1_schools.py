from django.conf import settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import SchoolMembership, User
from accounts.tests.factories import create_school, create_user
from platform_admin.models import PlatformUser, SchoolAdminInvite
from platform_admin.services.settings import (
    clear_platform_settings_cache,
    get_platform_settings,
    update_platform_settings,
)
from schools.models import School


class PlatformPhase1SchoolTests(APITestCase):
    def setUp(self):
        clear_platform_settings_cache()
        self.ops = PlatformUser.objects.create_user(
            email='ops@schoolasst.test',
            password='SecurePass123!',
            role=PlatformUser.Role.SUPER_ADMIN,
        )
        login = self.client.post(
            reverse('platform-login'),
            {'email': 'ops@schoolasst.test', 'password': 'SecurePass123!'},
            format='json',
        )
        self.access_cookie = settings.PLATFORM_JWT['AUTH_COOKIE']
        self.client.cookies[self.access_cookie] = login.cookies[self.access_cookie].value

    def test_public_config(self):
        response = self.client.get(reverse('platform-public-config'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('public_school_registration_enabled', response.data)

    def test_create_school_pending_and_invite_accept(self):
        created = self.client.post(
            reverse('platform-school-list'),
            {
                'name': 'Platform Academy',
                'phone_number': '0244000001',
                'email': 'school@example.com',
                'region': 'Greater Accra',
                'category': 'primary',
            },
            format='json',
        )
        self.assertEqual(created.status_code, status.HTTP_201_CREATED)
        school_id = created.data['id']
        school = School.objects.get(pk=school_id)
        self.assertEqual(school.status, School.Status.PENDING)

        invite_resp = self.client.post(
            reverse('platform-school-invite-create', kwargs={'pk': school_id}),
            {
                'phone_number': '0244111222',
                'email': 'admin@example.com',
                'first_name': 'Ama',
                'last_name': 'Mensah',
            },
            format='json',
        )
        self.assertEqual(invite_resp.status_code, status.HTTP_201_CREATED)
        invite = SchoolAdminInvite.objects.get(pk=invite_resp.data['id'])

        preview = self.client.get(
            reverse('school-admin-invite-preview', kwargs={'token': invite.token}),
        )
        self.assertEqual(preview.status_code, status.HTTP_200_OK)
        self.assertEqual(preview.data['school_name'], 'Platform Academy')

        accept = self.client.post(
            reverse('school-admin-invite-accept', kwargs={'token': invite.token}),
            {},
            format='json',
        )
        self.assertEqual(accept.status_code, status.HTTP_200_OK)
        school.refresh_from_db()
        self.assertEqual(school.status, School.Status.ACTIVE)
        self.assertTrue(
            SchoolMembership.objects.filter(
                school=school,
                user__phone_number='0244111222',
                role=User.RoleChoices.ADMIN,
                is_active=True,
            ).exists(),
        )

    def test_create_school_starts_chosen_plan_and_addon(self):
        from decimal import Decimal

        from billing.models import InvoiceLine, SchoolSubscription
        from billing.services.catalog import seed_default_plans
        from communications.services.catalog import seed_default_skus

        seed_default_plans()
        seed_default_skus()
        created = self.client.post(
            reverse('platform-school-list'),
            {
                'name': 'Billed Academy',
                'phone_number': '0244000991',
                'email': 'billed@example.com',
                'region': 'Ashanti',
                'category': 'primary',
                'plan_code': 'starter',
                'interval': 'monthly',
                'sms_sku_code': 'sms_monthly_standard',
            },
            format='json',
        )
        self.assertEqual(created.status_code, status.HTTP_201_CREATED)
        subscription = SchoolSubscription.objects.get(
            school_id=created.data['id'],
            is_current=True,
        )
        self.assertEqual(subscription.plan.code, 'starter')
        self.assertEqual(subscription.interval, SchoolSubscription.Interval.MONTHLY)
        self.assertTrue(subscription.sms_addon_enabled)
        self.assertEqual(subscription.sms_sku.code, 'sms_monthly_standard')
        self.assertFalse(subscription.email_addon_enabled)
        invoice = subscription.invoices.get()
        self.assertEqual(invoice.total_ghs, Decimal('160.00'))
        self.assertTrue(invoice.lines.filter(kind=InvoiceLine.Kind.SMS_ADDON).exists())
        self.assertFalse(invoice.lines.filter(kind=InvoiceLine.Kind.DISCOUNT).exists())

        mismatch = self.client.post(
            reverse('platform-school-list'),
            {
                'name': 'Wrong Addon Academy',
                'phone_number': '0244000992',
                'plan_code': 'starter',
                'interval': 'monthly',
                'email_sku_code': 'email_annual_standard',
            },
            format='json',
        )
        self.assertEqual(mismatch.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email_sku_code', str(mismatch.data))

    def test_public_signup_blocked_when_flag_off(self):
        update_platform_settings(public_school_registration_enabled=False)
        response = self.client.post(
            reverse('admin-signup'),
            {
                'school_name': 'Blocked School',
                'first_name': 'Kojo',
                'last_name': 'Asante',
                'phone_number': '0244333444',
                'email': 'kojo@example.com',
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_suspended_school_not_selectable(self):
        from accounts.tests.factories import create_membership, set_client_auth_cookies

        school = create_school(name='Suspended School', phone_number='0244555666')
        school.status = School.Status.SUSPENDED
        school.save(update_fields=['status', 'updated_at'])
        user = create_user(phone_number='0244777888')
        create_membership(user, school, role=User.RoleChoices.ADMIN)

        school_client = self.client_class()
        set_client_auth_cookies(school_client, user, school=school, scoped=True)
        # Token may still have school claim; membership resolve should fail for APIs
        from accounts.services.memberships import get_active_membership

        self.assertIsNone(get_active_membership(user, school.id))


class ExistingSchoolMigrationSmokeTests(APITestCase):
    def test_create_school_factory_defaults_active(self):
        school = create_school(name='Legacy Active')
        self.assertEqual(school.status, School.Status.ACTIVE)


class SchoolDirectoryCountTests(APITestCase):
    def setUp(self):
        clear_platform_settings_cache()
        self.ops = PlatformUser.objects.create_user(
            email='counts@schoolasst.test',
            password='SecurePass123!',
            role=PlatformUser.Role.SUPER_ADMIN,
        )
        login = self.client.post(
            reverse('platform-login'),
            {'email': 'counts@schoolasst.test', 'password': 'SecurePass123!'},
            format='json',
        )
        self.client.cookies[settings.PLATFORM_JWT['AUTH_COOKIE']] = (
            login.cookies[settings.PLATFORM_JWT['AUTH_COOKIE']].value
        )

    def test_staff_count_not_inflated_by_students(self):
        from accounts.tests.factories import create_membership
        from students.tests.factories import create_student

        school = create_school(name='Count School', phone_number='0244000111')
        for index in range(4):
            user = User.objects.create(
                phone_number=f'0244111{100 + index}',
                email=f'staff{index}@test.com',
                first_name='Staff',
                last_name=str(index),
                is_active=True,
            )
            create_membership(user, school, is_active=True)
        for index in range(20):
            create_student(school=school, student_id=f'S{index:03d}')

        listed = self.client.get(reverse('platform-school-list'), {'search': 'Count School'})
        self.assertEqual(listed.status_code, status.HTTP_200_OK)
        row = next(item for item in listed.data['results'] if item['name'] == 'Count School')
        self.assertEqual(row['staff_count'], 4)
        self.assertEqual(row['student_count'], 20)
        # Guard against the old 4×20=80 inflation bug
        self.assertNotEqual(row['staff_count'], 80)

    def test_directory_row_plan_admin_and_overdue(self):
        from datetime import timedelta
        from decimal import Decimal

        from django.utils import timezone

        from accounts.tests.factories import create_user
        from billing.models import Invoice, Plan, SchoolSubscription
        from billing.services.catalog import seed_default_plans
        from billing.services.invoices import mark_invoice_paid
        from billing.services.subscriptions import start_subscription

        seed_default_plans()
        school = create_school(name='Billing Academy', phone_number='0244000222')
        create_user(
            school=school,
            phone_number='0244000333',
            email='ama@billing.test',
            first_name='Ama',
            last_name='Mensah',
            is_active=True,
        )
        plan = Plan.objects.get(code='starter')
        subscription = start_subscription(school=school, plan=plan)
        subscription.status = SchoolSubscription.Status.PAST_DUE
        subscription.save(update_fields=['status', 'updated_at'])

        quiet = create_school(name='Quiet Academy', phone_number='0244000444')

        listed = self.client.get(reverse('platform-school-list'), {'search': 'Academy'})
        self.assertEqual(listed.status_code, status.HTTP_200_OK)
        billing = next(item for item in listed.data['results'] if item['id'] == str(school.id))
        self.assertEqual(billing['plan_name'], 'Starter')
        self.assertEqual(billing['plan_code'], 'starter')
        self.assertEqual(billing['subscription_status'], SchoolSubscription.Status.PAST_DUE)
        self.assertEqual(billing['subscription_interval'], SchoolSubscription.Interval.ANNUAL)
        self.assertIsNotNone(billing['next_renewal_at'])
        self.assertTrue(billing['payment_overdue'])
        self.assertEqual(billing['admins'][0]['full_name'], 'Ama Mensah')
        self.assertEqual(billing['admins'][0]['phone_number'], '0244000333')
        self.assertEqual(billing['admins'][0]['email'], 'ama@billing.test')

        untouched = next(item for item in listed.data['results'] if item['id'] == str(quiet.id))
        self.assertIsNone(untouched['plan_name'])
        self.assertIsNone(untouched['next_renewal_at'])
        self.assertFalse(untouched['payment_overdue'])
        self.assertEqual(untouched['admins'], [])

        mark_invoice_paid(subscription.invoices.get())
        subscription.status = SchoolSubscription.Status.CANCELLED
        subscription.save(update_fields=['status', 'updated_at'])
        cancelled = self.client.get(reverse('platform-school-list'), {'search': 'Billing Academy'})
        cancelled_row = cancelled.data['results'][0]
        self.assertEqual(cancelled_row['plan_name'], 'Starter')
        self.assertIsNone(cancelled_row['next_renewal_at'])
        self.assertFalse(cancelled_row['payment_overdue'])

        Invoice.objects.create(
            school=school,
            subscription=subscription,
            status=Invoice.Status.OPEN,
            period_start=timezone.now() - timedelta(days=40),
            period_end=timezone.now() - timedelta(days=10),
            total_ghs=Decimal('100.00'),
            amount_paid_ghs=Decimal('0.00'),
            due_at=timezone.now() - timedelta(days=2),
        )
        overdue = self.client.get(reverse('platform-school-list'), {'search': 'Billing Academy'})
        self.assertTrue(overdue.data['results'][0]['payment_overdue'])

    def test_directory_summary_counts(self):
        from accounts.tests.factories import create_membership, create_user
        from billing.models import SchoolSubscription
        from billing.services.catalog import seed_default_plans
        from billing.services.subscriptions import start_subscription
        from students.tests.factories import create_student

        seed_default_plans()
        active = create_school(name='Summary Active', phone_number='0244000555')
        create_user(
            school=active,
            phone_number='0244000666',
            email='admin@summary.test',
            is_active=True,
        )
        create_student(school=active, student_id='SUM001')
        subscription = start_subscription(school=active)
        subscription.status = SchoolSubscription.Status.PAST_DUE
        subscription.save(update_fields=['status', 'updated_at'])

        pending = create_school(name='Summary Pending', phone_number='0244000777')
        pending.status = School.Status.PENDING
        pending.save(update_fields=['status', 'updated_at'])
        teacher = User.objects.create(
            phone_number='0244000888',
            email='teacher@summary.test',
            first_name='Yaw',
            last_name='Boateng',
            is_active=True,
        )
        create_membership(teacher, pending, role=User.RoleChoices.TEACHER)

        summary = self.client.get(reverse('platform-school-summary'))
        self.assertEqual(summary.status_code, status.HTTP_200_OK)
        self.assertEqual(summary.data['school_count'], 2)
        self.assertEqual(summary.data['active_school_count'], 1)
        self.assertEqual(summary.data['student_count'], 1)
        self.assertEqual(summary.data['staff_count'], 2)
        self.assertEqual(summary.data['overdue_school_count'], 1)
