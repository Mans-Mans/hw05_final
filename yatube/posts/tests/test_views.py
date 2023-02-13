import shutil
import tempfile

from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from ..models import Follow, Group, Post

User = get_user_model()

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostPagesTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create_user(username='author')
        cls.authorized = User.objects.create_user(username='JustAuthorized')
        cls.follower = User.objects.create_user(username='follower')
        cls.small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        cls.uploaded = SimpleUploadedFile(
            name='small.gif',
            content=cls.small_gif,
            content_type='image/gif'
        )
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
            image=cls.uploaded,
        )
        cls.follow = Follow.objects.create(
            user=cls.follower,
            author=cls.post.author,
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.author = Client()
        self.author.force_login(PostPagesTests.post.author)
        self.authorized_client = Client()
        self.authorized_client.force_login(self.authorized)
        self.follower = Client()
        self.follower.force_login(PostPagesTests.follow.user)

    def test_pages_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        pages_names_templates = {
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
            reverse('posts:post_create'): 'posts/create_post.html',
            reverse('posts:post_edit',
                    kwargs={'post_id': self.post.pk}
                    ): 'posts/create_post.html',
        }
        for reverse_name, template in pages_names_templates.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.author.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def test_index_page_show_correct_context(self):
        """Шаблон index сформирован с правильным контекстом."""
        response = self.author.get(reverse('posts:index'))
        self.assertEqual(response.context.get('post').text, self.post.text)
        self.assertEqual(response.context.get('post').group, self.post.group)
        self.assertEqual(response.context.get('post').author, self.post.author)

    def test_group_list_pages_show_correct_context(self):
        """Шаблон group_list сформирован с правильным контекстом."""
        response = (self.author.
                    get(reverse('posts:group_list',
                        kwargs={'slug': self.group.slug})))
        expected = list(Post.objects.filter(group_id=self.group.id)[:10])
        self.assertEqual(list(response.context['page_obj']), expected)

    def test_profile_pages_show_correct_context(self):
        """Шаблон profile сформирован с правильным контекстом."""
        response = (self.author.
                    get(reverse('posts:profile',
                        kwargs={'username': self.post.author})))
        expected = list(Post.objects.
                        filter(author_id=self.post.author.id))[:10]
        self.assertEqual(list(response.context['page_obj']), expected)

    def test_post_detail_pages_show_correct_context(self):
        """Шаблон post_detail сформирован с правильным контекстом."""
        response = (self.author.
                    get(reverse('posts:post_detail',
                        kwargs={'post_id': self.post.pk})))
        expected = Post.objects.get(id=self.post.pk)
        self.assertEqual(response.context.get('posts'), expected)

    def test_create_post_pages_show_correct_context(self):
        """Шаблон create_post сформирован с правильным контекстом."""
        response = self.author.get(reverse('posts:post_create'))
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context['form'].fields[value]
                self.assertIsInstance(form_field, expected)

    def test_create_post_edit_pages_show_correct_context(self):
        """Шаблон create_post_edit сформирован с правильным контекстом."""
        response = (self.author.
                    get(reverse('posts:post_edit',
                        kwargs={'post_id': self.post.pk})))
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context['form'].fields[value]
                self.assertIsInstance(form_field, expected)

    def test_page_for_group_post(self):
        """Проверка на появление поста на нужных страницах."""
        cache.clear()
        pages = [
            reverse('posts:index'),
            reverse('posts:group_list', kwargs={'slug': self.group.slug}),
            reverse('posts:profile', kwargs={'username': self.post.author})
        ]
        for page in pages:
            with self.subTest(page=page):
                response = self.author.get(page)
                response_context = response.context['page_obj']
                self.assertIn(self.post, response_context)

    def test_index_page_show_correct_context(self):
        """Проверка вывода картинки в context на старницу index"""
        cache.clear()
        response = self.author.get(reverse('posts:index'))
        expected = list(Post.objects.filter(image=self.post.image))
        self.assertEqual(list(response.context['page_obj']), expected)

    def test_group_list_page_show_correct_context(self):
        """Проверка вывода картинки в
        context на старницу group_list"""
        response = self.author.get(reverse('posts:group_list',
                                           kwargs={'slug': self.group.slug}))
        expected = list(Post.objects.filter(image=self.post.image))
        self.assertEqual(list(response.context['page_obj']), expected)

    def test_profile_page_show_correct_context(self):
        """Проверка вывода картинки в context на старницу profile"""
        response = self.author.get(reverse(
                                   'posts:profile',
                                   kwargs={'username': self.post.author}))
        expected = list(Post.objects.filter(image=self.post.image))
        self.assertEqual(list(response.context['page_obj']), expected)

    def test_post_detail_page_show_correct_context(self):
        """Проверка вывода картинки в context на старницу post_detail"""
        response = self.author.get(reverse(
                                   'posts:post_detail',
                                   kwargs={'post_id': self.post.pk}))
        expected = Post.objects.get(image=self.post.image)
        self.assertEqual(response.context.get('posts'), expected)

    def test_index_page_have_cache(self):
        """Проверка работы кэша."""
        response = self.author.get(reverse('posts:index'))
        response_before_del = response.content
        Post.objects.all().delete()
        response_2 = self.author.get(reverse('posts:index'))
        response_after_del = response_2.content
        self.assertEqual(len(response_before_del), len(response_after_del))
        cache.clear()
        response_3 = self.author.get(reverse('posts:index'))
        response_after_cahce_clear = response_3.content
        self.assertNotEqual(len(response_before_del),
                            len(response_after_cahce_clear))

    def test_page_follow(self):
        """Проверка работы подписки:
        редирект и создание."""
        follow_count = Follow.objects.all().count()
        response = self.authorized_client.get(
            reverse('posts:profile_follow',
                    kwargs={'username': self.post.author}),)
        self.assertRedirects(
            response, reverse(
                'posts:profile', kwargs={'username': self.post.author}
            )
        )
        self.assertEqual(Follow.objects.count(), follow_count + 1)

    def test_page_unfollow(self):
        """Проверка работы отписки:
        редирект и удаление."""
        response_add_follow = self.follower.get(
            reverse('posts:profile_follow',
                    kwargs={'username': self.post.author}),)
        self.assertRedirects(
            response_add_follow, reverse(
                'posts:profile', kwargs={'username': self.post.author}
            )
        )
        follow_count = Follow.objects.all().count()
        response = self.follower.get(
            reverse('posts:profile_unfollow',
                    kwargs={'username': self.post.author}))
        self.assertRedirects(
            response, reverse(
                'posts:profile', kwargs={'username': self.post.author}
            )
        )
        self.assertEqual(Follow.objects.count(), follow_count - 1)


class PaginatorViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='HasNoName')
        cls.group = Group.objects.create(
            title='Тест',
            slug='test',
            description='Описание',
        )
        for i in range(15):
            cls.post = Post.objects.create(
                author=cls.user,
                text='Тестовый пост {i}',
                group=cls.group,
                id=1 + i,
            )

    def setUp(self):
        self.author = Client()
        self.author.force_login(PaginatorViewsTest.post.author)

    def test_paginator(self):
        """Проверка работы паджинатора."""
        cache.clear()
        reverse_name_post_count = {
            reverse('posts:index'): 10,
            reverse('posts:index') + '?page=2': 5,
            reverse('posts:group_list',
                    kwargs={'slug': self.group.slug}): 10,
            reverse('posts:group_list',
                    kwargs={'slug': self.group.slug}) + '?page=2': 5,
            reverse('posts:profile',
                    kwargs={'username': self.post.author}): 10,
            reverse('posts:profile',
                    kwargs={'username': self.post.author}) + '?page=2': 5,
        }
        for reverse_name, post_count in reverse_name_post_count.items():
            response = self.author.get(reverse_name)
            self.assertEqual(len(response.context['page_obj']), post_count)
