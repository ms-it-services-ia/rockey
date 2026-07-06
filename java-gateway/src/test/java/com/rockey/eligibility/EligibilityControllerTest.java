package com.rockey.eligibility;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.when;

import java.util.NoSuchElementException;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

@ExtendWith(MockitoExtension.class)
class EligibilityControllerTest {

    @Mock private EligibilityService eligibilityService;

    private EligibilityController controller;

    @Test
    void happyPath_returnEligibilityChecksReturnEligibility() {
        controller = new EligibilityController(eligibilityService);
        var articleData = new EligibilityController.ArticleDataDto(true, null);
        var request =
                new EligibilityController.EligibilityCheckRequest(
                        "CMD-2026-00001", "vinted", "wrong_size", articleData, false, "return");
        when(eligibilityService.checkReturnEligibility("vinted", "CMD-2026-00001", new EligibilityService.ArticleEligibilityInput(true, null), false))
                .thenReturn(new EligibilityService.EligibilityResult(true, true, "Eligible for return", "auto_refund_threshold:80.00"));

        var response = controller.check(request);

        assertThat(response.getStatusCode().is2xxSuccessful()).isTrue();
        assertThat(response.getBody().eligible()).isTrue();
        assertThat(response.getBody().appliedRule()).isEqualTo("auto_refund_threshold:80.00");
    }

    @Test
    void edgeCase_complaintTypeChecksComplaintEligibilityAndInvertsEscalationFlag() {
        controller = new EligibilityController(eligibilityService);
        var articleData = new EligibilityController.ArticleDataDto(true, null);
        var request =
                new EligibilityController.EligibilityCheckRequest(
                        "CMD-2026-00003", "vinted", "defective", articleData, false, "complaint");
        when(eligibilityService.checkComplaintEligibility("vinted", "CMD-2026-00003", false))
                .thenReturn(new EligibilityService.ComplaintEligibilityResult(true, true, "Eligible complaint", "manual_review_threshold:200.00"));

        var response = controller.check(request);

        assertThat(response.getBody().eligible()).isTrue();
        // requiresEscalation=true -> autoApprovable must be the inverse (not auto-approvable).
        assertThat(response.getBody().autoApprovable()).isFalse();
    }

    @Test
    void edgeCase_orderNotFoundReturns404() {
        controller = new EligibilityController(eligibilityService);
        var articleData = new EligibilityController.ArticleDataDto(true, null);
        var request =
                new EligibilityController.EligibilityCheckRequest(
                        "CMD-9999999", "vinted", "wrong_size", articleData, false, "return");
        when(eligibilityService.checkReturnEligibility("vinted", "CMD-9999999", new EligibilityService.ArticleEligibilityInput(true, null), false))
                .thenThrow(new NoSuchElementException("Order not found: CMD-9999999"));

        var response = controller.check(request);

        assertThat(response.getStatusCode().value()).isEqualTo(404);
    }
}
