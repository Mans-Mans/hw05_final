from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.test import Client, TestCase

User = get_user_model()


class AboutUrlTests(TestCase):
    def setUp(self):
        self.guest_client = Client()

    def test_url_exists(self):
        """Проверка доступности страниц."""
        url_names_clients = {
            '/about/author/': self.guest_client,
            '/about/tech/': self.guest_client,
        }
        for address, client in url_names_clients.items():
            with self.subTest(address=address):
                response = client.get(address)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_urls_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        url_names_templates = {
            '/about/author/': 'about/author.html',
            '/about/tech/': 'about/tech.html',
        }
        for address, template in url_names_templates.items():
            with self.subTest(address=address):
                response = self.guest_client.get(address)
                self.assertTemplateUsed(response, template)
