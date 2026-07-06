package com.rockey.eligibility;

import java.io.InputStream;
import java.math.BigDecimal;
import java.util.List;
import java.util.Map;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.core.io.ClassPathResource;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Component;
import org.yaml.snakeyaml.Yaml;

/**
 * Loads per-tenant policy thresholds (constitution V.3) from the retailer's own Drive-synced
 * policy documents (constitution I.7): {@code rag_documents} rows with {@code type='policy'},
 * kept current by python-agent's Drive sync job. The return-window days and refund-amount
 * thresholds are parsed straight out of the retailer's actual Return/Complaint Policy text —
 * no separate structured config is needed since that text already states them as exact
 * numbers ("Standard return window: 21 days...", "&le; &euro;80" / "&gt; &euro;200").
 *
 * <p>Falls back to a bundled static YAML mirror ({@code vinted-policy.yaml}), alert-logged,
 * if the live documents can't be read or don't contain the expected thresholds — the same
 * static-fallback pattern as {@code agent/rag/rag_fallback.py} on the Python side
 * (constitution VI.3).
 *
 * <p>{@code legalWarrantyDays} is the one field always sourced from the bundled YAML, on
 * both the live and fallback paths: the retailer's policy text describes the legal warranty
 * only qualitatively ("regardless of the 21-day window... reported within a reasonable time
 * of discovery"), never as a specific day count, so there is nothing to extract.
 */
@Component
public class PolicyLoader {

    private static final Logger log = LoggerFactory.getLogger(PolicyLoader.class);
    private static final String RESOURCE_PATH = "policy/vinted-policy.yaml";

    private static final Pattern RETURN_WINDOW_DOMESTIC =
            Pattern.compile("(?i)standard return window:\\s*(\\d+)\\s*days?");
    private static final Pattern RETURN_WINDOW_INTERNATIONAL =
            Pattern.compile("(?i)international orders:\\s*(\\d+)\\s*days?");
    private static final Pattern AUTO_REFUND_MAX = Pattern.compile("≤\\s*€\\s*(\\d+(?:\\.\\d+)?)");
    private static final Pattern MANUAL_REVIEW_MAX = Pattern.compile(">\\s*€\\s*(\\d+(?:\\.\\d+)?)");

    private final JdbcTemplate jdbcTemplate;

    public PolicyLoader(JdbcTemplate jdbcTemplate) {
        this.jdbcTemplate = jdbcTemplate;
    }

    public PolicyThresholds load(String tenantId) {
        try {
            return loadFromRagDocuments(tenantId);
        } catch (Exception e) {
            log.error(
                    "POLICY_RAG_FALLBACK_USED tenant_id={} reason=\"{}\" — falling back to bundled policy YAML",
                    tenantId,
                    e.getMessage());
            return loadFromBundledYaml(tenantId);
        }
    }

    private PolicyThresholds loadFromRagDocuments(String tenantId) {
        List<String> chunks =
                jdbcTemplate.queryForList(
                        "SELECT content FROM rag_documents WHERE tenant_id = ? AND type = 'policy' "
                                + "ORDER BY source, chunk_index",
                        String.class,
                        tenantId);
        if (chunks == null || chunks.isEmpty()) {
            throw new IllegalStateException("no synced policy documents found for tenant " + tenantId);
        }
        String text = String.join("\n", chunks);

        int windowDomestic = extractInt(RETURN_WINDOW_DOMESTIC, text, "domestic return window");
        int windowInternational = extractInt(RETURN_WINDOW_INTERNATIONAL, text, "international return window");
        BigDecimal autoMax = extractAmount(AUTO_REFUND_MAX, text, "auto-refund threshold");
        BigDecimal manualMax = extractAmount(MANUAL_REVIEW_MAX, text, "manual-review threshold");
        if (autoMax.compareTo(manualMax) >= 0) {
            throw new IllegalStateException(
                    "parsed thresholds are not increasing (auto=" + autoMax + ", manual=" + manualMax + ")");
        }

        return new PolicyThresholds(
                windowDomestic, windowInternational, autoMax, manualMax, legalWarrantyDays(tenantId));
    }

    private static int extractInt(Pattern pattern, String text, String label) {
        Matcher matcher = pattern.matcher(text);
        if (!matcher.find()) {
            throw new IllegalStateException("could not find the " + label + " in the retailer's policy documents");
        }
        return Integer.parseInt(matcher.group(1));
    }

    private static BigDecimal extractAmount(Pattern pattern, String text, String label) {
        Matcher matcher = pattern.matcher(text);
        if (!matcher.find()) {
            throw new IllegalStateException("could not find the " + label + " in the retailer's policy documents");
        }
        return new BigDecimal(matcher.group(1)).setScale(2);
    }

    private int legalWarrantyDays(String tenantId) {
        return (int) loadYamlTenantPolicy(tenantId).get("legal_warranty_days");
    }

    private PolicyThresholds loadFromBundledYaml(String tenantId) {
        Map<String, Object> tenantPolicy = loadYamlTenantPolicy(tenantId);
        return new PolicyThresholds(
                (int) tenantPolicy.get("return_window_days_domestic"),
                (int) tenantPolicy.get("return_window_days_international"),
                new BigDecimal(tenantPolicy.get("auto_refund_max_amount").toString()),
                new BigDecimal(tenantPolicy.get("manual_review_max_amount").toString()),
                (int) tenantPolicy.get("legal_warranty_days"));
    }

    @SuppressWarnings("unchecked")
    private Map<String, Object> loadYamlTenantPolicy(String tenantId) {
        try (InputStream in = new ClassPathResource(RESOURCE_PATH).getInputStream()) {
            Map<String, Object> root = new Yaml().load(in);
            Map<String, Object> tenantPolicy = (Map<String, Object>) root.get(tenantId);
            if (tenantPolicy == null) {
                throw new IllegalStateException("No policy configured for tenant: " + tenantId);
            }
            return tenantPolicy;
        } catch (Exception e) {
            throw new IllegalStateException("Failed to load bundled policy YAML for tenant " + tenantId, e);
        }
    }
}
