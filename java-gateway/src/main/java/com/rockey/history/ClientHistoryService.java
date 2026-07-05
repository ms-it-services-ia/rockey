package com.rockey.history;

import java.time.LocalDateTime;
import org.springframework.stereotype.Service;

@Service
public class ClientHistoryService {

    private final ClientHistoryRepository repository;

    public ClientHistoryService(ClientHistoryRepository repository) {
        this.repository = repository;
    }

    public record ComplaintRecordResult(int priorComplaintCount, boolean isRepeat) {}

    /** Records a new complaint contact for this customer and returns whether they've
     * complained about something before (spec User Story 5 edge case: repeated complaint on
     * the same item -> automatic escalation with history). */
    public ComplaintRecordResult recordComplaint(String tenantId, String clientEmail) {
        ClientHistory history =
                repository
                        .findByTenantIdAndClientEmail(tenantId, clientEmail)
                        .orElseGet(() -> new ClientHistory(tenantId, clientEmail));

        int priorCount = history.getComplaintCount();
        history.setComplaintCount(priorCount + 1);
        history.setLastContact(LocalDateTime.now());
        repository.save(history);

        return new ComplaintRecordResult(priorCount, priorCount > 0);
    }
}
