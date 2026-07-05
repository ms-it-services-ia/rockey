package com.rockey.tickets;

import com.rockey.dossier.Dossier;
import com.rockey.dossier.DossierRepository;
import java.math.BigDecimal;
import java.util.UUID;
import org.springframework.stereotype.Service;

/**
 * Creates the escalation ticket (spec User Story 4, constitution V.4). Only creates the
 * ticket/dossier record — the Slack notification itself is sent directly by the Python
 * Agent via the Slack MCP (see contracts/mcp-tools.md's escalate_to_human note), not by
 * this service, consistent with how the Google Drive MCP is also called directly from
 * Python rather than proxied through Java.
 */
@Service
public class TicketService {

    private final DossierRepository dossierRepository;

    public TicketService(DossierRepository dossierRepository) {
        this.dossierRepository = dossierRepository;
    }

    public record TicketResult(String ticketId, String delay) {}

    public TicketResult createTicket(
            String tenantId,
            String orderId,
            String clientEmail,
            String reason,
            String summary,
            BigDecimal amount,
            String channel,
            String sessionId) {
        String ticketId = "TCK-" + UUID.randomUUID().toString().substring(0, 8);

        Dossier dossier = new Dossier();
        dossier.setTenantId(tenantId);
        dossier.setClientEmail(clientEmail);
        dossier.setOrderId(orderId);
        dossier.setReason(reason);
        // Escalation is irreversible for the remainder of the session (constitution V.4) —
        // once a dossier is created here, its status can only ever be "escalated".
        dossier.setStatus("escalated");
        dossier.setDecision("escalated");
        dossier.setAmount(amount);
        dossier.setChannel(channel);
        dossier.setSessionId(sessionId);
        dossier.setTicketId(ticketId);
        dossierRepository.save(dossier);

        return new TicketResult(ticketId, "within 24 business hours");
    }
}
