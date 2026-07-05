package com.rockey.order;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.when;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.Optional;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

@ExtendWith(MockitoExtension.class)
class OrderServiceTest {

    @Mock private OrderRepository orderRepository;

    private OrderService orderService;

    @BeforeEach
    void setUp() {
        orderService = new OrderService(orderRepository);
    }

    private Order buildOrder(String tenantId, String email) throws Exception {
        Order order = new Order();
        var idField = Order.class.getDeclaredField("id");
        idField.setAccessible(true);
        idField.set(order, "CMD-2026-00001");
        var tenantField = Order.class.getDeclaredField("tenantId");
        tenantField.setAccessible(true);
        tenantField.set(order, tenantId);
        var emailField = Order.class.getDeclaredField("clientEmail");
        emailField.setAccessible(true);
        emailField.set(order, email);
        var amountField = Order.class.getDeclaredField("amount");
        amountField.setAccessible(true);
        amountField.set(order, new BigDecimal("68.00"));
        var dateField = Order.class.getDeclaredField("orderDate");
        dateField.setAccessible(true);
        dateField.set(order, LocalDate.of(2026, 6, 10));
        return order;
    }

    @Test
    void happyPath_returnsOrder_whenTenantAndEmailMatch() throws Exception {
        Order order = buildOrder("vinted", "marie.dupont@email.com");
        when(orderRepository.findByIdAndTenantId("CMD-2026-00001", "vinted"))
                .thenReturn(Optional.of(order));

        Optional<Order> result =
                orderService.findForIdentification("vinted", "CMD-2026-00001", "marie.dupont@email.com");

        assertThat(result).isPresent();
        assertThat(result.get().getClientEmail()).isEqualTo("marie.dupont@email.com");
    }

    @Test
    void edgeCase_wrongTenant_isTreatedAsNotFound() {
        // The order belongs to a different retailer than the one making the request —
        // the repository itself won't find it because the lookup is scoped by tenantId
        // (constitution III.3), so this must surface as empty, not as a cross-tenant leak.
        when(orderRepository.findByIdAndTenantId("CMD-2026-00001", "some-other-retailer"))
                .thenReturn(Optional.empty());

        Optional<Order> result =
                orderService.findForIdentification(
                        "some-other-retailer", "CMD-2026-00001", "marie.dupont@email.com");

        assertThat(result).isEmpty();
    }

    @Test
    void edgeCase_correctTenantButWrongEmail_isTreatedAsNotFound() throws Exception {
        Order order = buildOrder("vinted", "marie.dupont@email.com");
        when(orderRepository.findByIdAndTenantId("CMD-2026-00001", "vinted"))
                .thenReturn(Optional.of(order));

        Optional<Order> result =
                orderService.findForIdentification("vinted", "CMD-2026-00001", "wrong@email.com");

        assertThat(result).isEmpty();
    }
}
