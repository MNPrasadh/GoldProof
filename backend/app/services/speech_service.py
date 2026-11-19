"""Configurable Speech-to-Text and Text-to-Speech capability reporting."""

from app.config import get_settings


def get_speech_capabilities() -> dict:
    """Report active speech and LLM providers honestly without faking unconfigured APIs."""
    settings = get_settings()
    external_llm_configured = bool(
        settings.LLM_API_KEY.strip()
        and settings.LLM_PROVIDER.lower() not in ("", "local", "local_evidence_explainer")
    )
    external_speech_configured = bool(
        settings.SPEECH_API_KEY.strip() and settings.SPEECH_PROVIDER != "browser_web_speech"
    )
    return {
        "speech_provider": settings.SPEECH_PROVIDER,
        "external_speech_configured": external_speech_configured,
        "browser_web_speech_fallback": True,
        "supported_languages": ["ta-IN", "en-IN"],
        "llm_provider": settings.LLM_PROVIDER if external_llm_configured else "local_evidence_explainer",
        "external_llm_configured": external_llm_configured,
        "text_alternative_always_available": True,
        "note": (
            "Browser Web Speech API (ta-IN / en-IN) is active for client-side microphone STT and TTS playback, "
            "with full text input/output fallback on unsupported devices."
            if not external_speech_configured
            else f"Configured speech provider: {settings.SPEECH_PROVIDER}"
        ),
    }
