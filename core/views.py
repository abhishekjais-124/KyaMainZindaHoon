from django.views.decorators.http import require_GET, require_http_methods, require_POST
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth import login as auth_login
from datetime import timedelta
from allauth.account.forms import LoginForm, SignupForm
from allauth.account.utils import perform_login
from .models import Profile, UserPartnerMappings, SOSAlert, SOSResolvedNotification
from .utils import send_sos_via_emailjs
from django.utils import timezone
from django.http import JsonResponse
from django.db.models import Q


def _invite_link_response(request, profile, invite_code, success_redirect):
    """Shared invite-code friend add for friends/profile/link_partner views."""
    ok, message = Profile.link_by_invite_code(profile, invite_code)
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'success': ok, 'message': message})
    if ok:
        messages.success(request, message)
        return redirect(success_redirect)
    messages.error(request, message)
    return None


def alert_danger(request):
    return render(request, 'core/message_popup.html', {'message_title': 'Danger!', 'message_text': 'This is a danger alert.', 'message_type': 'danger'})


def alert_warning(request):
    return render(request, 'core/message_popup.html', {'message_title': 'Warning!', 'message_text': 'This is a warning alert.', 'message_type': 'warning'})

@login_required
def invite_code_popup(request):
    profile = request.user.profile
    if not profile.invite_code:
        from .models import generate_invite_code
        profile.invite_code = generate_invite_code()
        profile.save()
    return render(request, 'core/invite_code_popup.html', {'invite_code': profile.invite_code})

def loading_screen(request):
    return render(request, 'core/loading_screen.html')

@login_required
@require_GET
def get_invite_code(request):
    profile = request.user.profile
    if not profile.invite_code:
        from .models import generate_invite_code
        profile.invite_code = generate_invite_code()
        profile.save()
    return JsonResponse({'invite_code': profile.invite_code})

# Friends page view
@login_required
@require_http_methods(["GET", "POST"])
def friends_view(request):
    profile = request.user.profile
    # Handle invite code join
    if request.method == 'POST' and 'invite_code' in request.POST:
        response = _invite_link_response(
            request,
            profile,
            request.POST.get('invite_code', ''),
            success_redirect='friends',
        )
        if response is not None:
            return response

    # Handle delete mapping (AJAX)
    if request.method == 'POST' and 'delete_mapping' in request.POST:
        partner_email = request.POST.get('delete_mapping')
        try:
            partner_user = User.objects.get(email=partner_email)
            profile.unlink_from(partner_user.profile)
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'success': True, 'message': 'Connection deleted.'})
            messages.success(request, 'Connection deleted.')
            return redirect('friends')
        except User.DoesNotExist:
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'message': 'User not found.'})
            messages.error(request, 'User not found.')

    # Build connections list with emergency flag
    connections = []
    active_mappings = UserPartnerMappings.objects.filter(user=profile, is_active=True)
    for mapping in active_mappings:
        connections.append({
            'mapping_id': mapping.id,
            'user': mapping.partner.user,
            'is_emergency': mapping.is_emergency,
            'relation_level': mapping.relation_level,
            'relation_label': mapping.relation_label,
            'danger_hours': mapping.danger_hours,
            'warning_hours': mapping.warning_hours,
            'is_missing': mapping.is_missing(),
            'is_warning': mapping.is_warning(),
        })

    # Active SOS alerts received by this user (for "who triggered SOS" on friends page)
    def _display_name(u):
        name = (u.get_full_name() or '').strip()
        return name or u.username or u.email or 'Someone'

    def _location_str(p):
        parts = [x for x in (p.last_city, p.last_state) if x]
        return ', '.join(parts) if parts else None

    active_sos = SOSAlert.objects.filter(to_user=profile, status=SOSAlert.Status.ACTIVE).select_related('from_user', 'from_user__user')
    active_sos_alerts = []
    for a in active_sos:
        from_profile = a.from_user
        item = {
            'id': a.id,
            'from_name': _display_name(from_profile.user),
            'from_username': from_profile.user.username,
            'from_email': from_profile.user.email,
            'created_at': a.created_at,
            'location': _location_str(from_profile),
        }
        if from_profile.share_location_in_sos and from_profile.last_latitude is not None and from_profile.last_longitude is not None:
            item['lat'] = from_profile.last_latitude
            item['lng'] = from_profile.last_longitude
        active_sos_alerts.append(item)

    return render(request, 'core/friends.html', {
        'connections': connections,
        'active_sos_alerts': active_sos_alerts,
    })


@login_required
@require_POST
def friends_save_emergency(request):
    """Save which connections are marked as emergency. Expects JSON: { \"emergency_emails\": [\"a@b.com\", ...] }."""
    import json
    profile = request.user.profile
    try:
        data = json.loads(request.body)
        emergency_emails = set((data.get('emergency_emails') or []))
    except Exception:
        return JsonResponse({'success': False, 'message': 'Invalid request.'}, status=400)
    mappings = UserPartnerMappings.objects.filter(user=profile, is_active=True)
    for mapping in mappings:
        email = mapping.partner.user.email
        mapping.is_emergency = email in emergency_emails
        mapping.save(update_fields=['is_emergency'])
    return JsonResponse({'success': True, 'message': 'Emergency contacts saved.'})


@login_required
@require_POST
def friends_save_relation(request):
    """Save the shared relation meter for one active connection."""
    import json

    profile = request.user.profile
    try:
        data = json.loads(request.body)
        mapping_id = int(data.get('mapping_id'))
        relation_level = int(data.get('relation_level'))
        relation_choice = UserPartnerMappings.RelationLevel(relation_level)
    except (TypeError, ValueError, json.JSONDecodeError):
        return JsonResponse(
            {'success': False, 'message': 'Invalid relationship setting.'},
            status=400,
        )

    mapping = get_object_or_404(
        UserPartnerMappings,
        id=mapping_id,
        user=profile,
        is_active=True,
    )
    UserPartnerMappings.objects.filter(
        Q(user=profile, partner=mapping.partner)
        | Q(user=mapping.partner, partner=profile),
        is_active=True,
    ).update(
        relation_level=relation_choice,
        heartbeat_alert_sent=False,
    )
    danger_hours = UserPartnerMappings.danger_hours_for_level(relation_choice)
    return JsonResponse({
        'success': True,
        'message': (
            f'Relationship set to {relation_choice.label}. '
            f'Danger starts after {danger_hours} hours.'
        ),
        'relation_level': relation_choice.value,
        'relation_label': relation_choice.label,
        'danger_hours': danger_hours,
        'warning_hours': danger_hours / 2,
    })


@login_required
def profile_view(request):
    profile = request.user.profile
    # Handle name update
    if request.method == 'POST' and 'full_name' in request.POST:
        full_name = request.POST.get('full_name', '').strip()
        if full_name:
            parts = full_name.split(None, 1)
            request.user.first_name = parts[0]
            request.user.last_name = parts[1] if len(parts) > 1 else ''
            request.user.save()
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'success': True, 'message': 'Name updated successfully!'})
            messages.success(request, 'Name updated successfully!')
            return redirect('profile')
        else:
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'message': 'Name cannot be empty.'})
            messages.error(request, 'Name cannot be empty.')
            return redirect('profile')

    # Handle invite code join
    if request.method == 'POST' and 'invite_code' in request.POST:
        response = _invite_link_response(
            request,
            profile,
            request.POST.get('invite_code', ''),
            success_redirect='profile',
        )
        if response is not None:
            return response

    paired_users = [p.user for p in profile.get_partners()]

    return render(request, 'core/profile.html', {'paired_users': paired_users})


@login_required
@require_http_methods(["GET", "POST"])
def settings_view(request):
    profile = request.user.profile
    if request.method == 'POST':
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            import json
            try:
                data = json.loads(request.body)
                if 'share_location_with_friends' in data:
                    profile.share_location_with_friends = bool(data['share_location_with_friends'])
                if 'share_location_in_sos' in data:
                    profile.share_location_in_sos = bool(data['share_location_in_sos'])
                if 'snooze_enabled' in data:
                    profile.snooze_enabled = bool(data['snooze_enabled'])
                profile.save()
                return JsonResponse({
                    'success': True,
                    'share_location_with_friends': profile.share_location_with_friends,
                    'share_location_in_sos': profile.share_location_in_sos,
                    'snooze_enabled': profile.snooze_enabled,
                })
            except Exception:
                return JsonResponse({'success': False}, status=400)
        if 'share_location_with_friends' in request.POST:
            profile.share_location_with_friends = request.POST.get('share_location_with_friends') == 'on'
        if 'share_location_in_sos' in request.POST:
            profile.share_location_in_sos = request.POST.get('share_location_in_sos') == 'on'
        if 'snooze_enabled' in request.POST:
            profile.snooze_enabled = request.POST.get('snooze_enabled') == 'on'
        profile.save()
        return redirect('settings')
    return render(request, 'core/settings.html', {'profile': profile})


def home(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    login_form = LoginForm(request.POST or None, request=request)
    signup_form = SignupForm(request.POST or None)
    active_tab = 'login'
    if request.method == 'POST':
        if request.POST.get('form_type') == 'login' and login_form.is_valid():
            perform_login(request, login_form.user, email_verification='optional')
            # Remember me: persist session for 2 weeks; otherwise expire when browser closes
            if request.POST.get('remember'):
                request.session.set_expiry(timedelta(days=14))
            else:
                request.session.set_expiry(0)
            return redirect('dashboard')
        if request.POST.get('form_type') == 'signup' and signup_form.is_valid():
            user = signup_form.save(request)
            auth_login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            return redirect('dashboard')
        if request.POST.get('form_type') == 'signup':
            active_tab = 'signup'
    return render(request, 'core/home.html', {
        'login_form': login_form,
        'signup_form': signup_form,
        'active_auth_tab': active_tab,
    })

@login_required
def dashboard(request):
    profile = request.user.profile
    if not profile.get_partners():
        return redirect('link_partner')
    has_emergency_contacts = UserPartnerMappings.objects.filter(
        user=profile, is_active=True, is_emergency=True
    ).exists()
    has_active_sos_sent = SOSAlert.objects.filter(
        from_user=profile, status=SOSAlert.Status.ACTIVE
    ).exists()
    return render(request, 'core/dashboard.html', {
        'profile': profile,
        'has_emergency_contacts': has_emergency_contacts,
        'has_active_sos_sent': has_active_sos_sent,
        'danger_hours': profile.danger_hours,
        'warning_hours': profile.warning_hours,
    })

@login_required
def link_partner(request):
    if request.method == 'POST':
        response = _invite_link_response(
            request,
            request.user.profile,
            request.POST.get('invite_code', ''),
            success_redirect=reverse('friends') + '?member_added=1',
        )
        if response is not None:
            return response
    return render(request, 'core/link_partner.html')

@login_required
def check_in(request):
    if request.method == 'POST':
        profile = request.user.profile
        checked_in_at = timezone.now()
        profile.last_check_in = checked_in_at
        profile.alert_sent = False  # reset if was sent
        UserPartnerMappings.objects.filter(
            user=profile,
            is_active=True,
        ).update(heartbeat_alert_sent=False)
        # Store location when sharing is enabled (from JSON or form)
        if profile.share_location_with_friends:
            lat, lng = None, None
            if request.headers.get('content-type', '').startswith('application/json'):
                try:
                    import json
                    data = json.loads(request.body)
                    lat = data.get('lat')
                    lng = data.get('lng')
                except Exception:
                    pass
            else:
                lat = request.POST.get('lat')
                lng = request.POST.get('lng')
            if lat is not None and lng is not None:
                try:
                    profile.last_latitude = float(lat)
                    profile.last_longitude = float(lng)
                    profile.location_updated_at = timezone.now()
                    from .utils import reverse_geocode
                    city, state = reverse_geocode(profile.last_latitude, profile.last_longitude)
                    profile.last_city = city
                    profile.last_state = state
                except (TypeError, ValueError):
                    pass
        profile.save()
        return JsonResponse({
            'status': 'success',
            'checked_in_at': checked_in_at.isoformat(),
        })
    return JsonResponse({'status': 'error'}, status=400)


# --- SOS (emergency) feature ---

@login_required
@require_POST
def sos_trigger(request):
    """Create active SOS alerts only to emergency contacts. Called after 10s countdown (no cancel).
    Optional JSON body: { "lat": <float>, "lng": <float> }. If provided, store location and
    enable share_location_in_sos if it was off (user granted location from SOS button)."""
    profile = request.user.profile
    if SOSAlert.objects.filter(from_user=profile, status=SOSAlert.Status.ACTIVE).exists():
        return JsonResponse({
            'success': False,
            'message': 'You already have an active SOS. It must be resolved before you can send another.',
        }, status=400)
    emergency_mappings = UserPartnerMappings.objects.filter(
        user=profile, is_active=True, is_emergency=True
    )
    if not emergency_mappings.exists():
        return JsonResponse({
            'success': False,
            'message': 'No emergency contacts. Choose them on the Friends page and save.',
        }, status=400)
    # Optional location: if sent with SOS, store it and enable share_location_in_sos if not already
    try:
        data = __import__('json').loads(request.body) if request.body else {}
        lat, lng = data.get('lat'), data.get('lng')
    except Exception:
        lat, lng = None, None
    if lat is not None and lng is not None:
        try:
            profile.last_latitude = float(lat)
            profile.last_longitude = float(lng)
            profile.location_updated_at = timezone.now()
            from .utils import reverse_geocode
            city, state = reverse_geocode(profile.last_latitude, profile.last_longitude)
            profile.last_city = city
            profile.last_state = state
            if not profile.share_location_in_sos:
                profile.share_location_in_sos = True
        except (TypeError, ValueError):
            pass
    profile.save()
    emergency_profiles = []
    for mapping in emergency_mappings:
        SOSAlert.objects.create(from_user=profile, to_user=mapping.partner, status=SOSAlert.Status.ACTIVE)
        emergency_profiles.append(mapping.partner)
    send_sos_via_emailjs(profile, emergency_profiles)
    return JsonResponse({'success': True, 'message': 'SOS sent to your emergency contacts.'})


@login_required
@require_GET
def sos_has_emergency_contacts(request):
    """Return whether the current user has emergency contacts and if they already have an active SOS sent."""
    profile = request.user.profile
    has_emergency = UserPartnerMappings.objects.filter(
        user=profile, is_active=True, is_emergency=True
    ).exists()
    has_active_sos_sent = SOSAlert.objects.filter(
        from_user=profile, status=SOSAlert.Status.ACTIVE
    ).exists()
    return JsonResponse({
        'has_emergency_contacts': has_emergency,
        'has_active_sos_sent': has_active_sos_sent,
    })


@login_required
@require_GET
def sos_list(request):
    """List active SOS alerts received by the current user (for dashboard)."""
    profile = request.user.profile
    alerts = SOSAlert.objects.filter(to_user=profile, status=SOSAlert.Status.ACTIVE).select_related('from_user', 'from_user__user')
    def _location_str(p):
        parts = [x for x in (p.last_city, p.last_state) if x]
        return ', '.join(parts) if parts else None

    def _display_name(u):
        name = (u.get_full_name() or '').strip()
        return name or u.username or u.email or 'Someone'

    data = []
    for a in alerts:
        from_profile = a.from_user
        item = {
            'id': a.id,
            'from_name': _display_name(from_profile.user),
            'from_username': from_profile.user.username,
            'from_email': from_profile.user.email,
            'created_at': a.created_at.isoformat(),
            'location': _location_str(from_profile),
            'location_updated_at': from_profile.location_updated_at.isoformat() if from_profile.location_updated_at else None,
        }
        if from_profile.share_location_in_sos and from_profile.last_latitude is not None and from_profile.last_longitude is not None:
            item['lat'] = from_profile.last_latitude
            item['lng'] = from_profile.last_longitude
        data.append(item)
    return JsonResponse({'alerts': data})


@login_required
@require_POST
def sos_resolve(request):
    """Mark an SOS alert as resolved. Expects JSON body: { "alert_id": <id> }."""
    profile = request.user.profile
    try:
        import json
        data = json.loads(request.body)
        alert_id = data.get('alert_id')
    except Exception:
        return JsonResponse({'success': False, 'message': 'Invalid request.'}, status=400)
    if not alert_id:
        return JsonResponse({'success': False, 'message': 'alert_id required.'}, status=400)
    try:
        alert = SOSAlert.objects.get(id=alert_id, to_user=profile, status=SOSAlert.Status.ACTIVE)
    except SOSAlert.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Alert not found or already resolved.'}, status=404)
    from_profile = alert.from_user
    now = timezone.now()
    # When any emergency contact resolves, clear this SOS for everyone (all recipients)
    SOSAlert.objects.filter(
        from_user=from_profile,
        status=SOSAlert.Status.ACTIVE
    ).update(status=SOSAlert.Status.RESOLVED, resolved_at=now, resolved_by_id=profile.pk)
    # Notify the person who triggered the SOS so they see the resolved alert on dashboard
    try:
        SOSResolvedNotification.objects.create(
            triggerer=from_profile,
            resolved_by=profile,
        )
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning('SOSResolvedNotification create failed: %s', e)
    return JsonResponse({'success': True, 'message': 'SOS marked as resolved.'})


@login_required
@require_GET
def sos_resolved_notifications(request):
    """List unseen 'your SOS was resolved' notifications for the current user (triggerer)."""
    try:
        profile = request.user.profile
        def _display_name(u):
            name = (u.get_full_name() or '').strip()
            return name or u.username or u.email or 'Someone'
        notifications = SOSResolvedNotification.objects.filter(
            triggerer=profile, seen=False
        ).select_related('resolved_by', 'resolved_by__user').order_by('-created_at')
        data = [
            {
                'id': n.id,
                'resolved_by_name': _display_name(n.resolved_by.user),
                'resolved_by_username': n.resolved_by.user.username,
                'resolved_by_email': n.resolved_by.user.email,
                'resolved_at': n.created_at.isoformat(),
            }
            for n in notifications
        ]
        return JsonResponse({'notifications': data})
    except Exception as e:
        import logging
        logging.getLogger(__name__).exception('sos_resolved_notifications failed')
        return JsonResponse({'notifications': []})


@login_required
@require_POST
def sos_resolved_notifications_seen(request):
    """Mark resolved notifications as seen. Expects JSON body: { "ids": [1, 2, ...] }."""
    profile = request.user.profile
    try:
        import json
        data = json.loads(request.body)
        ids = data.get('ids') or []
    except Exception:
        return JsonResponse({'success': False}, status=400)
    if ids:
        SOSResolvedNotification.objects.filter(
            id__in=ids, triggerer=profile, seen=False
        ).update(seen=True)
    return JsonResponse({'success': True})
