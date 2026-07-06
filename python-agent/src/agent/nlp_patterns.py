"""Shared keyword-matching heuristics used across qualification.py, return_flow.py, and
complaint_flow.py (documented POC simplification — a production build would use Claude for
this, per research.md §4).

Exact-phrase keyword lists are brittle: "pas reçu" doesn't match "pas encore reçu", and
"introuvable" doesn't match "je ne le trouve pas" — every fixed phrase gets outpaced by the
next real customer's wording. `mentions_non_delivery` catches this family of phrasing more
robustly by checking for a negation co-occurring with a receipt/find word, instead of only
matching a fixed set of exact substrings.
"""

_NOT_RECEIVED_EXACT_PHRASES = (
    "not received",
    "never received",
    "haven't received",
    "hasn't arrived",
    "never arrived",
    "lost",
    "missing",
    "pas reçu",
    "non reçu",
    "jamais reçu",
    "introuvable",
    "perdu",
    "n'est jamais arrivé",
    "colis perdu",
)

_NEGATIONS = ("pas", "jamais", "aucun", "sans")
_RECEIPT_WORDS = ("reçu", "arrivé", "livré", "received", "arrived", "delivered")
_FIND_WORDS = ("trouve", "trouvé", "find", "found")


def mentions_non_delivery(message: str) -> bool:
    """True if the message describes an item never received / lost / untraceable, in
    English or French, under either an exact known phrase or a negation + receipt/find word
    co-occurring anywhere in the message (e.g. "pas encore reçu", "je ne le trouve pas")."""
    lowered = message.lower()
    if any(phrase in lowered for phrase in _NOT_RECEIVED_EXACT_PHRASES):
        return True
    has_negation = any(neg in lowered for neg in _NEGATIONS)
    if not has_negation:
        return False
    return any(w in lowered for w in _RECEIPT_WORDS) or any(w in lowered for w in _FIND_WORDS)
