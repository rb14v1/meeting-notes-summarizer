from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User
from common.test_utils import auth_client, create_user


class RegistrationTests(APITestCase):
    def test_registration_creates_user(self):
        url = reverse("auth-register")
        response = self.client.post(url, {
            "email": "newuser@example.com",
            "password": "StrongPass123!",
            "full_name": "New User",
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertTrue(User.objects.filter(email="newuser@example.com").exists())

    def test_new_registration_defaults_to_member_role(self):
        url = reverse("auth-register")
        response = self.client.post(url, {
            "email": "defaultrole@example.com",
            "password": "StrongPass123!",
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        user = User.objects.get(email="defaultrole@example.com")
        self.assertEqual(user.role, User.Role.MEMBER)

    def test_weak_password_rejected(self):
        url = reverse("auth-register")
        response = self.client.post(url, {
            "email": "weak@example.com",
            "password": "123",
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_duplicate_email_rejected(self):
        create_user(email="dup@example.com")
        url = reverse("auth-register")
        response = self.client.post(url, {
            "email": "dup@example.com",
            "password": "StrongPass123!",
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class LoginAndMeTests(APITestCase):
    def setUp(self):
        self.user = create_user(email="u1@example.com", password="StrongPass123!", full_name="U One")

    def test_login_returns_tokens(self):
        url = reverse("auth-login")
        response = self.client.post(url, {"email": "u1@example.com", "password": "StrongPass123!"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    def test_login_with_wrong_password_rejected(self):
        url = reverse("auth-login")
        response = self.client.post(url, {"email": "u1@example.com", "password": "WrongPass!"})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_me_endpoint(self):
        client = auth_client(self.user)
        response = client.get(reverse("users-me"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["email"], "u1@example.com")
        self.assertEqual(response.data["full_name"], "U One")
        self.assertEqual(response.data["role"], "member")

    def test_me_requires_authentication(self):
        response = self.client.get(reverse("users-me"))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_logout_blacklists_refresh_token(self):
        login_response = self.client.post(reverse("auth-login"), {"email": "u1@example.com", "password": "StrongPass123!"})
        refresh = login_response.data["refresh"]
        client = auth_client(self.user)
        logout_response = client.post(reverse("auth-logout"), {"refresh": refresh})
        self.assertEqual(logout_response.status_code, status.HTTP_205_RESET_CONTENT)

        refresh_response = self.client.post(reverse("auth-refresh"), {"refresh": refresh})
        self.assertEqual(refresh_response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_refresh_rotation_issues_new_tokens(self):
        login_response = self.client.post(reverse("auth-login"), {"email": "u1@example.com", "password": "StrongPass123!"})
        refresh = login_response.data["refresh"]
        refresh_response = self.client.post(reverse("auth-refresh"), {"refresh": refresh})
        self.assertEqual(refresh_response.status_code, status.HTTP_200_OK)
        self.assertIn("access", refresh_response.data)


class AdminRoleTests(APITestCase):
    def test_admin_user_can_be_created_directly(self):
        admin = User.objects.create_user(email="admin-direct@example.com", password="StrongPass123!", role=User.Role.ADMIN)
        self.assertTrue(admin.is_admin)
        client = auth_client(admin)
        response = client.get(reverse("users-me"))
        self.assertEqual(response.data["role"], "admin")
