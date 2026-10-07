"""Content and recipe identity: source_hash and fingerprint."""

from pydantic import BaseModel
from stubs import Widget

from docextract import fingerprint, source_hash
from docextract.config import ExtractionConfig


class _Other(BaseModel):
    value: str = ""


def test_source_hash_is_content_addressed():
    assert source_hash(b"hello") == source_hash(b"hello")
    assert source_hash(b"hello") != source_hash(b"hello!")
    assert len(source_hash(b"x")) == 64


def test_fingerprint_is_stable():
    config = ExtractionConfig.from_env()
    assert fingerprint(config, Widget) == fingerprint(config, Widget)


def test_fingerprint_tracks_provider_model_and_temperature():
    config = ExtractionConfig.from_env()
    base = fingerprint(config, Widget)
    assert base != fingerprint(config.replaced(model="another-model"), Widget)
    assert base != fingerprint(config.replaced(provider="openai"), Widget)
    assert base != fingerprint(config.replaced(temperature=0.9), Widget)


def test_fingerprint_tracks_schema():
    config = ExtractionConfig.from_env()
    assert fingerprint(config, Widget) != fingerprint(config, _Other)


def test_fingerprint_tracks_hint():
    config = ExtractionConfig.from_env()
    assert fingerprint(config, Widget, "hint a") != fingerprint(config, Widget, "hint b")
