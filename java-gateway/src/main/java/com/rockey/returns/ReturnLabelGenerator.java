package com.rockey.returns;

import java.util.UUID;
import org.springframework.stereotype.Component;

/** Generates a return label reference. A real implementation would call a shipping carrier
 * API; for the POC this produces a stable, unique label URL synchronously (constitution I.4
 * — synchronous REST, no Kafka/async queue needed at this scale).
 *
 * <p>The hostname is the retailer's own, never the platform's — constitution V.1/spec
 * FR-013 forbid ever exposing "Rockey" to the customer, and a label URL is customer-visible
 * (emailed, shown in the widget). Single-tenant POC (constitution II.1: Vinted only), so
 * this is hardcoded rather than sourced from tenant_config; a multi-tenant build would read
 * a per-retailer domain instead. */
@Component
public class ReturnLabelGenerator {

    private static final String LABEL_HOST = "https://returns.vinted.local/";

    public String generate(String orderId) {
        String labelId = "LBL-" + orderId + "-" + UUID.randomUUID().toString().substring(0, 8);
        return LABEL_HOST + labelId + ".pdf";
    }
}
