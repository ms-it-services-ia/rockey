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
import org.springframework.jdbc.core.JdbcTemplate;

@ExtendWith(MockitoExtension.class)
class EligibilityServiceTest {

    @Mock private OrderRepository orderRepository;

    // Unstubbed: queryForList returns Mockito's default empty list, so PolicyLoader falls
    // back to the bundled YAML (constitution VI.3) — this test cares about EligibilityService's
    // rules, not PolicyLoader's live-vs-fallback source, and the YAML holds the same values
    // (21/30/80.00/200.00/730) the retailer's actual policy documents state.
    @Mock private JdbcTemplate jdbcTemplate;

    private EligibilityService eligibilityService;

    @BeforeEach
    void setUp() {
        eligibilityService = new EligibilityService(orderRepository, new PolicyLoader(jdbcTemplate));
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

    @Test
    void complaint_withinReturnWindow_belowThreshold_isEligibleAndNotEscalated() throws Exception {
        Order order = buildOrder(new BigDecimal("68.00"), LocalDate.now().minusDays(15));
        when(orderRepository.findByIdAndTenantId("CMD-2026-00001", "vinted")).thenReturn(Optional.of(order));

        var result = eligibilityService.checkComplaintEligibility("vinted", "CMD-2026-00001", false);

        assertThat(result.eligible()).isTrue();
        assertThat(result.requiresEscalation()).isFalse();
    }

    @Test
    void complaint_pastReturnWindowButWithinLegalWarranty_isEligibleButMustEscalate() throws Exception {
        // spec US5 edge case: complaint filed after the standard return window -> legal
        // warranty applies -> escalation with a note, not an automatic refusal.
        Order order = buildOrder(new BigDecimal("68.00"), LocalDate.now().minusDays(45));
        when(orderRepository.findByIdAndTenantId("CMD-2026-00001", "vinted")).thenReturn(Optional.of(order));

        var result = eligibilityService.checkComplaintEligibility("vinted", "CMD-2026-00001", false);

        assertThat(result.eligible()).isTrue();
        assertThat(result.requiresEscalation()).isTrue();
        assertThat(result.reason()).contains("legal warranty");
    }

    @Test
    void complaint_pastLegalWarranty_isIneligible() throws Exception {
        Order order = buildOrder(new BigDecimal("68.00"), LocalDate.now().minusDays(800));
        when(orderRepository.findByIdAndTenantId("CMD-2026-00001", "vinted")).thenReturn(Optional.of(order));

        var result = eligibilityService.checkComplaintEligibility("vinted", "CMD-2026-00001", false);

        assertThat(result.eligible()).isFalse();
        assertThat(result.reason()).contains("expired");
    }
}
