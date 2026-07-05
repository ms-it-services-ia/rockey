package com.rockey.history;

import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

/** Backs `history_store.py`'s repeated-complaint detection (spec User Story 5). Relational
 * data (constitution III.5) — Python never queries client_history directly. */
@RestController
public class ClientHistoryController {

    private final ClientHistoryService clientHistoryService;

    public ClientHistoryController(ClientHistoryService clientHistoryService) {
        this.clientHistoryService = clientHistoryService;
    }

    public record RecordComplaintRequest(String tenantId, String clientEmail) {}

    public record RecordComplaintResponse(int priorComplaintCount, boolean isRepeat) {}

    @PostMapping("/internal/client-history/complaint")
    public ResponseEntity<RecordComplaintResponse> recordComplaint(@RequestBody RecordComplaintRequest request) {
        ClientHistoryService.ComplaintRecordResult result =
                clientHistoryService.recordComplaint(request.tenantId(), request.clientEmail());
        return ResponseEntity.ok(new RecordComplaintResponse(result.priorComplaintCount(), result.isRepeat()));
    }
}
