import logging

from django.apps import AppConfig

logger = logging.getLogger(__name__)


class MockInterviewConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'mock_interview'

    def ready(self):
        from mock_interview.speech.stt import preload_whisper_model
        try:
            logger.info("Pre-loading Whisper model at startup...")
            preload_whisper_model()
            logger.info("Whisper model loaded successfully.")
        except Exception as exc:
            logger.warning("Could not pre-load Whisper model at startup: %s", exc)
