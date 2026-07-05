package com.rockey.dossier;

import java.math.BigDecimal;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

/** Backs `record_refusal` (spec User Story 6, T072 — every processed request gets a
 * persisted Dossier, regardless of outcome). */
@RestController
public class DossierController {

    private final DossierService dossierService;

    public DossierController(DossierService dossierService) {
        this.dossierService = dossierService;
    }

    public record RecordRefusalRequest(
            String tenantId,
            String orderId,
            String articleId,
            String clientEmail,
            String type,
            String reason,
            BigDecimal amount,
            String channel,
            String sessionId,
            String appliedRule) {}

    public record RecordRefusalResponse(String caseId) {}

    @PostMapping("/internal/dossiers/refusal")
    public ResponseEntity<RecordRefusalResponse> recordRefusal(@RequestBody RecordRefusalRequest request) {
        String caseId =
                dossierService.recordRefusal(
                        request.tenantId(),
                        request.orderId(),
                        request.articleId(),
                        request.clientEmail(),
                        request.type(),
                        request.reason(),
                        request.amount(),
                        request.channel(),
                        request.sessionId(),
                        request.appliedRule());
        return ResponseEntity.ok(new RecordRefusalResponse(caseId));
    }
}
