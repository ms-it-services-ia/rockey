package com.rockey.refunds;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.when;

import java.math.BigDecimal;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

@ExtendWith(MockitoExtension.class)
class RefundControllerTest {

    @Mock private RefundService refundService;

    private RefundController controller;

    @Test
    void happyPath_triggersRefundAndReturnsIdAndDelay() {
        controller = new RefundController(refundService);
        var request = new RefundController.TriggerRefundRequest("vinted", "CMD-2026-00001", new BigDecimal("68.00"));
        when(refundService.triggerRefund("vinted", "CMD-2026-00001", new BigDecimal("68.00")))
                .thenReturn(new RefundService.RefundResult("RFD-abcd1234", "3-5 business days"));

        var response = controller.trigger(request);

        assertThat(response.getStatusCode().is2xxSuccessful()).isTrue();
        assertThat(response.getBody().refundId()).isEqualTo("RFD-abcd1234");
        assertThat(response.getBody().delay()).isEqualTo("3-5 business days");
    }

    @Test
    void edgeCase_zeroAmountStillTriggersARefund() {
        // A free-return complaint resolution (defective item, no fee) still goes through
        // the same refund path with amount 0 — the controller must not special-case this.
        controller = new RefundController(refundService);
        var request = new RefundController.TriggerRefundRequest("vinted", "CMD-2026-00002", BigDecimal.ZERO);
        when(refundService.triggerRefund("vinted", "CMD-2026-00002", BigDecimal.ZERO))
                .thenReturn(new RefundService.RefundResult("RFD-efgh5678", "3-5 business days"));

        var response = controller.trigger(request);

        assertThat(response.getBody().refundId()).isEqualTo("RFD-efgh5678");
    }
}
