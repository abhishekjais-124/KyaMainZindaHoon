from .models import SOSAlert


def emergency_sos(request):
    """Add emergency_sos_active to template context when the current user has an active SOS sent."""
    if not getattr(request, 'user', None) or not request.user.is_authenticated:
        return {'emergency_sos_active': False}
    try:
        profile = request.user.profile
    except Exception:
        return {'emergency_sos_active': False}
    active = SOSAlert.objects.filter(
        from_user=profile,
        status=SOSAlert.Status.ACTIVE,
    ).exists()
    return {'emergency_sos_active': active}
