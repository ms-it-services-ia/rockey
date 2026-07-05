package com.rockey.order;

import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;

public interface OrderRepository extends JpaRepository<Order, String> {

    /**
     * Looks up an order strictly scoped by tenant (constitution III.3) — never just by id,
     * so an order id that happens to exist for a different retailer can never be returned.
     */
    Optional<Order> findByIdAndTenantId(String id, String tenantId);
}
