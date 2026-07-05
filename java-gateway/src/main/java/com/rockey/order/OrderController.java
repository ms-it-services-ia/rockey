package com.rockey.order;

import java.math.BigDecimal;
import java.time.LocalDate;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

/** Internal endpoint backing the `check_order` MCP tool (contracts/mcp-tools.md). */
@RestController
public class OrderController {

    private final OrderService orderService;

    public OrderController(OrderService orderService) {
        this.orderService = orderService;
    }

    public record OrderData(
            String id,
            String tenantId,
            String clientEmail,
            String clientName,
            String articleId,
            BigDecimal amount,
            String status,
            LocalDate orderDate,
            LocalDate deliveryDate) {}

    @GetMapping("/internal/orders/{id}")
    public ResponseEntity<OrderData> getOrder(
            @PathVariable String id,
            @RequestParam String email,
            @RequestParam String tenantId) {
        return orderService
                .findForIdentification(tenantId, id, email)
                .map(
                        order ->
                                ResponseEntity.ok(
                                        new OrderData(
                                                order.getId(),
                                                order.getTenantId(),
                                                order.getClientEmail(),
                                                order.getClientName(),
                                                order.getArticleId(),
                                                order.getAmount(),
                                                order.getStatus(),
                                                order.getOrderDate(),
                                                order.getDeliveryDate())))
                // Generic 404 regardless of *why* it didn't match (wrong tenant vs. wrong
                // number/email) — constitution III.3, contracts/mcp-tools.md.
                .orElseGet(() -> ResponseEntity.notFound().build());
    }
}
