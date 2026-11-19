"""Afghan solar calendar (Solar Hijri / تقویم هجري شمسي) helpers. No dependencies.

The database keeps normal (Gregorian) `date` values, so sorting and date filters keep working.
Everything the user sees or types is converted with these functions.
Conversion follows the standard 33-year-cycle Solar Hijri algorithm (same year start as Afghanistan: 1 حمل = about 21 March).
"""
import math
import re
from datetime import date, datetime

# Afghan month names. To use Pashto names instead, replace with:
# وری، غویی، غبرګولی، چنګاښ، زمری، وږی، تله، لړم، لیندۍ، مرغومی، سلواغه، کب
MONTHS = ["حمل", "ثور", "جوزا", "سرطان", "اسد", "سنبله", "میزان", "عقرب", "قوس", "جدی", "دلو", "حوت"]

MIN_YEAR, MAX_YEAR = 1000, 1600          # supported range
_BREAKS = [-61, 9, 38, 199, 426, 686, 756, 818, 1111, 1181, 1210, 1635, 2060, 2097, 2192, 2262, 2324, 2394, 2456, 3178]
_LATIN = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")
_PERSIAN = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")


def _jal_cal(jy):
    gy = jy + 621
    leap_j, jp = -14, _BREAKS[0]
    jump = 0
    for jm in _BREAKS[1:]:
        jump = jm - jp
        if jy < jm:
            break
        leap_j += (jump // 33) * 8 + (jump % 33) // 4
        jp = jm
    n = jy - jp
    leap_j += (n // 33) * 8 + (n % 33 + 3) // 4
    if jump % 33 == 4 and jump - n == 4:
        leap_j += 1
    leap_g = gy // 4 - ((gy // 100 + 1) * 3) // 4 - 150
    march = 20 + leap_j - leap_g
    if jump - n < 6:
        n = n - jump + ((jump + 4) // 33) * 33
    leap = int(math.fmod(int(math.fmod(n + 1, 33)) - 1, 4))
    if leap == -1:
        leap = 4
    return leap, gy, march


def _div(a, b):
    """Integer division that truncates toward zero (like JavaScript), unlike Python's //."""
    return int(a / b) if abs(a) < 2 ** 50 else (abs(a) // abs(b)) * (1 if (a < 0) == (b < 0) else -1)


def _g2d(gy, gm, gd):
    d = _div((gy + _div(gm - 8, 6) + 100100) * 1461, 4) + _div(153 * ((gm + 9) % 12) + 2, 5) + gd - 34840408
    return d - _div(_div(gy + 100100 + _div(gm - 8, 6), 100) * 3, 4) + 752


def _d2g(jdn):
    j = 4 * jdn + 139361631
    j += (((4 * jdn + 183187720) // 146097) * 3 // 4) * 4 - 3908
    i = ((j % 1461) // 4) * 5 + 308
    gd = (i % 153) // 5 + 1
    gm = (i // 153) % 12 + 1
    gy = j // 1461 - 100100 + _div(8 - gm, 6)
    return gy, gm, gd


def is_leap(jy):
    return _jal_cal(jy)[0] == 0


def month_days(jy, jm):
    if jm <= 6:
        return 31
    if jm <= 11:
        return 30
    return 30 if is_leap(jy) else 29


def to_jalali(d):
    """date / datetime -> (year, month, day) in the solar calendar."""
    if isinstance(d, datetime):
        d = d.date()
    jdn = _g2d(d.year, d.month, d.day)
    gy = _d2g(jdn)[0]
    jy = gy - 621
    leap, _, march = _jal_cal(jy)
    k = jdn - _g2d(gy, 3, march)
    if k >= 0:
        if k <= 185:
            return jy, 1 + k // 31, k % 31 + 1
        k -= 186
    else:
        jy -= 1
        k += 179
        if leap == 1:
            k += 1
    return jy, 7 + k // 30, k % 30 + 1


def to_gregorian(jy, jm, jd):
    """(year, month, day) in the solar calendar -> date. Raises ValueError when impossible."""
    if not (MIN_YEAR <= jy <= MAX_YEAR) or not (1 <= jm <= 12) or not (1 <= jd <= month_days(jy, jm)):
        raise ValueError("invalid solar date")
    _, gy, march = _jal_cal(jy)
    jdn = _g2d(gy, 3, march) + (jm - 1) * 31 - (jm // 7) * (jm - 7) + jd - 1
    return date(*_d2g(jdn))


def latin_digits(s):
    return str(s).translate(_LATIN)


def persian_digits(s):
    return str(s).translate(_PERSIAN)


_PARSE = re.compile(r"(\d{4})[/\-.](\d{1,2})[/\-.](\d{1,2})")


def parse(text):
    """'1405/08/20' (any digits, separators / - .) -> date. Raises ValueError when wrong."""
    m = _PARSE.fullmatch(latin_digits(text).strip())
    if not m:
        raise ValueError("bad format")
    return to_gregorian(*(int(x) for x in m.groups()))


def today():
    from django.utils import timezone
    return to_jalali(timezone.localdate())


def month_start(d):
    """First day (as a Gregorian date) of the solar month that contains `d`."""
    jy, jm, _ = to_jalali(d)
    return to_gregorian(jy, jm, 1)


# ------------------------------------------------------------- formatting
def fmt_input(d):
    """For text inputs: 1405/08/20 (Latin digits)."""
    jy, jm, jd = to_jalali(d)
    return f"{jy:04d}/{jm:02d}/{jd:02d}"


def fmt_short(d):
    """۱۴۰۵/۰۸/۲۰"""
    return persian_digits(fmt_input(d))


def fmt_long(d):
    """۲۰ عقرب ۱۴۰۵"""
    jy, jm, jd = to_jalali(d)
    return persian_digits(f"{jd} {MONTHS[jm - 1]} {jy}")
