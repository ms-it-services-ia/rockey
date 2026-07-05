package com.rockey.gateway.adapter;

import com.rockey.gateway.dto.InternalMessage;
import org.springframework.stereotype.Component;

/**
 * Converts the Web Widget's native message shape into the unified internal format
 * (contracts/internal-message.md). The widget's own `session_id` doubles as its
 * `client_id` — there's no separate persistent widget identity at POC stage — so
 * reconnecting with the same `session_id` within the TTL is what resumes a session
 * (spec User Story 7 AC4).
 */
@Component
public class WebChatAdapter {

    public InternalMessage toInternal(String tenantId, String sessionId, String message) {
        return new InternalMessage(sessionId, tenantId, "web", message, sessionId);
    }
}
