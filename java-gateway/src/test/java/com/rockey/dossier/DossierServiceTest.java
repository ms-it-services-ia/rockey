package com.rockey.dossier;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import java.math.BigDecimal;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

@ExtendWith(MockitoExtension.class)
class DossierServiceTest {

    @Mock private DossierRepository dossierRepository;

    private DossierService dossierService;

    @BeforeEach
    void setUp() {
        dossierService = new DossierService(dossierRepository);
        when(dossierRepository.save(org.mockito.ArgumentMatchers.any(Dossier.class)))
                .thenAnswer(invocation -> invocation.getArgument(0));
    }

    @Test
    void happyPath_recordsRefusalAsResolvedDossier() {
        String caseId =
                dossierService.recordRefusal(
                        "vinted", "CMD-2026-00004", "VTG-003", "lucas.petit@email.com", "return",
                        "Item excluded from returns: piece_unique", new BigDecimal("210.00"), "web",
                        "session-4", "non_returnable_article_type:piece_unique");

        assertThat(caseId).isNotBlank();
    }

    @Test
    void edgeCase_dossierDecisionIsAlwaysRefused() {
        ArgumentCaptor<Dossier> captor = ArgumentCaptor.forClass(Dossier.class);

        dossierService.recordRefusal(
                "vinted", "CMD-2026-00004", "VTG-003", "lucas.petit@email.com", "return",
                "Item excluded from returns: piece_unique", new BigDecimal("210.00"), "web",
                "session-4", "non_returnable_article_type:piece_unique");

        verify(dossierRepository).save(captor.capture());
        assertThat(captor.getValue().getDecision()).isEqualTo("refused");
        assertThat(captor.getValue().getStatus()).isEqualTo("resolved");
    }
}
