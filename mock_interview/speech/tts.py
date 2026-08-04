import io
import importlib.util
import wave
from functools import lru_cache
from pathlib import Path

from django.conf import settings
from django.core.files.base import ContentFile


class TextToSpeechError(RuntimeError):
    pass


@lru_cache(maxsize=4)
def _kokoro_pipeline(language_code):
    try:
        from kokoro_onnx import KPipeline
    except ImportError as exc:
        raise TextToSpeechError(
            "Kokoro is not installed. Install the documented open-source TTS "
            "dependencies before generating interviewer audio."
        ) from exc
    return KPipeline(lang_code=language_code)


def _kokoro_onnx_paths():
    return (
        Path(settings.MOCK_INTERVIEW.get("KOKORO_ONNX_MODEL", "")),
        Path(settings.MOCK_INTERVIEW.get("KOKORO_ONNX_VOICES", "")),
    )


def _kokoro_onnx_ready():
    model_path, voices_path = _kokoro_onnx_paths()
    return (
        importlib.util.find_spec("kokoro_onnx") is not None
        and model_path.is_file()
        and voices_path.is_file()
    )


@lru_cache(maxsize=1)
def _kokoro_onnx_model(model_path, voices_path):
    try:
        from kokoro_onnx import Kokoro
    except ImportError as exc:
        raise TextToSpeechError(
            "Kokoro ONNX is not installed for this Python runtime."
        ) from exc
    try:
        return Kokoro(model_path, voices_path)
    except Exception as exc:
        raise TextToSpeechError(f"Kokoro ONNX could not be loaded: {exc}") from exc


def _selected_backend():
    configured = settings.MOCK_INTERVIEW.get("TTS_BACKEND", "auto").lower()
    if configured != "auto":
        if configured == "kokoro" and importlib.util.find_spec("kokoro") is None:
            return "kokoro_onnx" if _kokoro_onnx_ready() else "kokoro"
        return configured
    if importlib.util.find_spec("kokoro") is not None:
        return "kokoro"
    if _kokoro_onnx_ready():
        return "kokoro_onnx"
    if importlib.util.find_spec("piper") is not None:
        return "piper"
    return "unavailable"


def tts_status():
    backend = _selected_backend()
    if backend == "kokoro":
        return {"engine": "kokoro", "ready": True}
    if backend == "kokoro_onnx":
        return {"engine": "kokoro-onnx", "ready": _kokoro_onnx_ready()}
    if backend == "piper":
        model_path = Path(
            settings.MOCK_INTERVIEW.get("PIPER_VOICE_MODEL", "")
        )
        return {
            "engine": "piper",
            "ready": model_path.is_file()
            and Path(f"{model_path}.json").is_file(),
        }
    return {"engine": backend, "ready": False}


def _synthesize_kokoro(text, voice):
    try:
        import numpy as np
        import soundfile as sf
    except ImportError as exc:
        raise TextToSpeechError(
            "Kokoro audio generation requires numpy and soundfile."
        ) from exc

    pipeline = _kokoro_pipeline("a")
    try:
        chunks = []
        for _, _, audio in pipeline(
            text,
            voice=voice,
            speed=float(settings.MOCK_INTERVIEW.get("TTS_SPEED", 0.95)),
        ):
            chunks.append(np.asarray(audio, dtype=np.float32))
        if not chunks:
            raise TextToSpeechError("Kokoro returned no audio.")
        buffer = io.BytesIO()
        sf.write(buffer, np.concatenate(chunks), 24000, format="WAV")
    except TextToSpeechError:
        raise
    except Exception as exc:
        raise TextToSpeechError(f"Question speech generation failed: {exc}") from exc

    return buffer.getvalue()


def _synthesize_kokoro_onnx(text, voice):
    try:
        import soundfile as sf
    except ImportError as exc:
        raise TextToSpeechError(
            "Kokoro ONNX audio generation requires soundfile."
        ) from exc
    model_path, voices_path = _kokoro_onnx_paths()
    if not _kokoro_onnx_ready():
        raise TextToSpeechError(
            "Kokoro ONNX model or voice files are missing."
        )
    try:
        model = _kokoro_onnx_model(str(model_path), str(voices_path))
        samples, sample_rate = model.create(
            text,
            voice=voice,
            speed=float(settings.MOCK_INTERVIEW.get("TTS_SPEED", 0.95)),
            lang="en-us",
        )
        buffer = io.BytesIO()
        sf.write(buffer, samples, sample_rate, format="WAV")
    except TextToSpeechError:
        raise
    except Exception as exc:
        raise TextToSpeechError(
            f"Kokoro ONNX speech generation failed: {exc}"
        ) from exc
    return buffer.getvalue()


@lru_cache(maxsize=2)
def _piper_voice(model_path):
    try:
        from piper import PiperVoice
    except ImportError as exc:
        raise TextToSpeechError(
            "Piper TTS is not installed for this Python runtime."
        ) from exc
    return PiperVoice.load(model_path)


def _synthesize_piper(text):
    model_path = Path(
        settings.MOCK_INTERVIEW.get("PIPER_VOICE_MODEL", "")
    )
    if not model_path.is_file() or not Path(f"{model_path}.json").is_file():
        raise TextToSpeechError(
            "Piper voice files are missing. Configure "
            "MOCK_INTERVIEW_PIPER_VOICE_MODEL."
        )
    buffer = io.BytesIO()
    try:
        with wave.open(buffer, "wb") as wav_file:
            _piper_voice(str(model_path)).synthesize_wav(text, wav_file)
    except Exception as exc:
        raise TextToSpeechError(f"Piper speech generation failed: {exc}") from exc
    return buffer.getvalue()


def synthesize_question(question):
    if question.audio_file:
        return question.audio_file
    if question.session.language_mode != "en":
        raise TextToSpeechError(
            "Tamil TTS requires the separately deployed AI4Bharat Indic-TTS service."
        )
    backend = _selected_backend()
    if backend == "kokoro":
        voice = question.session.interviewer_voice or settings.MOCK_INTERVIEW.get(
            "KOKORO_VOICE", "af_heart"
        )
        audio_bytes = _synthesize_kokoro(question.question_text, voice)
    elif backend == "kokoro_onnx":
        voice = question.session.interviewer_voice or settings.MOCK_INTERVIEW.get(
            "KOKORO_VOICE", "af_heart"
        )
        audio_bytes = _synthesize_kokoro_onnx(question.question_text, voice)
    elif backend == "piper":
        audio_bytes = _synthesize_piper(question.question_text)
    else:
        raise TextToSpeechError(
            "No supported local TTS backend is installed."
        )
    question.audio_file.save(
        f"question-{question.public_id}.wav",
        ContentFile(audio_bytes),
        save=True,
    )
    return question.audio_file
