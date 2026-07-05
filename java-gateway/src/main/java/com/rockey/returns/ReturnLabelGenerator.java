package com.rockey.returns;

import java.util.UUID;
import org.springframework.stereotype.Component;

/** Generates a return label reference. A real implementation would call a shipping carrier
 * API; for the POC this produces a stable, unique label URL synchronously (constitution I.4
 * — synchronous REST, no Kafka/async queue needed at this scale). */
@Component
public class ReturnLabelGenerator {

    public String generate(String orderId) {
        String labelId = "LBL-" + orderId + "-" + UUID.randomUUID().toString().substring(0, 8);
        return "https://labels.rockey.local/" + labelId + ".pdf";
    }
}
