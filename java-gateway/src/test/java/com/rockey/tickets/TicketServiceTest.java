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
                        "session-3",
                        "complaint",
                        "manual_review_threshold:200.00");

        assertThat(result.ticketId()).startsWith("TCK-");
        assertThat(result.delay()).isNotBlank();
    }

    @Test
    void edgeCase_dossierStatusIsAlwaysEscalated_neverReversible() {
        ArgumentCaptor<Dossier> captor = ArgumentCaptor.forClass(Dossier.class);

        ticketService.createTicket(
                "vinted", "CMD-2026-00003", "sophie.bernard@email.com", "defective_item",
                "summary", new BigDecimal("265.00"), "web", "session-3", "complaint",
                "manual_review_threshold:200.00");

        verify(dossierRepository).save(captor.capture());
        assertThat(captor.getValue().getStatus()).isEqualTo("escalated");
    }

    @Test
    void edgeCase_dossierTypeDefaultsToReturn_whenEscalationHappensBeforeIntentIsKnown() {
        // dossiers.type has a CHECK ('return','complaint') constraint — identification/
        // qualification-failure escalations happen before intent is classified, so this
        // must never leave `type` null (regression: previously left unset, which violated
        // the DB's NOT NULL constraint and silently dropped the Dossier entirely).
        ArgumentCaptor<Dossier> captor = ArgumentCaptor.forClass(Dossier.class);

        ticketService.createTicket(
                "vinted", "CMD-2026-00003", "sophie.bernard@email.com", "identification_failed",
                "summary", new BigDecimal("265.00"), "web", "session-3", null, null);

        verify(dossierRepository).save(captor.capture());
        assertThat(captor.getValue().getType()).isEqualTo("return");
    }

    @Test
    void edgeCase_dossierPersistsAppliedRule_perConstitutionV3() {
        // Regression: previously never set at all, leaving escalated dossiers as the only
        // outcome path (vs. auto-approved/refused) with a blank applied_rule.
        ArgumentCaptor<Dossier> captor = ArgumentCaptor.forClass(Dossier.class);

        ticketService.createTicket(
                "vinted", "CMD-2026-00003", "sophie.bernard@email.com", "defective_item",
                "summary", new BigDecimal("265.00"), "web", "session-3", "complaint",
                "manual_review_threshold:200.00");

        verify(dossierRepository).save(captor.capture());
        assertThat(captor.getValue().getAppliedRule()).isEqualTo("manual_review_threshold:200.00");
    }
}
