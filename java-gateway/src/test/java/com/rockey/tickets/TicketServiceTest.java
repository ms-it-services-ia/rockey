package com.rockey.tickets;

import static org.assertj.core.api.Assertions.assertThat;

import com.rockey.dossier.Dossier;
import com.rockey.dossier.DossierRepository;
import java.math.BigDecimal;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class TicketServiceTest {

    @Mock private DossierRepository dossierRepository;

    private TicketService ticketService;

    @BeforeEach
    void setUp() {
        ticketService = new TicketService(dossierRepository);
        when(dossierRepository.save(org.mockito.ArgumentMatchers.any(Dossier.class)))
                .thenAnswer(invocation -> invocation.getArgument(0));
    }

    @Test
    void happyPath_createsTicketAndEscalatedDossier() {
        TicketService.TicketResult result =
                ticketService.createTicket(
                        "vinted",
                        "CMD-2026-00003",
                        "sophie.bernard@email.com",
                        "defective_item",
                        "Defective cashmere coat, amount above threshold",
                        new BigDecimal("265.00"),
                        "web",
                        "session-3");

        assertThat(result.ticketId()).startsWith("TCK-");
        assertThat(result.delay()).isNotBlank();
    }

    @Test
    void edgeCase_dossierStatusIsAlwaysEscalated_neverReversible() {
        ArgumentCaptor<Dossier> captor = ArgumentCaptor.forClass(Dossier.class);

        ticketService.createTicket(
                "vinted", "CMD-2026-00003", "sophie.bernard@email.com", "defective_item",
                "summary", new BigDecimal("265.00"), "web", "session-3");

        verify(dossierRepository).save(captor.capture());
        assertThat(captor.getValue().getStatus()).isEqualTo("escalated");
    }
}
