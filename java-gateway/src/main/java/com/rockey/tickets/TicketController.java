package com.rockey.tickets;

import java.math.BigDecimal;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

/** Backs the `escalate_to_human` MCP tool's ticket-creation step (contracts/mcp-tools.md). */
@RestController
public class TicketController {

    private final TicketService ticketService;

    public TicketController(TicketService ticketService) {
        this.ticketService = ticketService;
    }

    public record CreateTicketRequest(
            String tenantId,
            String orderId,
            String clientEmail,
            String reason,
            String summary,
            BigDecimal amount,
            String channel,
            String sessionId) {}

    public record CreateTicketResponse(String ticketId, String delay) {}

    @PostMapping("/internal/tickets")
    public ResponseEntity<CreateTicketResponse> create(@RequestBody CreateTicketRequest request) {
        TicketService.TicketResult result =
                ticketService.createTicket(
                        request.tenantId(),
                        request.orderId(),
                        request.clientEmail(),
                        request.reason(),
                        request.summary(),
                        request.amount(),
                        request.channel(),
                        request.sessionId());
        return ResponseEntity.ok(new CreateTicketResponse(result.ticketId(), result.delay()));
    }
}
