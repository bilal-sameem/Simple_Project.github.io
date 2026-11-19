import csv
import datetime
import mimetypes
import os
import re
from collections import Counter

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.http import FileResponse, Http404, HttpResponse, JsonResponse
from django.http.multipartparser import MultiPartParserError
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.views.decorators.http import require_http_methods, require_POST

from . import jalali
from .forms import PersonForm, collect_documents, parse_educations
from .models import Education, Person, PersonDocument, complete_q

PAGE_SIZE = 25
REPORT_PAGE_SIZE = 50
_LATIN = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")


def _json(data, status=200):
    return JsonResponse(data, status=status, json_dumps_params={"ensure_ascii": False})


def _errors(form):
    return {field: msgs[0] for field, msgs in form.errors.items()}


# ----------------------------------------------------------- query helpers
def _search(qs, text):
    """Name / father name / ID / phone / organization contains the text (Pashto digits accepted)."""
    text = (text or "").strip()
    if not text:
        return qs
    cond = Q()
    for t in {text, text.translate(_LATIN)}:
        cond |= (Q(full_name__icontains=t) | Q(father_name__icontains=t) | Q(id_number__icontains=t)
                 | Q(phone__icontains=t) | Q(organization__icontains=t) | Q(hire_letter_number__icontains=t))
    return qs.filter(cond)


def _date(value):
    """Filter dates are typed in the solar calendar (1405/08/20); old ISO links (2026-11-11) still work."""
    value = (value or "").strip()
    if not value:
        return None
    try:
        return jalali.parse(value)
    except ValueError:
        pass
    try:
        return parse_date(value)
    except ValueError:
        return None


def _filtered(params):
    """Shared by the Reports page and the CSV export so both always agree."""
    qs = _search(Person.objects.select_related("created_by").prefetch_related("educations"), params.get("q"))
    d_from, d_to = _date(params.get("date_from")), _date(params.get("date_to"))
    if d_from:
        qs = qs.filter(created_at__date__gte=d_from)
    if d_to:
        qs = qs.filter(created_at__date__lte=d_to)
    status = params.get("status")
    if status == "complete":
        qs = qs.filter(complete_q())
    elif status == "incomplete":
        qs = qs.filter(~complete_q())
    return qs


# ------------------------------------------------------------------- pages
@login_required
def dashboard(request):
    q = request.GET.get("q", "").strip()
    page = Paginator(_search(Person.objects.all(), q), PAGE_SIZE).get_page(request.GET.get("page"))
    # "this month" = since the 1st of the current solar month (e.g. 1 عقرب)
    month_start = timezone.make_aware(datetime.datetime.combine(jalali.month_start(timezone.localdate()),
                                                               datetime.time.min))
    stats = {"total": Person.objects.count(),
             "complete": Person.objects.filter(complete_q()).count(),
             "this_month": Person.objects.filter(created_at__gte=month_start).count()}
    return render(request, "sawanih/dashboard.html", {"active": "home", "page_obj": page, "q": q, "stats": stats})


@login_required
def person_new(request):
    return render(request, "sawanih/person_form.html", {"active": "add", "person": None, "docs": {}})


@login_required
def person_edit(request, pk):
    person = get_object_or_404(Person.objects.prefetch_related("educations", "documents"), pk=pk)
    docs = {kind: [d for d in person.documents.all() if d.kind == kind] for kind, _ in PersonDocument.KINDS}
    return render(request, "sawanih/person_form.html", {"active": "home", "person": person, "docs": docs})


@login_required
def person_detail(request, pk):
    person = get_object_or_404(Person.objects.select_related("created_by", "updated_by")
                               .prefetch_related("educations", "documents"), pk=pk)
    doc_groups = [(label, [d for d in person.documents.all() if d.kind == kind]) for kind, label in PersonDocument.KINDS]
    return render(request, "sawanih/person_detail.html", {"active": "home", "p": person, "doc_groups": doc_groups})


@login_required
def document_file(request, pk):
    """ID cards and certificates are private: only logged-in users can open them, never via a public /media/ URL."""
    doc = get_object_or_404(PersonDocument, pk=pk)
    ext = os.path.splitext(doc.file.name)[1].lower()
    try:
        resp = FileResponse(doc.file.open("rb"), content_type=mimetypes.types_map.get(ext, "application/octet-stream"),
                            filename=f"{doc.kind}-{doc.pk}{ext}")      # shown inline in the browser
    except FileNotFoundError:
        raise Http404
    resp["Cache-Control"] = "private, no-store"
    return resp


# ----------------------------------------------------------------- reports
@login_required
def reports(request):
    qs = _filtered(request.GET)
    total = qs.count()
    complete = qs.filter(complete_q()).count()
    stats = {"total": total, "complete": complete, "incomplete": total - complete}
    page = Paginator(qs, REPORT_PAGE_SIZE).get_page(request.GET.get("page"))
    return render(request, "sawanih/reports.html",
                  {"active": "reports", "page_obj": page, "stats": stats, "f": request.GET})


def _cell(value):
    """Stop Excel from running a cell as a formula (=, @, or +/- followed by text)."""
    s = "" if value is None else str(value)
    if s and (s[0] in "=@\t\r" or (s[0] in "+-" and not re.fullmatch(r"[+\-]?[\d\s()\-]+", s))):
        return "'" + s
    return s


def _jd(d):
    """Solar-calendar text for the CSV, e.g. 1405/08/20 (Latin digits so Excel keeps it as text)."""
    return jalali.fmt_input(d) if d else ""


def _edu_text(p):
    return " | ".join(f"{e.degree} - {e.institution}" + (f" ({e.graduation_year})" if e.graduation_year else "")
                      for e in p.educations.all())


@login_required
def reports_export(request):
    qs = _filtered(request.GET)
    resp = HttpResponse(content_type="text/csv; charset=utf-8")
    resp["Content-Disposition"] = f'attachment; filename="persons-{jalali.fmt_input(timezone.localdate()).replace("/", "-")}.csv"'
    resp.write("﻿")        # BOM so Excel reads Pashto text correctly
    w = csv.writer(resp)
    w.writerow(["بشپړ نوم", "د پلار نوم", "د نیکه نوم", "د زېږېدو نېټه", "د تذکرې شمېره", "تلیفون",
                "بریښنالیک", "پته", "تحصیلي معلومات", "دنده", "اداره", "د ګمارنې / پیل نېټه",
                "د ګمارنې د مکتوب شمېره", "د مکتوب نېټه", "مکتوب صادرونکې اداره",
                "حالت", "د ثبت نېټه", "ثبت کوونکی"])
    for p in qs.iterator(chunk_size=500):
        w.writerow([_cell(x) for x in (
            p.full_name, p.father_name, p.grandfather_name, _jd(p.date_of_birth), p.id_number, p.phone,
            p.email, p.address, _edu_text(p), p.job_title, p.organization,
            _jd(p.start_date), p.hire_letter_number, _jd(p.hire_letter_date), p.hire_letter_issuer,
            "بشپړ" if p.is_complete else "نابشپړ",
            _jd(timezone.localtime(p.created_at)) + timezone.localtime(p.created_at).strftime(" %H:%M"),
            p.created_by.get_username() if p.created_by else "")])
    return resp


# --------------------------------------------------------------------- API
def _sync_educations(person, rows):
    """Make the person's education rows match the submitted list (update, add, remove)."""
    existing = {e.pk: e for e in person.educations.all()}
    keep = set()
    for pos, r in enumerate(rows):
        e = existing.get(r["id"])
        if e:
            e.degree, e.institution = r["degree"], r["institution"]
            e.graduation_year, e.position = r["graduation_year"], pos
            e.save()
        else:
            e = Education.objects.create(person=person, degree=r["degree"], institution=r["institution"],
                                         graduation_year=r["graduation_year"], position=pos)
        keep.add(e.pk)
    person.educations.exclude(pk__in=keep).delete()


def _add_documents(person, new_docs, user):
    for kind, f, ext in new_docs:
        original = f.name
        f.name = "upload" + ext                  # extension comes from the checked file type
        PersonDocument.objects.create(person=person, kind=kind, file=f,
                                      original_name=original[:120], uploaded_by=user)


@login_required
@require_POST
def api_person_create(request):
    """POST /api/persons/  — multipart: person fields + edu_* rows + id_card_files / experience_files / education_files."""
    form = PersonForm(request.POST, request.FILES)
    edu_rows, edu_errors = parse_educations(request.POST, set())
    doc_errors, new_docs = collect_documents(request.FILES, {})
    errors = {}
    if not form.is_valid():
        errors.update(_errors(form))
    errors.update(edu_errors)
    errors.update(doc_errors)
    if errors:
        return _json({"errors": errors}, 400)

    with transaction.atomic():
        person = form.save(commit=False)
        person.created_by = request.user            # audit: who ...
        person.save()                               # ... and when (created_at is automatic)
        _sync_educations(person, edu_rows)
        _add_documents(person, new_docs, request.user)
    messages.success(request, "شخص په بریالیتوب ثبت شو.")
    return _json({"id": person.pk}, 201)


@login_required
@require_http_methods(["PUT", "DELETE"])
def api_person_item(request, pk):
    """PUT /api/persons/<id>/ updates a person; DELETE /api/persons/<id>/ removes one."""
    person = get_object_or_404(Person, pk=pk)

    if request.method == "DELETE":
        if not request.user.has_perm("sawanih.delete_person"):
            return _json({"error": "تاسو د ړنګولو اجازه نه لرئ."}, 403)
        files = [(d.file.storage, d.file.name) for d in person.documents.all()]
        if person.photo:
            files.append((person.photo.storage, person.photo.name))
        person.delete()                              # education + document rows go with it
        for storage, name in files:
            storage.delete(name)
        messages.success(request, "ریکارډ ړنګ شو.")
        return _json({"ok": True})

    # PUT: Django only parses multipart bodies for POST, so parse it by hand (keeps uploads working).
    if request.content_type != "multipart/form-data":
        return _json({"error": "bad request"}, 400)
    try:
        data, files = request.parse_file_upload(request.META, request)
    except MultiPartParserError:
        return _json({"error": "bad request"}, 400)

    old_photo = person.photo.name                    # read BEFORE the form touches the instance
    existing_docs = list(person.documents.all())
    remove_ids = {int(x) for x in data.getlist("remove_docs") if x.isdigit()}
    kept = Counter(d.kind for d in existing_docs if d.pk not in remove_ids)

    form = PersonForm(data, files, instance=person)  # instance => unique-ID check ignores this person
    edu_rows, edu_errors = parse_educations(data, {e.pk for e in person.educations.all()})
    doc_errors, new_docs = collect_documents(files, kept)
    errors = {}
    if not form.is_valid():
        errors.update(_errors(form))
    errors.update(edu_errors)
    errors.update(doc_errors)
    if errors:
        return _json({"errors": errors}, 400)

    removed = [d for d in existing_docs if d.pk in remove_ids]
    removed_files = [(d.file.storage, d.file.name) for d in removed]
    with transaction.atomic():
        person = form.save(commit=False)
        person.updated_by = request.user
        person.save()
        _sync_educations(person, edu_rows)
        PersonDocument.objects.filter(pk__in=[d.pk for d in removed]).delete()
        _add_documents(person, new_docs, request.user)
    for storage, name in removed_files:              # delete files only after the database change succeeded
        storage.delete(name)
    if old_photo and "photo" in files and old_photo != person.photo.name:
        person.photo.storage.delete(old_photo)
    messages.success(request, "د شخص معلومات په بریالیتوب تازه شول.")
    return _json({"id": person.pk})
