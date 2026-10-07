"""The base prompt is domain-free; consumers compose their framing on top of it."""

from stubs import CountingModel, Widget, stub_config

from docextract import Extractor, fingerprint
from docextract.prompts import BASE_PROMPT, compose_system_prompt

DOMAIN_PROMPT = "You extract ACME invoices."


def test_base_prompt_carries_no_domain_vocabulary():
    lowered = BASE_PROMPT.lower()
    for term in ("invoice", "bill of lading", "container", "consignee", "shipper", "port of", "currency"):
        assert term not in lowered


def test_base_prompt_states_the_universal_rules():
    assert "required schema" in BASE_PROMPT
    assert "Read the whole document" in BASE_PROMPT
    assert "Transcribe only what is printed" in BASE_PROMPT


def test_compose_puts_the_domain_framing_first():
    composed = compose_system_prompt(DOMAIN_PROMPT)
    assert composed.startswith(DOMAIN_PROMPT.strip())
    assert composed.endswith(BASE_PROMPT)


def test_compose_without_a_domain_is_the_base_prompt():
    assert compose_system_prompt(None) == BASE_PROMPT
    assert compose_system_prompt("   ") == BASE_PROMPT


def test_fingerprint_includes_the_composed_prompt():
    base = fingerprint(stub_config(), Widget)
    domain = fingerprint(stub_config(), Widget, system_prompt=compose_system_prompt(DOMAIN_PROMPT))
    assert base != domain


def test_loaders_send_the_supplied_system_prompt():
    from docextract.loaders import file_messages, text_messages

    assert text_messages("body", system_prompt="DOMAIN")[0].content == "DOMAIN"
    assert file_messages("application/pdf", b"%PDF", system_prompt="DOMAIN")[0].content == "DOMAIN"


def test_extractor_composes_the_domain_prompt():
    plain = Extractor(Widget, config=stub_config(), model=CountingModel(Widget()))
    domain = Extractor(Widget, config=stub_config(), model=CountingModel(Widget()), domain_prompt=DOMAIN_PROMPT)

    assert plain.system_prompt == BASE_PROMPT
    assert domain.system_prompt.startswith(DOMAIN_PROMPT.strip())
    assert domain.system_prompt.endswith(BASE_PROMPT)
