package com.rockey.refunds;

import java.math.BigDecimal;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

/** Backs the `trigger_refund` MCP tool (contracts/mcp-tools.md). */
@RestController
public class RefundController {

    private final RefundService refundService;

    public RefundController(RefundService refundService) {
        this.refundService = refundService;
    }

    public record TriggerRefundRequest(String tenantId, String orderId, BigDecimal amount) {}

    public record TriggerRefundResponse(String refundId, String delay) {}

    @PostMapping("/internal/refunds")
    public ResponseEntity<TriggerRefundResponse> trigger(@RequestBody TriggerRefundRequest request) {
        RefundService.RefundResult result =
                refundService.triggerRefund(request.tenantId(), request.orderId(), request.amount());
        return ResponseEntity.ok(new TriggerRefundResponse(result.refundId(), result.delay()));
    }
}
