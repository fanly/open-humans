from io import StringIO
import unittest

from allauth.account.models import EmailAddress, EmailConfirmation

from django.conf import settings
from django.contrib import auth
from django.core import mail, management
from django.db import IntegrityError
from django.test import TestCase
from django.test.utils import override_settings
from django.urls import reverse
from django.utils import timezone

from rest_framework.test import APITestCase

from mock import patch

from common.testing import BrowserTestCase, get_or_create_user, SmokeTestCase
from private_sharing.models import DataRequestProject

from .models import Member

UserModel = auth.get_user_model()


class SmokeTests(SmokeTestCase):
    """
    A simple GET test for all of the simple URLs in the site.
    """

    anonymous_urls = ["/account/login/", "/account/password/reset/", "/account/signup/"]

    authenticated_or_anonymous_urls = [
        "/",
        "/about/",
        "/activity/favorite-trance-tracks/",
        "/activity/groovy-music/",
        "/api/public/datafiles/",
        "/api/public/datatypes/",
        "/api/public/members/",
        "/api/public/projects/",
        "/api/public-data/?username=beau",
        "/api/public-data/?created_start=2/14/2016&created_end=2/14/2016",
        "/api/public-data/sources-by-member/",
        "/api/public-data/members-by-source/",
        "/beau/",
        "/community-guidelines/",
        "/contact-us/",
        "/copyright/",
        "/data-use/",
        "/member/beau/",
        "/members/",
        "/members/page/1/",
        "/members/?sort=username",
        "/members/page/1/?sort=username",
        "/public-data/",
        "/public-data-api/",
        "/news/",
        "/create/",
        "/terms/",
        "/gdpr/",
    ]

    redirect_urls = [
        "/account/delete/",
        "/member/beau/email/",
        "/member/me/",
        "/member/me/account-settings/",
        "/member/me/change-email/",
        "/member/me/change-name/",
        "/member/me/connections/",
        # '/member/me/connections/delete/1/',
        "/member/me/edit/",
        "/member/me/joined/",
        "/member/me/data/",
        "/member/me/research-data/delete/pgp/",
        "/member/me/research-data/delete/american_gut/",
        "/member/me/research-data/delete/runkeeper/",
        "/member/me/send-confirmation-email/",
        "/public-data/activate-1-overview/",
        "/public-data/activate-2-information/",
        # require a POST
        # '/public-data/activate-3-quiz/',
        # '/public-data/activate-4-signature/',
        # 301 redirect
        # '/public-data/toggle-sharing/',
        "/public-data/deactivate/",
    ]

    authenticated_urls = redirect_urls + [
        "/account/password/",
        (
            "/oauth2/authorize/?origin=external&response_type=code"
            "&scope=go-viral%20read%20write&client_id=example-id-15"
        ),
    ]

    def test_custom_404(self):
        self.assert_status_code("/does-not-exist/", status_code=404)

    def test_custom_500(self):
        with self.assertRaises(Exception):
            self.assert_status_code("/raise-exception/", status_code=500)


@override_settings(SSLIFY_DISABLE=True)
class OpenHumansUserTests(TestCase):
    """
    Tests for our custom User class.
    """

    fixtures = ["open_humans/fixtures/test-data.json"]

    def setUp(self):  # noqa
        get_or_create_user("user1")

    def test_lookup_by_username(self):
        user1 = auth.authenticate(username="user1", password="user1")

        self.assertEqual(user1.username, "user1")

    def test_lookup_by_email(self):
        user1 = auth.authenticate(username="user1@test.com", password="user1")

        self.assertEqual(user1.username, "user1")

    def test_redirect_on_login(self):
        """
        Redirect to previous page on login.
        """
        first_redirect = "/"
        first_response = self.client.post(
            reverse("account_login"),
            {"next": first_redirect, "login": "chickens", "password": "asdfqwerty"},
        )
        self.assertEqual(first_response.status_code, 302)
        self.assertEqual(first_response.url, first_redirect)

        second_redirect = "/api/public-data/?source=direct-sharing-1"
        second_response = self.client.post(
            reverse("account_login"),
            {"next": second_redirect, "login": "chickens", "password": "asdfqwerty"},
        )
        self.assertEqual(second_response.status_code, 302)
        self.assertEqual(second_response.url, second_redirect)

    def test_password_reset(self):
        """
        Test that password reset works and that we we redirect to the proper
        place when a password reset is made.
        """

        redirect = "/"
        response_request_reset = self.client.post(
            reverse("account_reset_password"),
            {"next_t": redirect, "email": "froopla@borknorp.com"},
        )
        self.assertEqual(response_request_reset.status_code, 302)
        # We should now have mail in the outbox
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, "[Open Humans] Password Reset E-mail")
        reset_url = [
            item
            for item in mail.outbox[0].body.split("\n")
            if "account/password/reset/key" in item
        ][0]
        key = reset_url.split("/")[7]
        # Go ahead and reset the mailbox
        mail.outbox = []
        do_reset_response = self.client.get(reset_url)
        self.assertEqual(do_reset_response.status_code, 200)
        self.assertContains(do_reset_response, "Set your new password")

        do_reset_post_response = self.client.post(
            reset_url, {"password": "asdfqwerty", "password_confirm": "asdfqwerty"}
        )
        self.assertEqual(do_reset_post_response.status_code, 302)
        self.assertEqual(do_reset_post_response.url, redirect)

    def test_lowercase_unique(self):
        # Create a lowercase user2
        UserModel.objects.create_user("user2", "user2@test.com", "user2")

        # Creating an uppercase USER2 should fail
        self.assertRaises(
            IntegrityError,
            UserModel.objects.create_user,
            "USER2",
            "other+user2@test.com",
            "user2",
        )


@unittest.skip("The way the django-oauth model handles the primary key has changed")
class CommandTests(TestCase):
    """
    Tests for our management commands.
    """

    fixtures = ["open_humans/fixtures/test-data.json"]

    def setUp(self):
        self.output = StringIO()

    def test_bulk_email(self):
        try:
            import sys

            out, sys.stdout = sys.stdout, StringIO()
            management.call_command("bulk_email", "-h", stdout=self.output)
            sys.stdout = out
        except SystemExit as e:
            if e.code != 0:
                raise e

    def test_setup_api(self):
        management.call_command("setup_api", stdout=self.output)

    def test_update_badges(self):
        management.call_command("update_badges", stdout=self.output)

    def test_user_connections_json(self):
        management.call_command(
            "user_connections_json", "/dev/null", stdout=self.output
        )

    def test_stats(self):
        management.call_command("stats", "--days=365", stdout=self.output)


class WsgiTests(TestCase):
    """
    Tests for our WSGI application.
    """

    @staticmethod
    def test_import():
        from .wsgi import application  # noqa, pylint: disable=unused-variable


class WelcomeEmailTests(TestCase):
    """
    Tests for our welcome email.
    """

    @patch("open_humans.signals.send_mail")
    def test_send_welcome_email(self, mock):
        user = get_or_create_user("email_test_user")

        member = Member(user=user)
        member.save()

        email = user.emailaddress_set.all()[0]
        email.verified = False
        email.save()

        confirmation = EmailConfirmation.create(email)
        confirmation.sent = timezone.now()
        confirmation.save()

        # confirm the email; this sends the email_confirmed signals
        confirmed_email = confirmation.confirm(request=mock)

        self.assertTrue(confirmed_email is not None)
        self.assertTrue(mock.called)
        self.assertEqual(mock.call_count, 1)
        self.assertEqual(mock.call_args[0][-1][0], "email_test_user@test.com")


class OpenHumansBrowserTests(BrowserTestCase):
    """
    Browser tests of general Open Humans functionality.
    """

    @unittest.skipIf(settings.NOBROWSER, "skipping browser tests")
    def test_create_user(self):
        driver = self.driver

        driver.get(self.live_server_url)

        driver.find_element_by_class_name("signup-link").click()

        username = self.wait_for_element_id("signup-username")

        username.clear()
        username.send_keys("test_123")

        name = driver.find_element_by_id("signup-name")

        name.clear()
        name.send_keys("Test Testerson")

        email = driver.find_element_by_id("email-address")

        email.clear()
        email.send_keys("test@example.com")

        password = driver.find_element_by_id("signup-password")

        password.clear()
        password.send_keys("testing123")

        password_confirm = driver.find_element_by_id("signup-password-confirm")

        password_confirm.clear()
        password_confirm.send_keys("testing123")

        driver.find_element_by_name("terms").click()

        driver.find_element_by_id("create-account").click()

        self.assertEqual(
            "Please verify your email address.",
            driver.find_element_by_css_selector(
                ".call-to-action-3 > .container > h3"
            ).text,
        )

    @unittest.skipIf(settings.NOBROWSER, "skipping browser tests")
    def test_remove_connection(self):
        driver = self.driver

        self.login()

        driver.get(self.live_server_url + "/member/me/connections/")

        driver.find_element_by_xpath(
            "(//a[contains(text(),'Remove connection')])[1]"
        ).click()
        driver.find_element_by_name("remove_datafiles").click()
        driver.find_element_by_css_selector("label").click()
        driver.find_element_by_css_selector("input.btn.btn-danger").click()


@override_settings(SSLIFY_DISABLE=True)
class HidePublicMembershipTestCase(APITestCase):
    """
    Tests whether or not membership in public data activities is properly
    hidden when requested.
    """

    fixtures = ["open_humans/fixtures/test-data.json"]

    def test_public_api(self):
        """
        Tests the public API endpoints.
        """
        user = UserModel.objects.get(username="bacon")
        project = DataRequestProject.objects.get(id=1)
        project_member = project.active_user(user)

        project_member.set_visibility(visible_status=False)
        results = self.client.get("/api/public-data/members-by-source/").data["results"]
        result = {}
        for item in results:
            if item["source"] == "direct-sharing-1":
                result = item
        assert result["usernames"] == []

        project_member.set_visibility(visible_status=True)
        results = self.client.get("/api/public-data/members-by-source/").data["results"]
        result = {}
        for item in results:
            if item["source"] == "direct-sharing-1":
                result = item
        assert result["usernames"] == ["bacon"]
