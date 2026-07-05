package com.rockey.gateway.dto;

import java.util.List;

/** The Python Agent's reply, per contracts/internal-message.md. */
public record AgentResponse(
        String sessionId,
        String currentState,
        String reply,
        List<Attachment> attachments,
        boolean escalated,
        String caseId) {

    public record Attachment(String type, String url) {}
}
