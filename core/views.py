
from django.views.decorators.http import require_GET, require_http_methods
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.models import User
from .models import Profile
from .utils import send_alert_via_emailjs
from django.utils import timezone
from django.http import JsonResponse
from .models import UserPartnerMappings
from django.db.models import Q

@login_required
def invite_code_popup(request):
    profile = request.user.profile
    if not profile.invite_code:
        from .models import generate_invite_code
        profile.invite_code = generate_invite_code()
        profile.save()
    return render(request, 'core/invite_code_popup.html', {'invite_code': profile.invite_code})

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
        invite_code = request.POST.get('invite_code', '').strip().lower()
        if invite_code:
            try:
                partner_profile = Profile.objects.get(invite_code=invite_code)
                if partner_profile == profile:
                    error_msg = "You can't pair with yourself."
                elif profile.get_partner():
                    error_msg = "You already have a partner."
                elif partner_profile.get_partner():
                    error_msg = "This user already has a partner."
                else:
                    UserPartnerMappings.objects.create(user=profile, partner=partner_profile, is_active=True)
                    UserPartnerMappings.objects.create(user=partner_profile, partner=profile, is_active=True)
                    success_msg = "Paired successfully!"
                    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                        return JsonResponse({'success': True, 'message': success_msg})
                    messages.success(request, success_msg)
                    return redirect('friends')
                if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    return JsonResponse({'success': False, 'message': error_msg})
                messages.error(request, error_msg)
            except Profile.DoesNotExist:
                error_msg = "Invalid invite code."
                if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    return JsonResponse({'success': False, 'message': error_msg})
                messages.error(request, error_msg)

    # Handle delete mapping (AJAX)
    if request.method == 'POST' and 'delete_mapping' in request.POST:
        partner_email = request.POST.get('delete_mapping')
        try:
            partner_user = User.objects.get(email=partner_email)
            partner_profile = partner_user.profile
            # Deactivate both directions
            UserPartnerMappings.objects.filter(user=profile, partner=partner_profile, is_active=True).update(is_active=False)
            UserPartnerMappings.objects.filter(user=partner_profile, partner=profile, is_active=True).update(is_active=False)
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'success': True, 'message': 'Connection deleted.'})
            messages.success(request, 'Connection deleted.')
            return redirect('friends')
        except User.DoesNotExist:
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'message': 'User not found.'})
            messages.error(request, 'User not found.')

    # Only show active mappings
    paired_users = []
    active_mappings = UserPartnerMappings.objects.filter(user=profile, is_active=True)
    for mapping in active_mappings:
        paired_users.append(mapping.partner.user)

    return render(request, 'core/friends.html', {'paired_users': paired_users})

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
            messages.success(request, 'Name updated successfully!')
            return redirect('profile')

    # Handle invite code join
    if request.method == 'POST' and 'invite_code' in request.POST:
        invite_code = request.POST.get('invite_code', '').strip().lower()
        if invite_code:
            try:
                partner_profile = Profile.objects.get(invite_code=invite_code)
                if partner_profile == profile:
                    error_msg = "You can't pair with yourself."
                elif profile.get_partner():
                    error_msg = "You already have a partner."
                elif partner_profile.get_partner():
                    error_msg = "This user already has a partner."
                else:
                    UserPartnerMappings.objects.create(user=profile, partner=partner_profile, is_active=True)
                    UserPartnerMappings.objects.create(user=partner_profile, partner=profile, is_active=True)
                    success_msg = "Paired successfully!"
                    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                        return JsonResponse({'success': True, 'message': success_msg})
                    messages.success(request, success_msg)
                    return redirect('profile')
                if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    return JsonResponse({'success': False, 'message': error_msg})
                messages.error(request, error_msg)
            except Profile.DoesNotExist:
                error_msg = "Invalid invite code."
                if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    return JsonResponse({'success': False, 'message': error_msg})
                messages.error(request, error_msg)

    # Paired users list (show only if paired)
    paired_users = []
    partner = profile.get_partner()
    if partner:
        paired_users.append(partner.user)

    return render(request, 'core/profile.html', {'paired_users': paired_users})

def home(request):
    if not request.user.is_authenticated:
        return render(request, 'core/home.html')
    profile = request.user.profile
    return render(request, 'core/dashboard.html', {'profile': profile})

@login_required
def dashboard(request):
    profile = request.user.profile
    if not profile.get_partner():
        return redirect('link_partner')
    return render(request, 'core/dashboard.html', {'profile': profile})

@login_required
def link_partner(request):
    if request.method == 'POST':
        invite_code = request.POST.get('invite_code', '').strip().lower()
        try:
            partner_profile = Profile.objects.get(invite_code=invite_code)
            if partner_profile.user == request.user:
                messages.error(request, "You can't link yourself as partner.")
            else:
                profile = request.user.profile
                if profile.get_partner() or partner_profile.get_partner():
                    messages.error(request, "One of you already has a partner.")
                else:
                    UserPartnerMappings.objects.create(user=profile, partner=partner_profile, is_active=True)
                    UserPartnerMappings.objects.create(user=partner_profile, partner=profile, is_active=True)
                    messages.success(request, "Partner linked successfully!")
                    return redirect('dashboard')
        except Profile.DoesNotExist:
            messages.error(request, "User with this invite code does not exist.")
    return render(request, 'core/link_partner.html')

@login_required
def check_in(request):
    if request.method == 'POST':
        profile = request.user.profile
        profile.last_check_in = timezone.now()
        profile.alert_sent = False  # reset if was sent
        profile.save()
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error'}, status=400)
