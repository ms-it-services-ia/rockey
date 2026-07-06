package com.rockey.eligibility;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.when;

import java.math.BigDecimal;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.jdbc.core.JdbcTemplate;

@ExtendWith(MockitoExtension.class)
class PolicyLoaderTest {

    // A trimmed-down excerpt of the actual synced Return Policy.docx / Complaint Policy.docx
    // content (rag_documents, type='policy') — real wording, not a made-up fixture.
    private static final List<String> REAL_POLICY_CHUNKS =
            List.of(
                    "1. Return Window\n\nStandard return window: 21 days from delivery date.\n\n"
                            + "International orders: 30 days from delivery date.",
                    "2. Refund Decision Thresholds\n\nOrder amount\nDecision\n\n≤ €80\n\n"
                            + "Automatic refund — no manual review\n\n€80.01 – €200\n\n"
                            + "Manual review by SAV team\n\n> €200\n\nMandatory escalation to human agent");

    @Mock private JdbcTemplate jdbcTemplate;

    @Test
    void happyPath_parsesThresholdsFromTheRetailersActualPolicyText() {
        when(jdbcTemplate.queryForList(any(String.class), eq(String.class), eq("vinted")))
                .thenReturn(REAL_POLICY_CHUNKS);

        PolicyThresholds thresholds = new PolicyLoader(jdbcTemplate).load("vinted");

        assertThat(thresholds.returnWindowDaysDomestic()).isEqualTo(21);
        assertThat(thresholds.returnWindowDaysInternational()).isEqualTo(30);
        assertThat(thresholds.autoRefundMaxAmount()).isEqualByComparingTo(new BigDecimal("80.00"));
        assertThat(thresholds.manualReviewMaxAmount()).isEqualByComparingTo(new BigDecimal("200.00"));
        // Not stated as an exact number anywhere in the retailer's policy text (see
        // PolicyLoader's Javadoc) — always sourced from the bundled YAML.
        assertThat(thresholds.legalWarrantyDays()).isEqualTo(730);
    }

    @Test
    void edgeCase_fallsBackToTheBundledYamlWhenNoPolicyDocumentsAreSynced() {
        when(jdbcTemplate.queryForList(any(String.class), eq(String.class), eq("vinted")))
                .thenReturn(List.of());

        PolicyThresholds thresholds = new PolicyLoader(jdbcTemplate).load("vinted");

        assertThat(thresholds.returnWindowDaysDomestic()).isEqualTo(21);
        assertThat(thresholds.returnWindowDaysInternational()).isEqualTo(30);
        assertThat(thresholds.autoRefundMaxAmount()).isEqualByComparingTo(new BigDecimal("80.00"));
        assertThat(thresholds.manualReviewMaxAmount()).isEqualByComparingTo(new BigDecimal("200.00"));
        assertThat(thresholds.legalWarrantyDays()).isEqualTo(730);
    }

    @Test
    void edgeCase_fallsBackToTheBundledYamlWhenTheRetailersTextDoesNotContainTheExpectedThresholds() {
        when(jdbcTemplate.queryForList(any(String.class), eq(String.class), eq("vinted")))
                .thenReturn(List.of("This policy document was edited and no longer mentions any numbers."));

        PolicyThresholds thresholds = new PolicyLoader(jdbcTemplate).load("vinted");

        assertThat(thresholds.autoRefundMaxAmount()).isEqualByComparingTo(new BigDecimal("80.00"));
        assertThat(thresholds.manualReviewMaxAmount()).isEqualByComparingTo(new BigDecimal("200.00"));
    }

    @Test
    void edgeCase_fallsBackToTheBundledYamlWhenTheDatabaseReadFails() {
        when(jdbcTemplate.queryForList(any(String.class), eq(String.class), eq("vinted")))
                .thenThrow(new RuntimeException("connection refused"));

        PolicyThresholds thresholds = new PolicyLoader(jdbcTemplate).load("vinted");

        assertThat(thresholds.autoRefundMaxAmount()).isEqualByComparingTo(new BigDecimal("80.00"));
        assertThat(thresholds.manualReviewMaxAmount()).isEqualByComparingTo(new BigDecimal("200.00"));
    }
}
