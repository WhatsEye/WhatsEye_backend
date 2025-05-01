import json
import os
import random
import secrets
from io import BytesIO
from uuid import uuid4

import qrcode
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import check_password, make_password
from django.core.exceptions import ValidationError
from django.core.files import File
from django.db import models
from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from phonenumber_field.modelfields import PhoneNumberField
from PIL import Image


# models functions
def save_picture(instance, filename):
    ext = filename.split(".")[-1]
    upload_to = f"{instance.__class__.__name__}/{instance.__str__()}/picture"
    file_name = f"{instance.__str__()}__{secrets.token_hex(8)}.{ext}"
    return os.path.join(upload_to, file_name)


def save_icon(instance, filename):
    ext = filename.split(".")[-1]
    upload_to = f"{instance.__class__.__name__}/{instance.__str__()}/icon"
    file_name = f"{instance.__str__()}__{secrets.token_hex(8)}.{ext}"
    return os.path.join(upload_to, file_name)


def save_qr(instance, filename):
    ext = filename.split(".")[-1]
    upload_to = f"{instance.__class__.__name__}/{instance.__str__()}/qr_code"
    file_name = f"{instance.__str__()}__{secrets.token_hex(8)}.{ext}"
    return os.path.join(upload_to, file_name)


def generate_qr_code(instance):
    """
    Generate a QR code for the given instance.

    Args:
        instance: Model instance to generate QR code for

    Returns:
        Generated QR code image
    """
    instance.qr_code = secrets.token_hex(20)
    content = {"id": str(instance.id), "qr_code": instance.qr_code}
    content = json.dumps(content)
    try:
        qr = qrcode.QRCode(
            version=4,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=5,
        )
        qr.add_data(content)
        qr.make(fit=True)
        file_name = f"qr__{secrets.token_hex(8)}.png"
        buffer = BytesIO()
        qr_img = qr.make_image()
        qr_img.save(buffer, format="PNG")
        instance.qr_image.save(file_name, File(buffer), save=False)
    except Exception as e:
        raise ValidationError(_("Couldn't generate a QR code for the given instance."))


def resize_photo(photo_icon, size):
    """
    Resize a photo to the specified dimensions.

    Args:
        photo_icon: Photo field to resize
        size: Target size in pixels

    Returns:
        Resized image
    """
    try:
        size = (size, size)
        img = Image.open(photo_icon.path)
        img.thumbnail(size)
        img.save(photo_icon.path)
    except Exception as e:
        raise ValidationError(
            _("Couldn't Resize the photo to the specified dimensions.")
        )


# models
onDelete = models.CASCADE


class BaseUser(models.Model):
    GENDER_CHOICES = [
        ("M", "Male"),
        ("F", "Female"),
    ]
    id = models.UUIDField(default=uuid4, primary_key=True, editable=False)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, blank=False)
    birthday = models.DateField(_("birthday"), blank=False)
    phone_number = PhoneNumberField(unique=True, blank=False)

    is_confirmed = models.BooleanField(default=False)
    conform_code = models.CharField(max_length=7, blank=False, editable=False)

    first_ip = models.GenericIPAddressField(blank=False, editable=False, null=True)
    ip = models.GenericIPAddressField(blank=False, editable=False, null=True)

    created_at = models.DateTimeField(_("created"), auto_now_add=True)
    last_seen = models.DateTimeField(blank=True, null=True)

    deleted = models.BooleanField(default=False)

    photo = models.ImageField(
        _("user picture"),
        upload_to=save_picture,
        null=True,
        blank=True,
    )
    photo_icon = models.ImageField(
        _("user picture icon"),
        upload_to=save_icon,
        null=True,
        blank=True,
    )

    class Meta:
        abstract = True

    def generate_code(self):
        return random.randint(1000000, 9999999)

    @property
    def get_new_code(self):
        self.conform_code = self.generate_code()

    def clean(self, *args, **kwargs):
        super().clean()
        if self.phone_number:
            if (
                Parent.objects.exclude(pk=self.pk)
                .filter(phone_number=self.phone_number)
                .exists()
                or Child.objects.exclude(pk=self.pk)
                .filter(phone_number=self.phone_number)
                .exists()
            ):
                raise ValidationError(
                    {"phone_number": _("This phone number is already in use.")}
                )
        if self.photo:
            if self.photo.width <= 300 or self.photo.height <= 300:
                raise ValidationError(_(f"{self.photo.name}  size not valid "))

    def __str__(self):
        return f"{self.user.username} profile"


class Parent(BaseUser):
    user = models.OneToOneField(
        get_user_model(), on_delete=onDelete, related_name="parent"
    )
    qr_code = models.CharField(max_length=40, blank=False, editable=False)
    qr_image = models.ImageField(
        _("parent qr"),
        upload_to=save_qr,
        null=True,
        blank=True,
    )

    def save(self, *args, **kwargs):
        if not self.qr_code:
            generate_qr_code(self)
        if not self.conform_code:
            self.conform_code = self.generate_code()

        if not self.photo or not self.photo_icon:
            default_image = "man.png" if self.gender == "M" else "woman.png"
            default_path = f"default/{default_image}"
            self.photo = default_path
            self.photo_icon = default_path
        super().save(*args, **kwargs)

    @property
    def get_new_qr(self):
        generate_qr_code(self)

    @property
    def make_icon(self):
        resize_photo(self.photo_icon, 200)

    @property
    def my_family(self):
        return (self.father.all() | self.mother.all()).first()


class Child(BaseUser):
    user = models.OneToOneField(
        get_user_model(), on_delete=onDelete, related_name="child"
    )

    def save(self, *args, **kwargs):
        if not self.conform_code:
            self.conform_code = self.generate_code()
        if not self.photo or not self.photo_icon:
            default_image = "boy.png" if self.gender == "M" else "girl.png"
            default_path = f"default/{default_image}"
            self.photo = default_path
            self.photo_icon = default_path
        super().save(*args, **kwargs)

    @property
    def make_icon(self):
        resize_photo(self.photo_icon, 200)

    @property
    def my_family(self):
        return self.family_set.all().first()


class Family(models.Model):
    CREATER_CHOICES = [
        ("F", "Father"),
        ("M", "Mother"),
    ]
    FAMILY_STATUS_CHOICES = [
        ("M", "Married"),
        ("D", "Divorced"),
        ("S", "Single"),
        ("W", "Widowed"),
    ]
    id = models.UUIDField(default=uuid4, primary_key=True, editable=False)
    name = models.CharField(max_length=100, help_text="Family name")
    about = models.CharField(max_length=255, blank=True)
    family_status = models.CharField(
        max_length=1,
        choices=FAMILY_STATUS_CHOICES,
        default="M",
        help_text="relational status of the family",
    )

    creater = models.CharField(max_length=1, choices=CREATER_CHOICES, blank=False)
    father = models.ForeignKey(
        Parent, on_delete=onDelete, related_name="father", blank=True, null=True
    )
    mother = models.ForeignKey(
        Parent, on_delete=onDelete, related_name="mother", blank=True, null=True
    )
    kids = models.ManyToManyField(Child, blank=True)

    deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(_("created"), auto_now_add=True)
    last_updated = models.DateTimeField(_("updated"), auto_now=True)
    qr_code = models.CharField(max_length=40, blank=False, editable=False)
    qr_image = models.ImageField(
        _("parent qr"),
        upload_to=save_qr,
        null=True,
        blank=True,
    )
    photo = models.ImageField(
        _("Family picture"),
        upload_to=save_picture,
        default="default/family.png",
        blank=True,
        null=True,
    )
    photo_icon = models.ImageField(
        _("Family profil picture icon"),
        upload_to=save_icon,
        default="default/family.png",
        blank=True,
        null=True,
    )

    class Meta:
        verbose_name = "Family"
        verbose_name_plural = "Families"
        unique_together = ["father", "mother"]

    def clean(self, *args, **kwargs):
        if self.photo and not self.pk:
            if self.photo.width <= 300 or self.photo.height <= 300:
                raise ValidationError(_(f"{self.photo.name}  size not valid "))

    def save(self, *args, **kwargs):
        if not self.qr_code:
            generate_qr_code(self)
        super().save(*args, **kwargs)
        if self.photo_icon:
            resize_photo(self.photo_icon, 200)

    @property
    def get_new_qr(self):
        generate_qr_code(self)

    def __str__(self):
        return f"{self.name} Family"


class ResetPassword(models.Model):
    id = models.UUIDField(primary_key=True, editable=False, default=uuid4)
    username_email = models.CharField(max_length=100, blank=False, unique=True)
    phone_number = PhoneNumberField(blank=True, unique=True)
    code = models.CharField(max_length=7, blank=False, editable=False, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    checked = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        self.code = self.generate_code()
        if self.username_email == None and self.phone_number == None:
            raise ValidationError(
                "Should give username or email or phone number to reset password"
            )

        obj1 = ResetPassword.objects.filter(
            Q(username_email=self.username_email) | Q(phone_number=self.phone_number)
        ).first()
        if obj1 != None:
            obj1.delete()
        super().save(*args, **kwargs)

    def generate_code(self):
        return random.randint(1000000, 9999999)

    @property
    def get_new_code(self):
        self.code = self.generate_code()

    def __str__(self):
        return f" rest for {self.username_email}"
