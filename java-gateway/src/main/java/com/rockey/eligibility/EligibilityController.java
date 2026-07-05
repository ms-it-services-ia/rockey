package com.rockey.eligibility;

import java.util.NoSuchElementException;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

/** Backs the `verify_eligibility` MCP tool (contracts/mcp-tools.md). */
@RestController
public class EligibilityController {

    private final EligibilityService eligibilityService;

    public EligibilityController(EligibilityService eligibilityService) {
        this.eligibilityService = eligibilityService;
    }

    public record ArticleDataDto(boolean returnable, String nonReturnReason) {}

    public record EligibilityCheckRequest(
            String orderId,
            String tenantId,
            String reason,
            ArticleDataDto articleData,
            boolean isInternational) {}

    public record EligibilityCheckResponse(
            boolean eligible, boolean autoApprovable, String reason, String appliedRule) {}

    @PostMapping("/internal/eligibility/check")
    public ResponseEntity<EligibilityCheckResponse> check(@RequestBody EligibilityCheckRequest request) {
        try {
            EligibilityService.EligibilityResult result =
                    eligibilityService.checkReturnEligibility(
                            request.tenantId(),
                            request.orderId(),
                            new EligibilityService.ArticleEligibilityInput(
                                    request.articleData().returnable(), request.articleData().nonReturnReason()),
                            request.isInternational());
            return ResponseEntity.ok(
                    new EligibilityCheckResponse(
                            result.eligible(), result.autoApprovable(), result.reason(), result.appliedRule()));
        } catch (NoSuchElementException e) {
            return ResponseEntity.notFound().build();
        }
    }
}
