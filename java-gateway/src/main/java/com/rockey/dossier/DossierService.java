package com.rockey.dossier;

import java.math.BigDecimal;
import org.springframework.stereotype.Service;

/**
 * Records dossiers for outcomes that don't otherwise create one — specifically a refusal
 * (spec User Story 3/5: eligibility fails, no escalation). Approved cases are recorded by
 * {@link com.rockey.returns.ReturnService} and escalated cases by
 * {@link com.rockey.tickets.TicketService}; this fills the third gap so every processed
 * request (spec's "Case" entity) has a Dossier row regardless of outcome.
 */
@Service
public class DossierService {

    private final DossierRepository dossierRepository;

    public DossierService(DossierRepository dossierRepository) {
        this.dossierRepository = dossierRepository;
    }

    public String recordRefusal(
            String tenantId,
            String orderId,
            String articleId,
            String clientEmail,
            String type,
            String reason,
            BigDecimal amount,
            String channel,
            String sessionId,
            String appliedRule) {
        Dossier dossier = new Dossier();
        dossier.setTenantId(tenantId);
        dossier.setClientEmail(clientEmail);
        dossier.setOrderId(orderId);
        dossier.setArticleId(articleId);
        dossier.setType(type);
        dossier.setReason(reason);
        dossier.setStatus("resolved");
        dossier.setDecision("refused");
        dossier.setAmount(amount);
        dossier.setChannel(channel);
        dossier.setSessionId(sessionId);
        dossier.setAppliedRule(appliedRule);
        dossierRepository.save(dossier);

        return dossier.getId().toString();
    }
}
