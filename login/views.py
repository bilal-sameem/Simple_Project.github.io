"""Sign in / sign up / sign out for Sawanih.

Rules (change the constant below if you want different behaviour):
  * The very first account that signs up becomes the administrator and can log in at once.
  * Every later sign-up is created INACTIVE. An administrator turns it on in
    http://<server>/admin/ -> Users -> tick "Active". Set SIGNUP_NEEDS_APPROVAL = False for instant access.
"""
import re

from django.contrib.auth import authenticate, get_user_model, login, logout, password_validation
from django.contrib.auth.decorators import login_required
from django.contrib.staticfiles.storage import staticfiles_storage
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

User = get_user_model()
SIGNUP_NEEDS_APPROVAL = True
USERNAME_RE = re.compile(r"[A-Za-z0-9._-]{3,30}")

MSG_BAD_LOGIN = "د کاروونکي نوم یا پټنوم سم نه دی."
MSG_PENDING = "ستاسو حساب لا تر اوسه فعال شوی نه دی. مهرباني وکړئ د سیستم له اداره کوونکي څخه وغواړئ چې فعال یې کړي."
MSG_PENDING_INFO = "حساب جوړ شو. اداره کوونکی باید لومړی فعال کړي، بیا به ننوتلی شئ."
MSG_REQUIRED = "دا ډګر اړین دی."
MSG_USERNAME = "د کاروونکي نوم ۳ تر ۳۰ توري وي (انګلیسي توري، شمېرې، . _ -)."
MSG_TAKEN = "دا د کاروونکي نوم مخکې اخیستل شوی دی."
MSG_WEAK = "پټنوم کمزوری دی: لږ تر لږه ۸ توري، نه یوازې شمېرې، او نه عام پټنوم."
MSG_MISMATCH = "دواړه پټنومونه یو شان نه دي."


def _next(request):
    nxt = request.POST.get("next") or request.GET.get("next") or ""
    ok = url_has_allowed_host_and_scheme(nxt, {request.get_host()}, require_https=request.is_secure())
    return nxt if nxt and ok else ""


def _ctx(extra):
    """Use login/static/login/auth-bg.jpg as the left-side photo when the file exists (green overlay is added in CSS)."""
    try:
        has_photo = staticfiles_storage.exists("login/auth-bg.jpg")
    except Exception:
        has_photo = False
    return {"has_photo": has_photo, **extra}


def login_user(request):
    if request.user.is_authenticated:
        return redirect(_next(request) or "sawanih:dashboard")
    error, username = "", ""
    notice = MSG_PENDING_INFO if request.GET.get("pending") else ""
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect(_next(request) or "sawanih:dashboard")
        waiting = User.objects.filter(username=username, is_active=False).first()
        error = MSG_PENDING if waiting and waiting.check_password(password) else MSG_BAD_LOGIN
    return render(request, "authenticate/login.html",
                  _ctx({"error": error, "notice": notice, "username": username, "next": _next(request)}))


def signup(request):
    if request.user.is_authenticated:
        return redirect("sawanih:dashboard")
    errors = {}
    values = {"username": ""}
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        p1, p2 = request.POST.get("password1", ""), request.POST.get("password2", "")
        values = {"username": username}
        if not username:
            errors["username"] = MSG_REQUIRED
        elif not USERNAME_RE.fullmatch(username):
            errors["username"] = MSG_USERNAME
        elif User.objects.filter(username__iexact=username).exists():
            errors["username"] = MSG_TAKEN
        if not p1:
            errors["password1"] = MSG_REQUIRED
        else:
            try:
                password_validation.validate_password(p1, User(username=username))
            except ValidationError:
                errors["password1"] = MSG_WEAK
        if "password1" not in errors and p1 != p2:
            errors["password2"] = MSG_MISMATCH
        if not errors:
            try:
                with transaction.atomic():
                    user = User.objects.create_user(username=username, password=p1)
                    if not User.objects.exclude(pk=user.pk).exists():      # first account ever = administrator
                        user.is_staff = user.is_superuser = True
                    elif SIGNUP_NEEDS_APPROVAL:
                        user.is_active = False
                    user.save()
            except IntegrityError:
                errors["username"] = MSG_TAKEN
            else:
                if user.is_active:
                    login(request, user)
                    return redirect("sawanih:dashboard")
                return redirect(reverse("login") + "?pending=1")
    first_user = not User.objects.exists()
    return render(request, "authenticate/signup.html", _ctx({"errors": errors, "values": values, "first_user": first_user}))


@require_POST
def logout_user(request):
    logout(request)
    return redirect("login")


@login_required
def home(request):
    return redirect("sawanih:dashboard")
