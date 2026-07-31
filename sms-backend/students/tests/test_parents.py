from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.tests.factories import create_user, set_client_auth_cookies, user_school
from students.models import Parent


class ParentListViewTests(APITestCase):
    def setUp(self):
        self.user = create_user(is_active=True)
        set_client_auth_cookies(self.client, self.user)
        self.school = user_school(self.user)
        self.url = reverse('parent-list')

        self.parent_a = Parent.objects.create(
            school=self.school,
            name='Akosua Mensah',
            phone_number='+233244111222',
            email='akosua@example.com',
        )
        self.parent_b = Parent.objects.create(
            school=self.school,
            name='Kwame Boateng',
            phone_number='+233244333444',
            email='',
        )

        other_user = create_user(
            is_active=True,
            email='other@example.com',
            phone_number='+233200000099',
        )
        other_school = user_school(other_user)
        Parent.objects.create(
            school=other_school,
            name='Other School Parent',
            phone_number='+233200000001',
        )

    def test_lists_parents_for_school(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 2)
        names = [item['name'] for item in response.data['results']]
        self.assertEqual(names, ['Akosua Mensah', 'Kwame Boateng'])
        self.assertEqual(response.data['results'][0]['id'], str(self.parent_a.id))
        self.assertEqual(response.data['results'][0]['phone_number'], '+233244111222')

    def test_search_filters_parents(self):
        response = self.client.get(self.url, {'search': 'kwame'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['id'], str(self.parent_b.id))
