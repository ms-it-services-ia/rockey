package com.rockey.gateway.adapter;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.Test;

class WebChatAdapterTest {

    private final WebChatAdapter adapter = new WebChatAdapter();

    @Test
    void happyPath_convertsToTheUnifiedInternalMessageShape() {
        var internal = adapter.toInternal("vinted", "session-123", "I'd like to return an item");

        assertThat(internal.sessionId()).isEqualTo("session-123");
        assertThat(internal.tenantId()).isEqualTo("vinted");
        assertThat(internal.channel()).isEqualTo("web");
        assertThat(internal.message()).isEqualTo("I'd like to return an item");
    }

    @Test
    void edgeCase_sessionIdDoublesAsTheClientId() {
        // spec User Story 7 AC4: reconnecting with the same session_id within the TTL is
        // what resumes a session — there's no separate persistent widget identity at POC
        // stage, so clientId must always equal sessionId.
        var internal = adapter.toInternal("vinted", "session-456", "hello");

        assertThat(internal.clientId()).isEqualTo("session-456");
    }
}
