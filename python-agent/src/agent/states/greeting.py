"""GREETING node (spec User Story 1, AC1-2): introduces the agent under the retailer's
persona and asks for the order number + email in the same reply.

Customers routinely say everything in their very first message ("Bonjour, je voudrai faire
une réclamation, mon colis n'est jamais arrivé") — but GREETING can't act on it (identifying
the customer always comes first, constitution V.2) and, before this fix, simply discarded it
outright. Buffered into `_qualification_context` instead, so QUALIFICATION can classify the
customer's actual request once identification is done, instead of only seeing whatever
(often much vaguer) message happens to come after — see qualification.py.
"""

from agent.states.qualification import append_context
from agent.tools.tenant_config_client import get_tenant_config


def _retailer_display_name(tenant_id: str) -> str:
    # tenant_config has no separate display-name column (data-model.md) — the tenant_id
    # itself is the retailer's slug (e.g. "vinted" -> "Vinted").
    return tenant_id.capitalize()


async def greeting_node(state: dict) -> dict:
    tenant_config = await get_tenant_config(state["tenant_id"])
    agent_name = tenant_config.get("agentFirstName", "the assistant")
    retailer_name = _retailer_display_name(state["tenant_id"])

    reply = (
        f"Bonjour, je suis {agent_name}, l'assistante du service client {retailer_name}. "
        "Pour commencer, pourriez-vous me communiquer votre numéro de commande ainsi que "
        "l'adresse email utilisée pour cette commande ?"
    )

    context = append_context(state, state.get("_latest_message", ""))

    return {**state, "_qualification_context": context, "current_state": "GREETING", "reply": reply}
