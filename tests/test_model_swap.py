"""Re-extraction under a new model preserves Corrections (issue #6)."""

from stubs import CountingModel, Widget, stub_config

from docextract import (
    Correction,
    Extractor,
    MemoryCache,
    MemoryCorrectionStore,
    effective_values,
)



def test_reextraction_keeps_corrections():
    cache = MemoryCache()
    corrections = MemoryCorrectionStore()

    first = Extractor(
        Widget, config=stub_config("model-a"), model=CountingModel(Widget(total="50.00")), cache=cache
    )
    result_a = first.extract_text("bytes")
    corrections.append(
        result_a.source_hash,
        "alice",
        [Correction(field_path="total", old_value="50.00", new_value="51.00")],
        base_fingerprint=result_a.fingerprint,
    )

    # Swap the model: same document, new recipe -> new cache entry, same source_hash.
    second = Extractor(
        Widget, config=stub_config("model-b"), model=CountingModel(Widget(total="52.00")), cache=cache
    )
    result_b = second.extract_text("bytes")

    assert result_b.cached is False
    assert result_b.source_hash == result_a.source_hash
    assert result_b.fingerprint != result_a.fingerprint
    assert len(corrections.corrections_for(result_b.source_hash)) == 1

    effective = effective_values(corrections, result_b.source_hash, result_b.data.model_dump())
    assert effective["total"] == "51.00"  # new extraction + existing correction
