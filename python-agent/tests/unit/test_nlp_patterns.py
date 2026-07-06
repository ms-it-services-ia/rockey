"""Tests for the shared non-delivery detection heuristic (found brittle twice via live
testing: exact-phrase matching missed real customer wording variations)."""

import pytest

from agent.nlp_patterns import mentions_non_delivery


@pytest.mark.parametrize(
    "message",
    [
        "I never received my package.",
        "It's lost, tracking shows nothing.",
        "Mon article n'est pas reçu, il est introuvable.",
        "mon article n'est pas encore reçu et je ne le trouve pas",
        "je ne le trouve pas nulle part",
        "toujours pas reçu à ce jour",
        "je n'ai pas reçu mon colis",
    ],
)
def test_happy_path_detects_non_delivery_phrasing(message):
    assert mentions_non_delivery(message) is True


@pytest.mark.parametrize(
    "message",
    [
        "The dress doesn't fit, it's too small.",
        "The item arrived damaged and broken.",
        "J'ai changé d'avis, je n'en veux plus.",
        "Je trouve cet article très joli.",
    ],
)
def test_edge_case_does_not_false_positive_on_unrelated_messages(message):
    assert mentions_non_delivery(message) is False
