from datetime import datetime

from django import template
from django.utils import timezone

from .. import jalali

register = template.Library()
_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")


@register.filter
def pd(value):
    """Show digits as Eastern Arabic-Indic: 12 -> ۱۲"""
    return str(value).translate(_DIGITS)


def _as_date(value):
    if not value:
        return None
    if isinstance(value, datetime):
        if timezone.is_aware(value):
            value = timezone.localtime(value)
        return value
    return value


@register.filter
def jdate(value):
    """date -> ۲۰ عقرب ۱۴۰۵"""
    v = _as_date(value)
    return jalali.fmt_long(v) if v else "—"


@register.filter
def jshort(value):
    """date -> ۱۴۰۵/۰۸/۲۰"""
    v = _as_date(value)
    return jalali.fmt_short(v) if v else "—"


@register.filter
def jdatetime(value):
    """datetime -> ۲۰ عقرب ۱۴۰۵ — ۱۴:۰۲"""
    v = _as_date(value)
    if not v:
        return "—"
    out = jalali.fmt_long(v)
    return out + (" — " + jalali.persian_digits(v.strftime("%H:%M")) if isinstance(v, datetime) else "")


@register.filter
def jinput(value):
    """date -> 1405/08/20 (value for the text inputs)"""
    return jalali.fmt_input(value) if value else ""
