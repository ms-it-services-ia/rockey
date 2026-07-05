package com.rockey.returns;

import com.rockey.dossier.Dossier;
import com.rockey.dossier.DossierRepository;
import java.math.BigDecimal;
import java.util.UUID;
import org.springframework.stereotype.Service;

@Service
public class ReturnService {

    private final DossierRepository dossierRepository;
    private final ReturnLabelGenerator labelGenerator;

    public ReturnService(DossierRepository dossierRepository, ReturnLabelGenerator labelGenerator) {
        this.dossierRepository = dossierRepository;
        this.labelGenerator = labelGenerator;
    }

    public record ReturnResult(String returnId, String labelUrl, UUID dossierId) {}

    /** Only ever called after `EligibilityService` has confirmed eligibility (spec FR-005) —
     * this method does not re-check eligibility itself, it executes the decision. Also
     * reused for auto-approved complaints (spec US5 AC4: "initiates a free return plus
     * refund") — `dossierType` records which one this actually was. */
    public ReturnResult createReturn(
            String tenantId,
            String orderId,
            String articleId,
            String clientEmail,
            String reason,
            BigDecimal amount,
            String channel,
            String sessionId,
            String appliedRule,
            String dossierType) {
        String labelUrl = labelGenerator.generate(orderId);
        String returnId = "RET-" + UUID.randomUUID().toString().substring(0, 8);

        Dossier dossier = new Dossier();
        dossier.setTenantId(tenantId);
        dossier.setClientEmail(clientEmail);
        dossier.setOrderId(orderId);
        dossier.setArticleId(articleId);
        dossier.setType(dossierType);
        dossier.setReason(reason);
        dossier.setStatus("resolved");
        dossier.setDecision("accepted");
        dossier.setAmount(amount);
        dossier.setChannel(channel);
        dossier.setSessionId(sessionId);
        dossier.setAppliedRule(appliedRule);
        dossier.setReturnId(returnId);
        dossierRepository.save(dossier);

        return new ReturnResult(returnId, labelUrl, dossier.getId());
    }
}
