package com.rockey.returns;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.when;

import java.math.BigDecimal;
import java.util.UUID;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

@ExtendWith(MockitoExtension.class)
class ReturnControllerTest {

    @Mock private ReturnService returnService;

    private ReturnController controller;

    @Test
    void happyPath_createsReturnAndReturnsIdAndLabelUrl() {
        controller = new ReturnController(returnService);
        var request =
                new ReturnController.CreateReturnRequest(
                        "vinted", "CMD-2026-00001", "VTG-001", "marie.dupont@email.com", "wrong_size", new BigDecimal("68.00"), "web", "s1", "auto_refund_threshold:80.00", "return");
        when(returnService.createReturn(
                        "vinted", "CMD-2026-00001", "VTG-001", "marie.dupont@email.com", "wrong_size", new BigDecimal("68.00"), "web", "s1", "auto_refund_threshold:80.00", "return"))
                .thenReturn(new ReturnService.ReturnResult("RET-abcd1234", "https://returns.vinted.local/LBL-abcd1234.pdf", UUID.randomUUID()));

        var response = controller.create(request);

        assertThat(response.getStatusCode().is2xxSuccessful()).isTrue();
        assertThat(response.getBody().returnId()).isEqualTo("RET-abcd1234");
        assertThat(response.getBody().labelUrl()).endsWith(".pdf");
    }

    @Test
    void edgeCase_nullTypeDefaultsToReturn() {
        // dossiers.type has a NOT NULL CHECK constraint restricted to "return"/"complaint" —
        // the controller must never forward a raw null through to the service.
        controller = new ReturnController(returnService);
        var request =
                new ReturnController.CreateReturnRequest(
                        "vinted", "CMD-2026-00001", "VTG-001", "marie.dupont@email.com", "wrong_size", new BigDecimal("68.00"), "web", "s1", "auto_refund_threshold:80.00", null);
        when(returnService.createReturn(
                        "vinted", "CMD-2026-00001", "VTG-001", "marie.dupont@email.com", "wrong_size", new BigDecimal("68.00"), "web", "s1", "auto_refund_threshold:80.00", "return"))
                .thenReturn(new ReturnService.ReturnResult("RET-efgh5678", "https://returns.vinted.local/LBL-efgh5678.pdf", UUID.randomUUID()));

        var response = controller.create(request);

        assertThat(response.getBody().returnId()).isEqualTo("RET-efgh5678");
    }
}
