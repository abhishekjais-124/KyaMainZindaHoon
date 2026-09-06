from datetime import datetime, timedelta, timezone as datetime_timezone
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from .models import UserPartnerMappings


class ProfileStatusWindowTests(TestCase):
    def setUp(self):
        user = User.objects.create_user(username='status-test')
        self.checked_in_at = datetime(
            2026, 9, 6, 18, 0, tzinfo=datetime_timezone.utc
        )
        self.profile = user.profile
        self.profile.last_check_in = self.checked_in_at
        self.profile.save(update_fields=['last_check_in'])

    def assert_status_at(self, elapsed, *, warning, missing):
        with patch(
            'core.models.timezone.now',
            return_value=self.checked_in_at + elapsed,
        ):
            self.assertIs(self.profile.is_warning(), warning)
            self.assertIs(self.profile.is_missing(), missing)

    def test_crossing_midnight_does_not_end_active_window(self):
        self.assert_status_at(
            timedelta(hours=6),
            warning=False,
            missing=False,
        )

    def test_active_window_includes_the_full_first_24_hours(self):
        self.assert_status_at(
            timedelta(hours=24),
            warning=False,
            missing=False,
        )

    def test_warning_window_starts_after_24_hours(self):
        self.assert_status_at(
            timedelta(hours=24, microseconds=1),
            warning=True,
            missing=False,
        )

    def test_danger_window_starts_after_48_hours(self):
        self.assert_status_at(
            timedelta(hours=48, microseconds=1),
            warning=False,
            missing=True,
        )


class RelationMeterTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='relation-user',
            email='relation@example.com',
            password='test-pass',
        )
        self.friend = User.objects.create_user(
            username='relation-friend',
            email='friend@example.com',
        )
        self.user.profile.link_with(self.friend.profile)
        self.mapping = UserPartnerMappings.objects.get(
            user=self.user.profile,
            partner=self.friend.profile,
        )
        self.reverse_mapping = UserPartnerMappings.objects.get(
            user=self.friend.profile,
            partner=self.user.profile,
        )
        self.checked_in_at = datetime(
            2026, 9, 6, 18, 0, tzinfo=datetime_timezone.utc
        )
        self.user.profile.last_check_in = self.checked_in_at
        self.user.profile.save(update_fields=['last_check_in'])
        self.friend.profile.last_check_in = self.checked_in_at
        self.friend.profile.save(update_fields=['last_check_in'])

    def test_five_relation_points_map_from_12_to_48_hours(self):
        expected = [12, 18, 24, 36, 48]
        actual = [
            UserPartnerMappings.danger_hours_for_level(level)
            for level in range(1, 6)
        ]
        self.assertEqual(actual, expected)

    def test_very_strong_changes_profile_warning_and_danger_windows(self):
        self.mapping.relation_level = (
            UserPartnerMappings.RelationLevel.VERY_STRONG
        )
        self.mapping.save(update_fields=['relation_level'])

        self.assertEqual(self.user.profile.danger_hours, 12)
        self.assertEqual(self.user.profile.warning_hours, 6)
        with patch(
            'core.models.timezone.now',
            return_value=self.checked_in_at + timedelta(hours=6, microseconds=1),
        ):
            self.assertTrue(self.user.profile.is_warning())
            self.assertFalse(self.user.profile.is_missing())
        with patch(
            'core.models.timezone.now',
            return_value=self.checked_in_at + timedelta(hours=12, microseconds=1),
        ):
            self.assertFalse(self.user.profile.is_warning())
            self.assertTrue(self.user.profile.is_missing())

    def test_connection_status_uses_its_relation_window(self):
        self.mapping.relation_level = UserPartnerMappings.RelationLevel.STRONG
        self.mapping.save(update_fields=['relation_level'])
        with patch(
            'core.models.timezone.now',
            return_value=self.checked_in_at + timedelta(hours=11),
        ):
            self.assertTrue(self.mapping.is_warning())
            self.assertFalse(self.mapping.is_missing())
        with patch(
            'core.models.timezone.now',
            return_value=self.checked_in_at + timedelta(hours=22),
        ):
            self.assertFalse(self.mapping.is_warning())
            self.assertTrue(self.mapping.is_missing())

    def test_relation_endpoint_updates_both_sides(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse('friends_save_relation'),
            data={
                'mapping_id': self.mapping.id,
                'relation_level': (
                    UserPartnerMappings.RelationLevel.VERY_STRONG
                ),
            },
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        self.mapping.refresh_from_db()
        self.reverse_mapping.refresh_from_db()
        self.assertEqual(
            self.mapping.relation_level,
            UserPartnerMappings.RelationLevel.VERY_STRONG,
        )
        self.assertEqual(
            self.reverse_mapping.relation_level,
            UserPartnerMappings.RelationLevel.VERY_STRONG,
        )
        self.assertEqual(response.json()['danger_hours'], 12)

    def test_relation_meter_renders_on_friends_and_dashboard(self):
        self.client.force_login(self.user)

        friends_response = self.client.get(reverse('friends'))
        dashboard_response = self.client.get(reverse('dashboard'))

        self.assertEqual(friends_response.status_code, 200)
        self.assertContains(friends_response, 'Relationship meter')
        self.assertEqual(dashboard_response.status_code, 200)
        self.assertContains(dashboard_response, '48:00:00')

    @patch('core.management.commands.check_heartbeats.send_heartbeat_alert')
    def test_heartbeat_command_alerts_each_connection_at_its_limit(
        self,
        send_alert,
    ):
        send_alert.return_value = True
        self.mapping.relation_level = (
            UserPartnerMappings.RelationLevel.VERY_STRONG
        )
        self.mapping.save(update_fields=['relation_level'])
        now = self.checked_in_at + timedelta(hours=13)

        with patch(
            'core.management.commands.check_heartbeats.timezone.now',
            return_value=now,
        ):
            call_command('check_heartbeats')

        send_alert.assert_called_once_with(
            self.user.profile,
            self.friend.profile,
        )
        self.mapping.refresh_from_db()
        self.assertTrue(self.mapping.heartbeat_alert_sent)
