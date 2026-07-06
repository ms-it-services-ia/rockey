package com.rockey.refunds;

import static org.assertj.core.api.Assertions.assertThat;

import java.math.BigDecimal;
import org.junit.jupiter.api.Test;

class RefundServiceTest {

    private final RefundService refundService = new RefundService();

    @Test
    void happyPath_returnsARefundIdAndAStandardDelay() {
        var result = refundService.triggerRefund("vinted", "CMD-2026-00001", new BigDecimal("68.00"));

        assertThat(result.refundId()).startsWith("RFD-");
        assertThat(result.delay()).isEqualTo("3-5 business days");
    }

    @Test
    void edgeCase_eachCallGetsAUniqueRefundId() {
        var first = refundService.triggerRefund("vinted", "CMD-2026-00001", new BigDecimal("68.00"));
        var second = refundService.triggerRefund("vinted", "CMD-2026-00001", new BigDecimal("68.00"));

        assertThat(first.refundId()).isNotEqualTo(second.refundId());
    }
}
