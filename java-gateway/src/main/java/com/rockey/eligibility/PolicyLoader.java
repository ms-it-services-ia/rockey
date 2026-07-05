package com.rockey.eligibility;

import java.io.InputStream;
import java.math.BigDecimal;
import java.util.Map;
import org.springframework.core.io.ClassPathResource;
import org.springframework.stereotype.Component;
import org.yaml.snakeyaml.Yaml;

/** Loads per-tenant policy thresholds (constitution V.3). See vinted-policy.yaml's header
 * comment for why this is a bundled file rather than a live Drive read at this POC stage.
 * Tracked follow-up: specs/001-poc-agent/tasks.md T090 — replacing the bundled YAML with a
 * live Drive-derived source only requires changing this class; {@link EligibilityService}
 * only ever calls {@link #load(String)} and consumes the resulting {@link PolicyThresholds}.
 */
@Component
public class PolicyLoader {

    private static final String RESOURCE_PATH = "policy/vinted-policy.yaml";

    @SuppressWarnings("unchecked")
    public PolicyThresholds load(String tenantId) {
        try (InputStream in = new ClassPathResource(RESOURCE_PATH).getInputStream()) {
            Map<String, Object> root = new Yaml().load(in);
            Map<String, Object> tenantPolicy = (Map<String, Object>) root.get(tenantId);
            if (tenantPolicy == null) {
                throw new IllegalStateException("No policy configured for tenant: " + tenantId);
            }
            return new PolicyThresholds(
                    (int) tenantPolicy.get("return_window_days_domestic"),
                    (int) tenantPolicy.get("return_window_days_international"),
                    new BigDecimal(tenantPolicy.get("auto_refund_max_amount").toString()),
                    new BigDecimal(tenantPolicy.get("manual_review_max_amount").toString()));
        } catch (Exception e) {
            throw new IllegalStateException("Failed to load policy for tenant " + tenantId, e);
        }
    }
}
