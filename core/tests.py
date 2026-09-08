from datetime import datetime, timedelta, timezone as datetime_timezone
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

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


class SosTriggerTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='sos-user',
            email='sos@example.com',
            password='test-pass',
        )
        self.friend = User.objects.create_user(
            username='sos-friend',
            email='sos-friend@example.com',
        )
        self.user.profile.link_with(self.friend.profile)
        self.mapping = UserPartnerMappings.objects.get(
            user=self.user.profile,
            partner=self.friend.profile,
        )
        self.mapping.is_emergency = True
        self.mapping.save(update_fields=['is_emergency'])
        self.old_check_in = datetime(
            2026, 9, 1, 12, 0, tzinfo=datetime_timezone.utc
        )
        self.user.profile.last_check_in = self.old_check_in
        self.user.profile.share_location_in_sos = False
        self.user.profile.save(
            update_fields=['last_check_in', 'share_location_in_sos']
        )
        self.client.force_login(self.user)

    @patch('core.views.run_in_background')
    def test_sos_trigger_marks_check_in(self, _background):
        before = self.user.profile.last_check_in
        response = self.client.post(
            reverse('sos_trigger'),
            data='{}',
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['success'])
        self.user.profile.refresh_from_db()
        self.assertGreater(self.user.profile.last_check_in, before)
        self.assertIn('checked_in_at', response.json())

    @patch('core.views.run_in_background')
    def test_sos_ignores_location_when_setting_off(self, _background):
        response = self.client.post(
            reverse('sos_trigger'),
            data='{"lat": 12.97, "lng": 77.59}',
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        self.user.profile.refresh_from_db()
        self.assertFalse(self.user.profile.share_location_in_sos)
        self.assertIsNone(self.user.profile.last_latitude)
        self.assertIsNone(self.user.profile.last_longitude)

    @patch('core.views.run_in_background')
    def test_sos_stores_location_when_setting_on(self, background):
        self.user.profile.share_location_in_sos = True
        self.user.profile.save(update_fields=['share_location_in_sos'])
        response = self.client.post(
            reverse('sos_trigger'),
            data='{"lat": 12.97, "lng": 77.59}',
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        self.user.profile.refresh_from_db()
        self.assertAlmostEqual(self.user.profile.last_latitude, 12.97)
        self.assertAlmostEqual(self.user.profile.last_longitude, 77.59)
        self.assertIsNotNone(self.user.profile.location_updated_at)
        background.assert_called()


class AutoCheckinSettingTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='auto-user',
            email='auto@example.com',
            password='test-pass',
        )
        self.friend = User.objects.create_user(
            username='auto-friend',
            email='auto-friend@example.com',
        )
        self.user.profile.link_with(self.friend.profile)
        self.client.force_login(self.user)

    def test_auto_checkin_defaults_to_false(self):
        self.assertFalse(self.user.profile.auto_checkin_on_warning_danger)

    def test_settings_can_enable_auto_checkin(self):
        response = self.client.post(
            reverse('settings'),
            data='{"auto_checkin_on_warning_danger": true}',
            content_type='application/json',
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['success'])
        self.assertTrue(response.json()['auto_checkin_on_warning_danger'])
        self.user.profile.refresh_from_db()
        self.assertTrue(self.user.profile.auto_checkin_on_warning_danger)

    def test_dashboard_auto_checks_in_when_warning_and_enabled(self):
        profile = self.user.profile
        profile.auto_checkin_on_warning_danger = True
        # Mid warning window for default 48h danger / 24h warning
        profile.last_check_in = timezone.now() - timedelta(hours=30)
        profile.save(
            update_fields=['auto_checkin_on_warning_danger', 'last_check_in']
        )
        before = profile.last_check_in

        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['auto_checked_in'])
        self.assertEqual(response.context['auto_checkin_state'], 'warning')
        self.assertFalse(response.context['is_warning'])
        self.assertFalse(response.context['is_missing'])
        profile.refresh_from_db()
        self.assertGreater(profile.last_check_in, before)
        self.assertContains(response, 'Auto checked in')

    def test_dashboard_auto_checks_in_when_danger_and_enabled(self):
        profile = self.user.profile
        profile.auto_checkin_on_warning_danger = True
        profile.last_check_in = timezone.now() - timedelta(hours=50)
        profile.save(
            update_fields=['auto_checkin_on_warning_danger', 'last_check_in']
        )
        before = profile.last_check_in

        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['auto_checked_in'])
        self.assertEqual(response.context['auto_checkin_state'], 'danger')
        profile.refresh_from_db()
        self.assertGreater(profile.last_check_in, before)

    def test_dashboard_skips_auto_checkin_when_disabled(self):
        profile = self.user.profile
        profile.auto_checkin_on_warning_danger = False
        profile.last_check_in = timezone.now() - timedelta(hours=30)
        profile.save(
            update_fields=['auto_checkin_on_warning_danger', 'last_check_in']
        )
        before = profile.last_check_in

        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context['auto_checked_in'])
        self.assertTrue(response.context['is_warning'])
        profile.refresh_from_db()
        self.assertEqual(profile.last_check_in, before)

    def test_dashboard_skips_auto_checkin_when_snoozed(self):
        profile = self.user.profile
        profile.auto_checkin_on_warning_danger = True
        profile.snooze_enabled = True
        profile.last_check_in = timezone.now() - timedelta(hours=50)
        profile.save(
            update_fields=[
                'auto_checkin_on_warning_danger',
                'snooze_enabled',
                'last_check_in',
            ]
        )
        before = profile.last_check_in

        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context['auto_checked_in'])
        profile.refresh_from_db()
        self.assertEqual(profile.last_check_in, before)

    def test_auto_checkin_on_open_endpoint(self):
        profile = self.user.profile
        profile.auto_checkin_on_warning_danger = True
        profile.last_check_in = timezone.now() - timedelta(hours=30)
        profile.save(
            update_fields=['auto_checkin_on_warning_danger', 'last_check_in']
        )
        before = profile.last_check_in

        response = self.client.post(reverse('auto_checkin_on_open'))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['checked_in'])
        self.assertEqual(data['state'], 'warning')
        self.assertIn('Auto checked in', data['message'])
        profile.refresh_from_db()
        self.assertGreater(profile.last_check_in, before)

    def test_auto_checkin_on_open_noop_when_ok(self):
        profile = self.user.profile
        profile.auto_checkin_on_warning_danger = True
        profile.last_check_in = timezone.now()
        profile.save(
            update_fields=['auto_checkin_on_warning_danger', 'last_check_in']
        )
        before = profile.last_check_in

        response = self.client.post(reverse('auto_checkin_on_open'))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertFalse(data['checked_in'])
        self.assertEqual(data['reason'], 'ok')
        profile.refresh_from_db()
        self.assertEqual(profile.last_check_in, before)
