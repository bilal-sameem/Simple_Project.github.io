from django.conf import settings
import os
import uuid

from django.core.files.storage import FileSystemStorage
from django.db import models
from django.db.models import Exists, OuterRef, Q


class SawanihEntry(models.Model):
    slug = models.SlugField("slug", unique=True, allow_unicode=True)
    title = models.CharField("نوم / سرلیک", max_length=200)
    subtitle = models.CharField("لنډه معرفي", max_length=300, blank=True)
    intro = models.TextField("پېژندنه", blank=True)
    language = models.CharField("ژبه", max_length=5, default="ps")
    published = models.BooleanField("خپور شوی", default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        verbose_name = "سوانح"
        verbose_name_plural = "سوانح"

    def __str__(self):
        return self.title


class EntrySection(models.Model):
    entry = models.ForeignKey(SawanihEntry, on_delete=models.CASCADE, related_name="sections")
    heading = models.CharField("سرلیک", max_length=200)
    body = models.TextField("متن", blank=True)
    position = models.PositiveIntegerField("ترتیب", default=0)

    class Meta:
        ordering = ["position", "id"]


class TimelineEvent(models.Model):
    entry = models.ForeignKey(SawanihEntry, on_delete=models.CASCADE, related_name="events")
    date_label = models.CharField("نېټه", max_length=60)
    title = models.CharField("پېښه", max_length=200)
    description = models.TextField("تشریح", blank=True)
    position = models.PositiveIntegerField("ترتیب", default=0)

    class Meta:
        ordering = ["position", "id"]


class EntryQuote(models.Model):
    entry = models.ForeignKey(SawanihEntry, on_delete=models.CASCADE, related_name="quotes")
    text = models.TextField("وینا")
    attribution = models.CharField("منسوب", max_length=200, blank=True)
    position = models.PositiveIntegerField("ترتیب", default=0)

    class Meta:
        ordering = ["position", "id"]


class Person(models.Model):
    # --- شخصي معلومات ---
    full_name = models.CharField("بشپړ نوم", max_length=150)
    father_name = models.CharField("د پلار نوم", max_length=150)
    grandfather_name = models.CharField("د نیکه نوم", max_length=150, blank=True)
    date_of_birth = models.DateField("د زېږېدو نېټه")
    id_number = models.CharField("د تذکرې شمېره", max_length=30, unique=True)
    phone = models.CharField("تلیفون", max_length=20)
    email = models.EmailField("بریښنالیک", blank=True)
    address = models.TextField("پته", blank=True)
    photo = models.ImageField("عکس", upload_to="persons/%Y/", blank=True)
    # (education lives in the Education model: one person can have many degrees)
    # --- دندې معلومات ---
    job_title = models.CharField("دنده", max_length=150, blank=True)
    organization = models.CharField("اداره", max_length=150, blank=True)
    start_date = models.DateField("د ګمارنې / پیل نېټه", null=True, blank=True)
    # مکتوب = the official letter the person was hired under
    hire_letter_number = models.CharField("د ګمارنې د مکتوب شمېره", max_length=60, blank=True)
    hire_letter_date = models.DateField("د مکتوب نېټه", null=True, blank=True)
    hire_letter_issuer = models.CharField("مکتوب صادرونکې اداره", max_length=150, blank=True)
    # --- اضافي ---
    notes = models.TextField("یادښتونه / سوانح", blank=True)
    # --- audit log ---
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    updated_at = models.DateTimeField(auto_now=True, null=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        verbose_name = "شخص"
        verbose_name_plural = "اشخاص"

    @property
    def is_complete(self):
        return bool(self.job_title and self.organization and self.educations.all())

    def __str__(self):
        return self.full_name


def private_storage():
    """Documents (ID cards, certificates) are stored OUTSIDE MEDIA_ROOT, so they are never public files.
    Override the folder with SAWANIH_PRIVATE_ROOT in settings.py if you like."""
    root = getattr(settings, "SAWANIH_PRIVATE_ROOT", None) or (getattr(settings, "BASE_DIR", ".") / "private_media")
    return FileSystemStorage(location=root)


def document_path(instance, filename):
    # random name; the extension is set by the server after checking the real file type
    return f"persons/docs/{uuid.uuid4().hex}{os.path.splitext(filename)[1].lower()}"


class Education(models.Model):
    person = models.ForeignKey(Person, on_delete=models.CASCADE, related_name="educations")
    degree = models.CharField("درجه", max_length=100)
    institution = models.CharField("موسسه", max_length=150)
    graduation_year = models.PositiveSmallIntegerField("د فراغت کال", null=True, blank=True)
    position = models.PositiveSmallIntegerField("ترتیب", default=0)

    class Meta:
        ordering = ["position", "id"]
        verbose_name = "تحصیلي معلومات"
        verbose_name_plural = "تحصیلي معلومات"

    def __str__(self):
        return f"{self.degree} - {self.institution}"


class PersonDocument(models.Model):
    ID_CARD, EXPERIENCE, EDUCATION = "id_card", "experience", "education"
    KINDS = [(ID_CARD, "د تذکرې کاپي"), (EXPERIENCE, "د دندې تجربې سند"), (EDUCATION, "د زده کړې سند")]

    person = models.ForeignKey(Person, on_delete=models.CASCADE, related_name="documents")
    kind = models.CharField("ډول", max_length=12, choices=KINDS)
    file = models.FileField("فایل", upload_to=document_path, storage=private_storage)
    original_name = models.CharField(max_length=120, blank=True)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]
        verbose_name = "سند"
        verbose_name_plural = "اسناد"

    @property
    def is_image(self):
        return self.file.name.lower().endswith((".jpg", ".png", ".webp"))

    def __str__(self):
        return f"{self.get_kind_display()} - {self.person}"


def complete_q():
    """'Complete' record = at least one education + job title + organization.
    Used by the Reports status filter."""
    return (Q(Exists(Education.objects.filter(person=OuterRef("pk"))))
            & ~Q(job_title="") & ~Q(organization=""))
