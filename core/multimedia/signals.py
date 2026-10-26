import logging
import os

from django.db.models.signals import post_save
from django.dispatch import receiver
from imageio_ffmpeg import read_frames

from .models import Media

logger = logging.getLogger(__name__)

"""Longest video duration, in seconds, that counts as a story."""
STORY_MAX_SECONDS = 15.0


@receiver(signal=post_save, sender=Media)
def trigger_story(sender, instance, created, **kwargs):

    """
    Mark a short video as a story, or remove a video that cannot be read.

    Runs after every ``Media`` save. The video's duration is read with ffmpeg:

    * If it is ``STORY_MAX_SECONDS`` or shorter, ``is_story`` is set to ``True``
      and the change is saved with a change reason, so it appears in history.
    * If the video cannot be read, the error is logged, then the file and the
      ``Media`` record are deleted.

    Args:
        sender: The ``Media`` model class.
        instance: The media that was saved.
        created: ``True`` if the media was just created.
        **kwargs: Extra signal arguments; ``raw`` is checked.

    Note:
        Nothing happens for fixture loading (``raw``), for media without a video
        (the field is optional) or for media that is already a story. Any
        exception while reading counts as an unreadable video, so a missing or
        broken ffmpeg binary would delete uploads; check the logs after deploying.
        Media that is not a story is re-read on every save.
    """

    if kwargs.get('raw') or not instance.video or instance.is_story:
        return

    path = instance.video.path

    try:
        reader = read_frames(path)
        meta = reader.send(None)
        reader.close()
        duration = meta.get('duration')
    except Exception:
        logger.exception('Media %s: ویدیو خوانده نشد؛ فایل و رکورد حذف می‌شوند.', instance.pk)
        if os.path.exists(path):
            os.remove(path)
        instance.delete()
        return

    if duration and float(duration) <= STORY_MAX_SECONDS:
        instance.is_story = True
        instance._change_reason = 'خودکار: ویدیوی ۱۵ ثانیه یا کوتاه‌تر'
        instance.save(update_fields=['is_story', 'updated_date'])