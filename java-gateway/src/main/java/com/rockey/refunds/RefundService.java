package com.rockey.refunds;

import java.math.BigDecimal;
import java.util.UUID;
import org.springframework.stereotype.Service;

@Service
public class RefundService {

    /** Only ever called after eligibility + auto-approval have already been confirmed
     * (spec FR-006). A real implementation would call a payment provider; the POC returns a
     * synchronous, deterministic refund reference and processing delay. */
    public record RefundResult(String refundId, String delay) {}

    public RefundResult triggerRefund(String tenantId, String orderId, BigDecimal amount) {
        String refundId = "RFD-" + UUID.randomUUID().toString().substring(0, 8);
        return new RefundResult(refundId, "3 à 5 jours ouvrés");
    }
}
