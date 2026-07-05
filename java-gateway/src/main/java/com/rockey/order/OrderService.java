package com.rockey.order;

import java.util.Optional;
import org.springframework.stereotype.Service;

@Service
public class OrderService {

    private final OrderRepository orderRepository;

    public OrderService(OrderRepository orderRepository) {
        this.orderRepository = orderRepository;
    }

    /**
     * Looks up an order for customer identification (spec User Story 1). Per
     * contracts/mcp-tools.md, a wrong tenant and a wrong order number/email combination MUST
     * both surface as the same generic "not found" outcome to the caller — this method
     * enforces that by returning empty in both cases rather than distinguishing them.
     */
    public Optional<Order> findForIdentification(String tenantId, String orderId, String email) {
        return orderRepository
                .findByIdAndTenantId(orderId, tenantId)
                .filter(order -> order.getClientEmail().equalsIgnoreCase(email));
    }
}
