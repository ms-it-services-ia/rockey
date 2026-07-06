package com.rockey.order;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.when;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.Optional;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

@ExtendWith(MockitoExtension.class)
class OrderControllerTest {

    @Mock private OrderService orderService;

    private OrderController controller;

    private Order buildOrder() throws Exception {
        var constructor = Order.class.getDeclaredConstructor();
        constructor.setAccessible(true);
        Order order = constructor.newInstance();
        setField(order, "id", "CMD-2026-00001");
        setField(order, "tenantId", "vinted");
        setField(order, "clientEmail", "marie.dupont@email.com");
        setField(order, "clientName", "Marie Dupont");
        setField(order, "articleId", "VTG-001");
        setField(order, "amount", new BigDecimal("68.00"));
        setField(order, "status", "delivered");
        setField(order, "orderDate", LocalDate.now().minusDays(20));
        setField(order, "deliveryDate", LocalDate.now().minusDays(15));
        return order;
    }

    private void setField(Object target, String name, Object value) throws Exception {
        var field = Order.class.getDeclaredField(name);
        field.setAccessible(true);
        field.set(target, value);
    }

    @Test
    void happyPath_matchingOrderReturnsOrderData() throws Exception {
        controller = new OrderController(orderService);
        when(orderService.findForIdentification("vinted", "CMD-2026-00001", "marie.dupont@email.com"))
                .thenReturn(Optional.of(buildOrder()));

        var response = controller.getOrder("CMD-2026-00001", "marie.dupont@email.com", "vinted");

        assertThat(response.getStatusCode().is2xxSuccessful()).isTrue();
        assertThat(response.getBody().clientName()).isEqualTo("Marie Dupont");
        assertThat(response.getBody().articleId()).isEqualTo("VTG-001");
    }

    @Test
    void edgeCase_noMatchReturnsGeneric404RegardlessOfReason() {
        controller = new OrderController(orderService);
        when(orderService.findForIdentification("vinted", "CMD-9999999", "nobody@email.com"))
                .thenReturn(Optional.empty());

        var response = controller.getOrder("CMD-9999999", "nobody@email.com", "vinted");

        assertThat(response.getStatusCode().value()).isEqualTo(404);
        assertThat(response.getBody()).isNull();
    }
}
