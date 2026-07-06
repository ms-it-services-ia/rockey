package com.rockey.tickets;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.when;

import java.math.BigDecimal;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

@ExtendWith(MockitoExtension.class)
class TicketControllerTest {

    @Mock private TicketService ticketService;

    private TicketController controller;

    @Test
    void happyPath_createsTicketAndReturnsIdAndDelay() {
        controller = new TicketController(ticketService);
        var request =
                new TicketController.CreateTicketRequest(
                        "vinted",
                        "CMD-2026-00003",
                        "sophie.bernard@email.com",
                        "amount_above_threshold",
                        "Defective coat, amount above threshold",
                        new BigDecimal("265.00"),
                        "web",
                        "s3",
                        "complaint",
                        "manual_review_threshold:200.00");
        when(ticketService.createTicket(
                        "vinted",
                        "CMD-2026-00003",
                        "sophie.bernard@email.com",
                        "amount_above_threshold",
                        "Defective coat, amount above threshold",
                        new BigDecimal("265.00"),
                        "web",
                        "s3",
                        "complaint",
                        "manual_review_threshold:200.00"))
                .thenReturn(new TicketService.TicketResult("TCK-abcd1234", "within 24 business hours"));

        var response = controller.create(request);

        assertThat(response.getStatusCode().is2xxSuccessful()).isTrue();
        assertThat(response.getBody().ticketId()).isEqualTo("TCK-abcd1234");
        assertThat(response.getBody().delay()).isEqualTo("within 24 business hours");
    }

    @Test
    void edgeCase_nullOrderIdAndAppliedRulePropagateThrough() {
        // Identification/qualification failures escalate before an order or policy decision
        // exists (constitution V.3 only requires appliedRule once a decision is reached).
        controller = new TicketController(ticketService);
        var request =
                new TicketController.CreateTicketRequest(
                        "vinted", null, "unknown", "identification_failed", "summary", BigDecimal.ZERO, "web", "s1", "return", null);
        when(ticketService.createTicket(
                        "vinted", null, "unknown", "identification_failed", "summary", BigDecimal.ZERO, "web", "s1", "return", null))
                .thenReturn(new TicketService.TicketResult("TCK-efgh5678", "within 24 business hours"));

        var response = controller.create(request);

        assertThat(response.getBody().ticketId()).isEqualTo("TCK-efgh5678");
    }
}
