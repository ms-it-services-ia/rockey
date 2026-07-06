package com.rockey.dossier;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.when;

import java.math.BigDecimal;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

@ExtendWith(MockitoExtension.class)
class DossierControllerTest {

    @Mock private DossierService dossierService;

    private DossierController controller;

    @Test
    void happyPath_recordsRefusalAndReturnsCaseId() {
        controller = new DossierController(dossierService);
        var request =
                new DossierController.RecordRefusalRequest(
                        "vinted",
                        "CMD-2026-00004",
                        "VTG-003",
                        "lucas.petit@email.com",
                        "return",
                        "Item excluded from returns: piece_unique",
                        new BigDecimal("210.00"),
                        "web",
                        "s4",
                        "non_returnable_article_type:piece_unique");
        when(dossierService.recordRefusal(
                        "vinted",
                        "CMD-2026-00004",
                        "VTG-003",
                        "lucas.petit@email.com",
                        "return",
                        "Item excluded from returns: piece_unique",
                        new BigDecimal("210.00"),
                        "web",
                        "s4",
                        "non_returnable_article_type:piece_unique"))
                .thenReturn("d064386e-4a18-44ca-ba31-dc2797335c3f");

        var response = controller.recordRefusal(request);

        assertThat(response.getStatusCode().is2xxSuccessful()).isTrue();
        assertThat(response.getBody().caseId()).isEqualTo("d064386e-4a18-44ca-ba31-dc2797335c3f");
    }

    @Test
    void edgeCase_nullArticleIdPropagatesThrough() {
        // A refusal reached before an article was identified (e.g. return-window check
        // failed before article lookup) still needs a Dossier row.
        controller = new DossierController(dossierService);
        var request =
                new DossierController.RecordRefusalRequest(
                        "vinted", "CMD-2026-00006", null, "julie.moreau@email.com", "return", "Return window exceeded", new BigDecimal("145.00"), "web", "s6", "return_window:21d");
        when(dossierService.recordRefusal(
                        "vinted", "CMD-2026-00006", null, "julie.moreau@email.com", "return", "Return window exceeded", new BigDecimal("145.00"), "web", "s6", "return_window:21d"))
                .thenReturn("7de53149-2007-46ff-83c7-6c6f5f24678c");

        var response = controller.recordRefusal(request);

        assertThat(response.getBody().caseId()).isEqualTo("7de53149-2007-46ff-83c7-6c6f5f24678c");
    }
}
