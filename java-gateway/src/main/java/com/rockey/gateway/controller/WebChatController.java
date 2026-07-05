package com.rockey.gateway.controller;

import com.rockey.gateway.adapter.WebChatAdapter;
import com.rockey.gateway.client.AgentClient;
import com.rockey.gateway.dto.AgentResponse;
import com.rockey.gateway.dto.InternalMessage;
import java.util.UUID;
import org.springframework.messaging.handler.annotation.DestinationVariable;
import org.springframework.messaging.handler.annotation.MessageMapping;
import org.springframework.messaging.simp.SimpMessageHeaderAccessor;
import org.springframework.messaging.simp.SimpMessagingTemplate;
import org.springframework.stereotype.Controller;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.ResponseBody;

/**
 * Web Widget channel (constitution I.4b): WebSocket primary, REST fallback, per
 * contracts/channel-apis.md. Both paths convert through {@link WebChatAdapter} and never
 * call the Python Agent directly — {@link AgentClient} owns that.
 */
@Controller
public class WebChatController {

    private final WebChatAdapter webChatAdapter;
    private final AgentClient agentClient;
    private final SimpMessagingTemplate messagingTemplate;

    public WebChatController(
            WebChatAdapter webChatAdapter, AgentClient agentClient, SimpMessagingTemplate messagingTemplate) {
        this.webChatAdapter = webChatAdapter;
        this.agentClient = agentClient;
        this.messagingTemplate = messagingTemplate;
    }

    public record WidgetMessage(String message) {}

    @MessageMapping("/chat/{tenantId}")
    public void handleWebSocketMessage(
            @DestinationVariable String tenantId, WidgetMessage payload, SimpMessageHeaderAccessor headers) {
        String sessionId = headers.getSessionId();
        InternalMessage internal = webChatAdapter.toInternal(tenantId, sessionId, payload.message());
        AgentResponse response = agentClient.process(internal);
        messagingTemplate.convertAndSend("/topic/chat/" + sessionId, response);
    }

    public record ChatRequest(String sessionId, String message) {}

    @PostMapping("/api/v1/chat")
    @ResponseBody
    public AgentResponse handleRestFallback(
            @RequestBody ChatRequest request, @RequestHeader("X-Tenant-ID") String tenantId) {
        String sessionId = request.sessionId() != null ? request.sessionId() : UUID.randomUUID().toString();
        InternalMessage internal = webChatAdapter.toInternal(tenantId, sessionId, request.message());
        return agentClient.process(internal);
    }
}
