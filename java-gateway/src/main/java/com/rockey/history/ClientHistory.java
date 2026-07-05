package com.rockey.history;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import jakarta.persistence.UniqueConstraint;
import java.time.LocalDateTime;
import java.util.UUID;

/** Long-term memory across sessions for a customer (spec User Story 5 edge case: repeated
 * complaints). Relational data — constitution III.5, owned by Java. */
@Entity
@Table(
        name = "client_history",
        uniqueConstraints = @UniqueConstraint(columnNames = {"tenant_id", "client_email"}))
public class ClientHistory {

    @Id
    @GeneratedValue
    private UUID id;

    @Column(name = "tenant_id")
    private String tenantId;

    @Column(name = "client_email")
    private String clientEmail;

    @Column(name = "return_count")
    private int returnCount;

    @Column(name = "complaint_count")
    private int complaintCount;

    @Column(name = "escalation_count")
    private int escalationCount;

    @Column(name = "last_contact")
    private LocalDateTime lastContact;

    protected ClientHistory() {}

    public ClientHistory(String tenantId, String clientEmail) {
        this.tenantId = tenantId;
        this.clientEmail = clientEmail;
    }

    public UUID getId() {
        return id;
    }

    public String getTenantId() {
        return tenantId;
    }

    public String getClientEmail() {
        return clientEmail;
    }

    public int getReturnCount() {
        return returnCount;
    }

    public int getComplaintCount() {
        return complaintCount;
    }

    public void setComplaintCount(int complaintCount) {
        this.complaintCount = complaintCount;
    }

    public int getEscalationCount() {
        return escalationCount;
    }

    public void setEscalationCount(int escalationCount) {
        this.escalationCount = escalationCount;
    }

    public LocalDateTime getLastContact() {
        return lastContact;
    }

    public void setLastContact(LocalDateTime lastContact) {
        this.lastContact = lastContact;
    }
}
