from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from simple_history.models import HistoricalRecords
import magic

# Create your models here.

def content_type_validator(file_field):

    """
    Check that an uploaded file really contains a video.

    Detects the MIME type from the first 1024 bytes of the file (using
    ``python-magic``) instead of trusting the file name, and accepts MP4, AVI,
    MOV, WEBM and MKV. The file pointer is rewound afterwards so the file can
    still be saved.

    Args:
        file_field: The uploaded file (an open file-like object).

    Raises:
        ValidationError: If the detected type is not an allowed video type.

    Note:
        ``python-magic`` needs the ``libmagic`` system library to be installed.
    """

    content_type = [
        'video/mp4', # mp4
        'video/x-msvideo', # avi
        'video/quicktime', # mov
        'video/webm', # webm
        'video/x-matroska' # mkv
        ]
    file_sample = file_field.read(1024)
    file_field.seek(0)

    mime = magic.from_buffer(file_sample, mime=True)

    if mime not in content_type:
        raise ValidationError('فایل انتخابی فاقد متحوای ویدیویی است.')

class Media(models.Model):

    """
    A video uploaded by a user, optionally linked to a product.

    Short videos are turned into stories automatically (see
    ``multimedia.signals.trigger_story``), and a story can then be highlighted.

    Attributes:
        profile: The uploader; deleting the profile deletes the media.
        product: The related product (optional); deleting the product deletes
            the media.
        video: The video file (optional). Must have an allowed extension and
            video content.
        is_story: Whether the video is a story. Set automatically for videos of
            15 seconds or less.
        is_highlighted: Whether the story is highlighted. Only stories can be
            highlighted.
        created_date: When the media was created.
        updated_date: When the media was last saved.

    Note:
        The "only stories can be highlighted" rule is enforced twice: by
        ``clean`` (for forms and the admin) and by a database ``CheckConstraint``
        (for any other code). Because ``is_story`` is set after saving, a new
        upload cannot be highlighted straight away.
    """

    profile = models.ForeignKey(
        
        'accounts.Profile',
        verbose_name = 'کاربر',
        on_delete = models.CASCADE,
        related_name = 'multimedias'
    )

    product = models.ForeignKey(
        'products.Catalog',
        verbose_name = 'محصول',
        on_delete = models.CASCADE,
        related_name = 'multimedias',
        null = True,
        blank = True
    )

    video = models.FileField(
        verbose_name = 'ویدیو',
        upload_to = 'media/videos/',
        null = True,
        blank = True,
        validators = [
            FileExtensionValidator(
                allowed_extensions = [
                    'mp4','avi','mov','webm','mkv'
                ]
            ),
            content_type_validator
        ]
    )

    is_story = models.BooleanField(
        verbose_name = 'استوری',
        default = False
    )

    is_highlighted = models.BooleanField(
        verbose_name = 'هایلایت',
        default = False
    )

    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()

    class Meta:
        verbose_name = 'رسانه'
        verbose_name_plural = 'چندرسانه ای'
        ordering = ('created_date',)
        constraints = [
            models.CheckConstraint(
                check=~(models.Q(is_story=False) & models.Q(is_highlighted=True)),
                name='story_required_for_highlight'
            )
        ]   
    def __str__(self):

        return f'{self.product} - {self.is_story}'

    def clean(self):

        """
        Reject a highlighted media that is not a story.

        Raises:
            ValidationError: If ``is_highlighted`` is set while ``is_story`` is not.
                The error is attached to the ``is_highlighted`` field.

        Note:
            ``clean`` runs for forms and the admin but not on a plain ``save()``;
            the database constraint covers that case.
        """

        if not self.is_story and self.is_highlighted:
            raise ValidationError({'is_highlighted': 'تنها ویدیوهایی که استوری هستند می‌توانند هایلایت شوند.'})
                    
        super().clean()
