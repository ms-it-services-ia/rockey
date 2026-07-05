package com.rockey.returns;

import java.math.BigDecimal;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

/** Backs the `create_return_label` MCP tool (contracts/mcp-tools.md). */
@RestController
public class ReturnController {

    private final ReturnService returnService;

    public ReturnController(ReturnService returnService) {
        this.returnService = returnService;
    }

    public record CreateReturnRequest(
            String tenantId,
            String orderId,
            String articleId,
            String clientEmail,
            String reason,
            BigDecimal amount,
            String channel,
            String sessionId,
            String appliedRule,
            String type) {}

    public record CreateReturnResponse(String returnId, String labelUrl) {}

    @PostMapping("/internal/returns")
    public ResponseEntity<CreateReturnResponse> create(@RequestBody CreateReturnRequest request) {
        ReturnService.ReturnResult result =
                returnService.createReturn(
                        request.tenantId(),
                        request.orderId(),
                        request.articleId(),
                        request.clientEmail(),
                        request.reason(),
                        request.amount(),
                        request.channel(),
                        request.sessionId(),
                        request.appliedRule(),
                        request.type() != null ? request.type() : "return");
        return ResponseEntity.ok(new CreateReturnResponse(result.returnId(), result.labelUrl()));
    }
}
