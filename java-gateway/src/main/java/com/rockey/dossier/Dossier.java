package com.rockey.dossier;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.math.BigDecimal;
import java.util.UUID;

/**
 * A single return or complaint request being processed — called "Case" in spec.md and
 * "Dossier" here, matching the constitution's `dossiers` table name (data-model.md documents
 * this naming mapping explicitly).
 *
 * <p>{@code id} is generated client-side (not {@code @GeneratedValue}) so callers can read
 * it back immediately after {@code save()} without depending on a DB round-trip — several
 * services (ReturnService, TicketService, DossierService) return this id to their caller in
 * the same call.
 */
@Entity
@Table(name = "dossiers")
public class Dossier {

    @Id private UUID id = UUID.randomUUID();

    @Column(name = "tenant_id")
    private String tenantId;

    @Column(name = "client_email")
    private String clientEmail;

    @Column(name = "order_id")
    private String orderId;

    @Column(name = "article_id")
    private String articleId;

    private String type; // "return" | "complaint"
    private String reason;
    private String status; // "in_progress" | "resolved" | "escalated"
    private String decision; // "accepted" | "refused" | "escalated"
    private BigDecimal amount;
    private String channel;

    @Column(name = "session_id")
    private String sessionId;

    @Column(name = "applied_rule")
    private String appliedRule;

    @Column(name = "return_id")
    private String returnId;

    @Column(name = "refund_id")
    private String refundId;

    @Column(name = "ticket_id")
    private String ticketId;

    public UUID getId() {
        return id;
    }

    public void setTenantId(String tenantId) {
        this.tenantId = tenantId;
    }

    public void setClientEmail(String clientEmail) {
        this.clientEmail = clientEmail;
    }

    public void setOrderId(String orderId) {
        this.orderId = orderId;
    }

    public void setArticleId(String articleId) {
        this.articleId = articleId;
    }

    public String getType() {
        return type;
    }

    public void setType(String type) {
        this.type = type;
    }

    public void setReason(String reason) {
        this.reason = reason;
    }

    public String getStatus() {
        return status;
    }

    public void setStatus(String status) {
        this.status = status;
    }

    public String getDecision() {
        return decision;
    }

    public void setDecision(String decision) {
        this.decision = decision;
    }

    public void setAmount(BigDecimal amount) {
        this.amount = amount;
    }

    public void setChannel(String channel) {
        this.channel = channel;
    }

    public void setSessionId(String sessionId) {
        this.sessionId = sessionId;
    }

    public void setAppliedRule(String appliedRule) {
        this.appliedRule = appliedRule;
    }

    public String getReturnId() {
        return returnId;
    }

    public void setReturnId(String returnId) {
        this.returnId = returnId;
    }

    public String getRefundId() {
        return refundId;
    }

    public void setRefundId(String refundId) {
        this.refundId = refundId;
    }

    public String getTicketId() {
        return ticketId;
    }

    public void setTicketId(String ticketId) {
        this.ticketId = ticketId;
    }
}
