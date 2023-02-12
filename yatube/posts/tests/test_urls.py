from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import Client, TestCase
from django.urls import reverse

from ..models import Group, Post

User = get_user_model()


class StaticURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create_user(username='Author')
        cls.authorized = User.objects.create_user(username='JustAuthorized')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.author,
            text='Тестовый пост',
            group=cls.group,
            id=1,
        )

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.authorized)
        self.author = Client()
        self.author.force_login(StaticURLTests.post.author)

    def test_url_exists(self):
        """Проверка доступности страниц для автора,
        авторизованных и неавторизованных пользователей"""
        url_names_clients = {
            reverse('posts:index'): self.guest_client,
            reverse('posts:group_list',
                    kwargs={'slug': self.post.group.slug}
                    ): self.guest_client,
            reverse('posts:profile',
                    kwargs={'username': self.post.author}
                    ): self.guest_client,
            reverse('posts:post_detail',
                    kwargs={'post_id': self.post.pk}
                    ): self.guest_client,
            reverse('posts:post_edit',
                    kwargs={'post_id': self.post.pk}
                    ): self.author,
            reverse('posts:post_create'): self.authorized_client,
        }
        for address, client in url_names_clients.items():
            with self.subTest(address=address):
                response = client.get(address)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_url_redirect(self):
        """Проверка редиректов для авторизованного,
        неавторизованного пользователя."""
        url_name_client = {
            reverse('posts:post_create'): self.guest_client,
            reverse('posts:post_edit',
                    kwargs={'post_id': self.post.pk}
                    ): self.authorized_client,
        }
        for address, client in url_name_client.items():
            with self.subTest(address=address):
                response = client.get(address)
                self.assertEqual(response.status_code, HTTPStatus.FOUND)

    def test_url_page_not_found(self):
        """Проверка ошибки для несуществующей страницы"""
        response = self.guest_client.get('unexisting_page')
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_urls_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        cache.clear()
        url_names_templates = {
            reverse('posts:index'): 'posts/index.html',
            reverse('posts:group_list',
                    kwargs={'slug': self.post.group.slug}
                    ): 'posts/group_list.html',
            reverse('posts:profile',
                    kwargs={'username': self.post.author}
                    ): 'posts/profile.html',
            reverse('posts:post_detail',
                    kwargs={'post_id': self.post.pk}
                    ): 'posts/post_detail.html',
            reverse('posts:post_edit',
                    kwargs={'post_id': self.post.pk}
                    ): 'posts/create_post.html',
            reverse('posts:post_create'): 'posts/create_post.html',
        }
        for address, template in url_names_templates.items():
            with self.subTest(address=address):
                response = self.author.get(address)
                self.assertTemplateUsed(response, template)
