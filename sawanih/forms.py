import re
from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from PIL import Image

from . import jalali
from .models import Person

# Inline error messages (Pashto). The same texts are used in person_form.js.
REQ = "دا ډګر اړین دی."
DUP = "دا د تذکرې شمېره مخکې ثبت شوې ده."
BAD_ID = "د تذکرې شمېره سمه نه ده (۵ تر ۳۰ توري، شمېرې یا - /)."
BAD_PHONE = "د تلیفون شمېره سمه نه ده. بېلګه: 0700123456"
BAD_DOB = "د زېږېدو نېټه سمه نه ده."
BAD_DATE = "نېټه سمه نه ده. بېلګه: ۱۴۰۵/۰۸/۲۰ (کال/میاشت/ورځ)"
BAD_LETTER_DATE = "د مکتوب نېټه نشي کولی راتلونکې وي."
LETTER_PAIR = "د مکتوب شمېره او نېټه دواړه باید ډک شي."
BAD_YEAR = "د فراغت کال سم نه دی."
BAD_START = "د پیل نېټه نشي کولی راتلونکې وي."
PHOTO_TYPE = "عکس باید JPG، PNG یا WEBP وي."
PHOTO_SIZE = "د عکس اندازه باید له 2 MB څخه کمه وي."
TOO_LONG = "دا متن ډېر اوږد دی."
EDU_COUNT = "تر ۱۰ درجو زیات نشي ثبتېدلی."
DOC_ID = "د تذکرې سند اړین دی."
DOC_ONE = "د دندې تجربې یا د زده کړې له سندونو لږ تر لږه یو اړین دی."
DOC_TYPE = "فایل باید JPG، PNG، WEBP یا PDF وي."
DOC_SIZE = "د هر فایل اندازه باید له 5 MB څخه کمه وي."
DOC_COUNT = "تر ۵ فایلونو زیات نشي پورته کېدی."

MAX_EDU, MAX_DOCS, MAX_DOC_SIZE = 10, 5, 5 * 1024 * 1024
# document kind -> name of the file input in the form
KIND_FIELDS = {"id_card": "id_card_files", "experience": "experience_files", "education": "education_files"}
_LATIN = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")


EDU_YEAR_MIN = 1300          # graduation years are entered as solar-calendar years, e.g. 1398


class JalaliDateField(forms.Field):
    """Text box holding a solar-calendar date such as 1405/08/20. Cleaned value is a normal `date`."""
    widget = forms.TextInput

    def to_python(self, value):
        if value in self.empty_values:
            return None
        try:
            return jalali.parse(str(value))
        except ValueError:
            raise ValidationError(self.error_messages["invalid"], code="invalid")

    def prepare_value(self, value):
        return jalali.fmt_input(value) if hasattr(value, "year") else value


class PersonForm(forms.ModelForm):
    date_of_birth = JalaliDateField(required=True)
    start_date = JalaliDateField(required=False)
    hire_letter_date = JalaliDateField(required=False)

    class Meta:
        model = Person
        fields = ["full_name", "father_name", "grandfather_name", "date_of_birth", "id_number",
                  "phone", "email", "address", "photo", "job_title", "organization", "start_date",
                  "hire_letter_number", "hire_letter_date", "hire_letter_issuer", "notes"]
        error_messages = {"id_number": {"unique": DUP}}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for f in self.fields.values():
            f.error_messages.update(required=REQ, invalid="دا معلومات سم نه دي.",
                                    max_length=TOO_LONG, invalid_image=PHOTO_TYPE)
        self.fields["email"].error_messages["invalid"] = "بریښنالیک سم نه دی."
        for name in ("date_of_birth", "start_date", "hire_letter_date"):
            self.fields[name].error_messages["invalid"] = BAD_DATE

    def clean_id_number(self):
        v = self.cleaned_data["id_number"].strip()
        if not re.fullmatch(r"[0-9A-Za-z/\-]{5,30}", v):
            raise ValidationError(BAD_ID)
        return v

    def clean_phone(self):
        v = re.sub(r"[\s\-()]", "", self.cleaned_data["phone"])
        if not re.fullmatch(r"\+?\d{9,15}", v):
            raise ValidationError(BAD_PHONE)
        return v

    def clean_date_of_birth(self):
        v = self.cleaned_data["date_of_birth"]
        if v > timezone.localdate() or v.year < 1900:
            raise ValidationError(BAD_DOB)
        return v

    def clean_start_date(self):
        v = self.cleaned_data["start_date"]
        if v and v > timezone.localdate():
            raise ValidationError(BAD_START)
        return v

    def clean_hire_letter_number(self):
        return self.cleaned_data["hire_letter_number"].strip()

    def clean_hire_letter_date(self):
        v = self.cleaned_data["hire_letter_date"]
        if v and v > timezone.localdate():
            raise ValidationError(BAD_LETTER_DATE)
        return v

    def clean(self):
        data = super().clean()
        number, when = data.get("hire_letter_number"), data.get("hire_letter_date")
        if "hire_letter_number" in data and "hire_letter_date" in data and bool(number) != bool(when):
            self.add_error("hire_letter_date" if number else "hire_letter_number", LETTER_PAIR)
        return data

    def clean_photo(self):
        img = self.cleaned_data.get("photo")
        if img:
            if img.size > 2 * 1024 * 1024:
                raise ValidationError(PHOTO_SIZE)
            fmt = getattr(getattr(img, "image", None), "format", None)
            if fmt not in ("JPEG", "PNG", "WEBP"):
                raise ValidationError(PHOTO_TYPE)
        return img


# ------------------------------------------------------------ education rows
def parse_educations(data, existing_ids):
    """Read the repeated edu_* fields. Returns (rows, errors).
    A row with nothing typed in it is ignored; a started row needs a degree and an institution.
    Error keys look like edu_2_degree (2 = position of the row in the submitted form)."""
    ids, degrees = data.getlist("edu_id"), data.getlist("edu_degree")
    insts, years = data.getlist("edu_institution"), data.getlist("edu_year")
    n = max(len(ids), len(degrees), len(insts), len(years))
    if n > MAX_EDU:
        return [], {"edu_list": EDU_COUNT}

    def at(lst, i):
        return (lst[i] if i < len(lst) else "").strip()

    rows, errors = [], {}
    for i in range(n):
        degree, inst, year = at(degrees, i), at(insts, i), at(years, i).translate(_LATIN)
        if not (degree or inst or year):
            continue
        if not degree:
            errors[f"edu_{i}_degree"] = REQ
        elif len(degree) > 100:
            errors[f"edu_{i}_degree"] = TOO_LONG
        if not inst:
            errors[f"edu_{i}_institution"] = REQ
        elif len(inst) > 150:
            errors[f"edu_{i}_institution"] = TOO_LONG
        grad = None
        if year:
            if re.fullmatch(r"\d{4}", year) and EDU_YEAR_MIN <= int(year) <= jalali.today()[0] + 6:
                grad = int(year)
            else:
                errors[f"edu_{i}_year"] = BAD_YEAR
        raw_id = at(ids, i)
        rid = int(raw_id) if raw_id.isdigit() and int(raw_id) in existing_ids else None
        rows.append({"id": rid, "degree": degree, "institution": inst, "graduation_year": grad})
    return rows, errors


# --------------------------------------------------------------- documents
def check_document(f):
    """Return (extension, None) for a real JPG/PNG/WEBP/PDF under 5 MB, else (None, message).
    The type is read from the file's own bytes, not from its name."""
    if f.size > MAX_DOC_SIZE:
        return None, DOC_SIZE
    head = f.read(5)
    f.seek(0)
    if head == b"%PDF-":
        return ".pdf", None
    try:
        img = Image.open(f)
        fmt = img.format
        img.verify()
    except Exception:
        return None, DOC_TYPE
    finally:
        f.seek(0)
    ext = {"JPEG": ".jpg", "PNG": ".png", "WEBP": ".webp"}.get(fmt)
    return (ext, None) if ext else (None, DOC_TYPE)


def collect_documents(files, kept):
    """Validate uploads. `kept` = {kind: number of already-saved files that stay} (edit mode).
    Rules: ID card required; at least one of experience / education. Returns (errors, new_docs)."""
    errors, new, counts = {}, [], {}
    for kind, field in KIND_FIELDS.items():
        uploads = [f for f in files.getlist(field) if f]
        counts[kind] = kept.get(kind, 0) + len(uploads)
        if counts[kind] > MAX_DOCS:
            errors[field] = DOC_COUNT
            continue
        for f in uploads:
            ext, err = check_document(f)
            if err:
                errors[field] = err
                break
            new.append((kind, f, ext))
    if counts["id_card"] < 1 and "id_card_files" not in errors:
        errors["id_card_files"] = DOC_ID
    if counts["experience"] + counts["education"] < 1:
        errors["docs_one_of"] = DOC_ONE
    return errors, new
