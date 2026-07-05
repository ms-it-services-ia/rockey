package com.rockey.eligibility;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.when;

import com.rockey.order.Order;
import com.rockey.order.OrderRepository;
import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.Optional;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

@ExtendWith(MockitoExtension.class)
class EligibilityServiceTest {

    @Mock private OrderRepository orderRepository;

    private EligibilityService eligibilityService;

    @BeforeEach
    void setUp() {
        eligibilityService = new EligibilityService(orderRepository, new PolicyLoader());
    }

    private Order buildOrder(BigDecimal amount, LocalDate deliveryDate) throws Exception {
        var constructor = Order.class.getDeclaredConstructor();
        constructor.setAccessible(true);
        Order order = constructor.newInstance();
        setField(order, "id", "CMD-2026-00001");
        setField(order, "tenantId", "vinted");
        setField(order, "amount", amount);
        setField(order, "deliveryDate", deliveryDate);
        return order;
    }

    private void setField(Object target, String name, Object value) throws Exception {
        var field = Order.class.getDeclaredField(name);
        field.setAccessible(true);
        field.set(target, value);
    }

    @Test
    void happyPath_eligibleAndAutoApprovable_belowThreshold() throws Exception {
        Order order = buildOrder(new BigDecimal("68.00"), LocalDate.now().minusDays(15));
        when(orderRepository.findByIdAndTenantId("CMD-2026-00001", "vinted")).thenReturn(Optional.of(order));

        var result =
                eligibilityService.checkReturnEligibility(
                        "vinted",
                        "CMD-2026-00001",
                        new EligibilityService.ArticleEligibilityInput(true, null),
                        false);

        assertThat(result.eligible()).isTrue();
        assertThat(result.autoApprovable()).isTrue();
        assertThat(result.appliedRule()).contains("auto_refund_threshold");
    }

    @Test
    void edgeCase_returnWindowExceeded_isIneligible() throws Exception {
        Order order = buildOrder(new BigDecimal("68.00"), LocalDate.now().minusDays(45));
        when(orderRepository.findByIdAndTenantId("CMD-2026-00001", "vinted")).thenReturn(Optional.of(order));

        var result =
                eligibilityService.checkReturnEligibility(
                        "vinted",
                        "CMD-2026-00001",
                        new EligibilityService.ArticleEligibilityInput(true, null),
                        false);

        assertThat(result.eligible()).isFalse();
        assertThat(result.reason()).contains("window exceeded");
    }

    @Test
    void eligibleButAboveAutoThreshold_isNotAutoApprovable() throws Exception {
        Order order = buildOrder(new BigDecimal("265.00"), LocalDate.now().minusDays(4));
        when(orderRepository.findByIdAndTenantId("CMD-2026-00001", "vinted")).thenReturn(Optional.of(order));

        var result =
                eligibilityService.checkReturnEligibility(
                        "vinted",
                        "CMD-2026-00001",
                        new EligibilityService.ArticleEligibilityInput(true, null),
                        false);

        assertThat(result.eligible()).isTrue();
        assertThat(result.autoApprovable()).isFalse();
    }
}
