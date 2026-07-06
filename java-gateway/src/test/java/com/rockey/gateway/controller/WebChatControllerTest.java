package com.rockey.gateway.controller;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.rockey.gateway.adapter.WebChatAdapter;
import com.rockey.gateway.client.AgentClient;
import com.rockey.gateway.dto.AgentResponse;
import com.rockey.gateway.dto.InternalMessage;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.slf4j.MDC;
import org.springframework.messaging.simp.SimpMessageHeaderAccessor;
import org.springframework.messaging.simp.SimpMessagingTemplate;

@ExtendWith(MockitoExtension.class)
class WebChatControllerTest {

    @Mock private WebChatAdapter webChatAdapter;
    @Mock private AgentClient agentClient;
    @Mock private SimpMessagingTemplate messagingTemplate;

    private WebChatController controller;

    @Test
    void happyPath_restFallbackGeneratesASessionIdWhenNoneIsProvided() {
        controller = new WebChatController(webChatAdapter, agentClient, messagingTemplate);
        var internal = new InternalMessage("generated-id", "vinted", "web", "hello", "generated-id");
        var agentResponse = new AgentResponse(null, "GREETING", "Bonjour !", List.of(), false, null);
        when(webChatAdapter.toInternal(eq("vinted"), org.mockito.ArgumentMatchers.anyString(), eq("hello")))
                .thenReturn(internal);
        when(agentClient.process(internal)).thenReturn(agentResponse);

        var request = new WebChatController.ChatRequest(null, "hello");
        var response = controller.handleRestFallback(request, "vinted");

        assertThat(response.reply()).isEqualTo("Bonjour !");
    }

    @Test
    void edgeCase_restFallbackReusesAProvidedSessionIdForResumption() {
        // spec User Story 7 AC4: reconnecting with the same session_id resumes the session,
        // so an explicit sessionId in the request must never be replaced with a new one.
        controller = new WebChatController(webChatAdapter, agentClient, messagingTemplate);
        var internal = new InternalMessage("existing-session", "vinted", "web", "hello again", "existing-session");
        var agentResponse = new AgentResponse(null, "RETURN_FLOW", "Welcome back", List.of(), false, null);
        when(webChatAdapter.toInternal("vinted", "existing-session", "hello again")).thenReturn(internal);
        when(agentClient.process(internal)).thenReturn(agentResponse);

        var request = new WebChatController.ChatRequest("existing-session", "hello again");
        controller.handleRestFallback(request, "vinted");

        verify(webChatAdapter).toInternal("vinted", "existing-session", "hello again");
    }

    @Test
    void edgeCase_webSocketMessageIsBroadcastToTheSessionsOwnTopic() {
        controller = new WebChatController(webChatAdapter, agentClient, messagingTemplate);
        var headers = SimpMessageHeaderAccessor.create();
        headers.setSessionId("ws-session-1");
        var internal = new InternalMessage("ws-session-1", "vinted", "web", "hi", "ws-session-1");
        var agentResponse = new AgentResponse(null, "GREETING", "Bonjour !", List.of(), false, null);
        when(webChatAdapter.toInternal("vinted", "ws-session-1", "hi")).thenReturn(internal);
        when(agentClient.process(internal)).thenReturn(agentResponse);

        controller.handleWebSocketMessage("vinted", new WebChatController.WidgetMessage("hi"), headers);

        verify(messagingTemplate).convertAndSend("/topic/chat/ws-session-1", agentResponse);
    }

    @Test
    void happyPath_setsAndClearsSessionAndTenantIdInMdcForStructuredLogging() {
        // Constitution VI.1: any error logged while agentClient.process runs (e.g. by
        // ChatErrorHandler) must carry session_id/tenant_id via MDC.
        controller = new WebChatController(webChatAdapter, agentClient, messagingTemplate);
        var internal = new InternalMessage("s1", "vinted", "web", "hello", "s1");
        when(webChatAdapter.toInternal("vinted", "s1", "hello")).thenReturn(internal);
        when(agentClient.process(internal))
                .thenAnswer(
                        invocation -> {
                            assertThat(MDC.get("session_id")).isEqualTo("s1");
                            assertThat(MDC.get("tenant_id")).isEqualTo("vinted");
                            return new AgentResponse(null, "GREETING", "Bonjour !", List.of(), false, null);
                        });

        controller.handleRestFallback(new WebChatController.ChatRequest("s1", "hello"), "vinted");

        assertThat(MDC.get("session_id")).isNull();
        assertThat(MDC.get("tenant_id")).isNull();
    }

    @Test
    void edgeCase_clearsMdcEvenWhenAgentClientThrows() {
        controller = new WebChatController(webChatAdapter, agentClient, messagingTemplate);
        var internal = new InternalMessage("s2", "vinted", "web", "hello", "s2");
        when(webChatAdapter.toInternal("vinted", "s2", "hello")).thenReturn(internal);
        when(agentClient.process(internal)).thenThrow(new RuntimeException("boom"));

        try {
            controller.handleRestFallback(new WebChatController.ChatRequest("s2", "hello"), "vinted");
        } catch (RuntimeException expected) {
            // ChatErrorHandler normally catches this; irrelevant to this MDC-cleanup test.
        }

        assertThat(MDC.get("session_id")).isNull();
        assertThat(MDC.get("tenant_id")).isNull();
    }
}
