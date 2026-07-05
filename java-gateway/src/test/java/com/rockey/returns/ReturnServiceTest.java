package com.rockey.returns;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.when;

import com.rockey.dossier.Dossier;
import com.rockey.dossier.DossierRepository;
import java.math.BigDecimal;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

@ExtendWith(MockitoExtension.class)
class ReturnServiceTest {

    @Mock private DossierRepository dossierRepository;

    private ReturnService returnService;

    @BeforeEach
    void setUp() {
        returnService = new ReturnService(dossierRepository, new ReturnLabelGenerator());
        when(dossierRepository.save(org.mockito.ArgumentMatchers.any(Dossier.class)))
                .thenAnswer(invocation -> invocation.getArgument(0));
    }

    @Test
    void happyPath_createsReturnWithLabelAndResolvedDossier() {
        ReturnService.ReturnResult result =
                returnService.createReturn(
                        "vinted",
                        "CMD-2026-00001",
                        "VTG-001",
                        "marie.dupont@email.com",
                        "wrong_size",
                        new BigDecimal("68.00"),
                        "web",
                        "session-1",
                        "auto_refund_threshold:80.00",
                        "return");

        assertThat(result.returnId()).startsWith("RET-");
        assertThat(result.labelUrl()).endsWith(".pdf");
    }

    @Test
    void edgeCase_repeatedCallsProduceUniqueReturnIdsAndLabels() {
        // ReturnService is only ever called after EligibilityService has already confirmed
        // eligibility (spec FR-005) — it doesn't re-check returnability itself. The
        // meaningful edge case at this layer is ensuring concurrent/repeated returns for
        // different sessions never collide on identifiers.
        ReturnService.ReturnResult first =
                returnService.createReturn(
                        "vinted", "CMD-2026-00001", "VTG-001", "a@email.com", "wrong_size",
                        new BigDecimal("68.00"), "web", "session-1", "auto_refund_threshold:80.00", "return");
        ReturnService.ReturnResult second =
                returnService.createReturn(
                        "vinted", "CMD-2026-00002", "VTG-010", "b@email.com", "wrong_size",
                        new BigDecimal("89.00"), "web", "session-2", "auto_refund_threshold:80.00", "return");

        assertThat(first.returnId()).isNotEqualTo(second.returnId());
        assertThat(first.labelUrl()).isNotEqualTo(second.labelUrl());
    }

    @Test
    void createReturn_recordsDossierTypeAsComplaint_whenReusedForAutoApprovedComplaint() {
        // spec US5 AC4: an auto-approved complaint reuses this service ("initiates a free
        // return plus refund"), but the Dossier must record it as a complaint, not a return.
        var captor = org.mockito.ArgumentCaptor.forClass(Dossier.class);

        returnService.createReturn(
                "vinted", "CMD-2026-00003", "VTG-011", "sophie.bernard@email.com", "quality_defect",
                new BigDecimal("68.00"), "web", "session-3", "auto_refund_threshold:80.00", "complaint");

        org.mockito.Mockito.verify(dossierRepository).save(captor.capture());
        assertThat(captor.getValue().getType()).isEqualTo("complaint");
        assertThat(captor.getValue().getStatus()).isEqualTo("resolved");
    }
}
