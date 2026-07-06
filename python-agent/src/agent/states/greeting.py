"""GREETING node (spec User Story 1, AC1-2): introduces the agent under the retailer's
persona and asks for the order number + email in the same reply."""

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

    return {**state, "current_state": "GREETING", "reply": reply}
