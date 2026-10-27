import os
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import UploadedFile
from PIL import Image, UnidentifiedImageError
from io import BytesIO
from phonenumber_field.modelfields import PhoneNumberField
from simple_history.models import HistoricalRecords
from .mangers import UserManager

# Create your models here.

def image_validator(file_field):

    """
    Validate an uploaded profile image.

    Checks that the file is at most 1 MB, that it can be read as an image and that
    its format is JPEG, PNG or WEBP. The file pointer is rewound afterwards so the
    file can still be saved.

    Args:
        file_field: The uploaded file (an open file-like object with ``size``).

    Raises:
        ValidationError: If the file is too large, is not a readable image or has
            an unsupported format.
    """

    max_size = 1 * 1024 * 1024
    allowed_format = [
        'JPEG',
        'PNG',
        'WEBP'
    ]

    if file_field.size > max_size:
        raise ValidationError('حجم فایل انتخابی بیش از حد مجاز.')
    
    try:
        file_field.seek(0)
        with Image.open(file_field) as img:
            img.verify()
    except(UnidentifiedImageError, FileNotFoundError, IsADirectoryError):
        raise ValidationError('محتوی ارسالی معتبر نمیباشد.')
    
    file_field.seek(0)
    with Image.open(file_field) as img:
        if img.format not in allowed_format:
            raise ValidationError('فرمت ارسالی معتبر نمیباشد.')
        

class User(AbstractBaseUser,PermissionsMixin):


    """
    Custom user model that logs in with a phone number.

    Built on ``AbstractBaseUser`` and ``PermissionsMixin``. The phone number is
    the login identifier (``USERNAME_FIELD``) and must be unique, as must the
    username.
    
    Attributes:
        phone: Unique phone number, used to log in.
        username: Unique display name.
        email: Email address.
        is_staff: Whether the user can access the admin site.
        is_active: Whether the account can log in; ``False`` means banned.
        is_verified: Whether the user has been verified.
        is_superuser: Whether the user has all permissions.
        created_date: When the user was created.
        updated_date: When the user was last saved.
    
    Note:
        History is recorded for every field except ``password`` and
        ``last_login``, so password hashes are never copied into the history
        table and logins do not create history records.
    """

    phone = PhoneNumberField(unique=True,max_length=13,blank=False,null=False)
    username = models.CharField(unique=True,max_length=24)
    email = models.EmailField(max_length=64, unique=True)
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_verified = models.BooleanField(default=False)
    is_superuser= models.BooleanField(default=False)
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = "phone"
    REQUIRED_FIELDS = []
    objects = UserManager()
    history = HistoricalRecords(excluded_fields=['password', 'last_login'])
    def __str__(self):
        return self.username
    
class Profile(models.Model):

    """
    Personal details of a user, linked one-to-one with ``User``.

    Attributes:
        user: The owning user; deleting the user deletes the profile.
        first_name: First name.
        last_name: Last name.
        address: Postal address (a state and city are merged into it by
            ``ProfileModelForm``).
        postal_code: Postal code.
        image: Profile picture; defaults to ``image/default.jpg`` and is
            validated by ``image_validator``.
        description: Free-text description.
        created_date: When the profile was created.
        updated_date: When the profile was last saved.
    """

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    first_name = models.CharField(max_length=24)
    last_name = models.CharField(max_length=24)
    address = models.TextField()
    postal_code = models.CharField(max_length=12)
    image = models.ImageField(upload_to="image/",default="image/default.svg",validators=[image_validator,],null=True,blank=True)
    description = models.TextField()

    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()

    def __str__(self):
        return f'{self.user}'
    
    def save(self, *args, **kwargs):

        """
        Save the profile, converting a newly uploaded image to WebP.

        If the image is a fresh upload that is not already a ``.webp`` file, it is
        re-encoded as WebP (quality 65) and renamed with a ``.webp`` extension before
        saving.

        Args:
            *args: Passed to ``Model.save``.
            **kwargs: Passed to ``Model.save``.

        Returns:
            The result of ``Model.save``.

        Note:
            Images with transparency (RGBA) keep it; every other mode is converted to
            RGB. Images already stored, including the default image, are left
            unchanged.
        """
        
        if self.image and isinstance(self.image.file, UploadedFile):

            if not self.image.name.lower().endswith('.webp'):
                self.image.seek(0)

                with Image.open(self.image) as img:
                    output_stream = BytesIO()
                    img_converted = img.convert('RGB') if img.mode != 'RGBA' else img
                    img_converted.save(output_stream, 'WEBP', quality=65)

                    base_name = os.path.splitext(self.image.name)[0]
                    new_name = f'{base_name}.webp'

                    self.image = ContentFile(output_stream.getvalue(), new_name)

        return super().save(*args, **kwargs)