package com.rockey.config;

import org.springframework.context.annotation.Configuration;
import org.springframework.messaging.simp.config.MessageBrokerRegistry;
import org.springframework.web.socket.config.annotation.EnableWebSocketMessageBroker;
import org.springframework.web.socket.config.annotation.StompEndpointRegistry;
import org.springframework.web.socket.config.annotation.WebSocketMessageBrokerConfigurer;

/**
 * Web Widget channel transport (constitution I.4b: "WebSocket + REST fallback"). A single
 * STOMP endpoint is registered; tenant scoping happens in the destination path
 * ({@code /app/chat/{tenantId}}) rather than the connect URL itself — Spring's STOMP support
 * doesn't parameterize the handshake endpoint, so this is the idiomatic equivalent of the
 * contract's "CONNECT /ws/chat/{tenant_id}".
 */
@Configuration
@EnableWebSocketMessageBroker
public class WebSocketConfig implements WebSocketMessageBrokerConfigurer {

    @Override
    public void configureMessageBroker(MessageBrokerRegistry registry) {
        registry.enableSimpleBroker("/topic");
        registry.setApplicationDestinationPrefixes("/app");
    }

    @Override
    public void registerStompEndpoints(StompEndpointRegistry registry) {
        registry.addEndpoint("/ws").withSockJS();
    }
}
