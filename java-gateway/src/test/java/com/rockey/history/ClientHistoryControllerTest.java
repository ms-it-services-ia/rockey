package com.rockey.history;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.when;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

@ExtendWith(MockitoExtension.class)
class ClientHistoryControllerTest {

    @Mock private ClientHistoryService clientHistoryService;

    private ClientHistoryController controller;

    @Test
    void happyPath_firstComplaintIsNotARepeat() {
        controller = new ClientHistoryController(clientHistoryService);
        var request = new ClientHistoryController.RecordComplaintRequest("vinted", "sophie.bernard@email.com");
        when(clientHistoryService.recordComplaint("vinted", "sophie.bernard@email.com"))
                .thenReturn(new ClientHistoryService.ComplaintRecordResult(0, false));

        var response = controller.recordComplaint(request);

        assertThat(response.getStatusCode().is2xxSuccessful()).isTrue();
        assertThat(response.getBody().priorComplaintCount()).isEqualTo(0);
        assertThat(response.getBody().isRepeat()).isFalse();
    }

    @Test
    void edgeCase_priorComplaintIsFlaggedAsRepeat() {
        controller = new ClientHistoryController(clientHistoryService);
        var request = new ClientHistoryController.RecordComplaintRequest("vinted", "sophie.bernard@email.com");
        when(clientHistoryService.recordComplaint("vinted", "sophie.bernard@email.com"))
                .thenReturn(new ClientHistoryService.ComplaintRecordResult(2, true));

        var response = controller.recordComplaint(request);

        assertThat(response.getBody().priorComplaintCount()).isEqualTo(2);
        assertThat(response.getBody().isRepeat()).isTrue();
    }
}
