package com.rockey.gateway.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import java.util.List;

/** The Python Agent's reply, per contracts/internal-message.md. Wire format is snake_case,
 * matching the Python Agent's Pydantic `ChatResponse` field names exactly. */
public record AgentResponse(
        @JsonProperty("session_id") String sessionId,
        @JsonProperty("current_state") String currentState,
        String reply,
        List<Attachment> attachments,
        boolean escalated,
        @JsonProperty("case_id") String caseId) {

    public record Attachment(String type, String url) {}
}
