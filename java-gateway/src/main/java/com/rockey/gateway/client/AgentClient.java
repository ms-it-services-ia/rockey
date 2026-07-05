package com.rockey.gateway.client;

import com.rockey.config.RockeyProperties;
import com.rockey.gateway.dto.AgentResponse;
import com.rockey.gateway.dto.InternalMessage;
import java.time.Duration;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;

/**
 * The Java Gateway's only entry point into the Python Agent — every channel adapter
 * (WebChatAdapter, EmailAdapter) converts its native message into an {@link InternalMessage}
 * and calls {@link #process(InternalMessage)}; none of them talk to the agent directly.
 * Constitution I.4: synchronous REST/JSON, 30s LLM timeout (the agent's own budget) — this
 * client's read timeout is set slightly above that so the agent's own escalation logic gets
 * a chance to respond before the Gateway gives up.
 */
@Component
public class AgentClient {

    private static final String TOKEN_HEADER = "X-Internal-Token";
    private static final Duration READ_TIMEOUT = Duration.ofSeconds(35);

    private final RestClient restClient;

    public AgentClient(RockeyProperties properties) {
        var requestFactory = new SimpleClientHttpRequestFactory();
        requestFactory.setReadTimeout(READ_TIMEOUT);

        this.restClient =
                RestClient.builder()
                        .baseUrl(properties.pythonAgentUrl())
                        .requestFactory(requestFactory)
                        .defaultHeader(TOKEN_HEADER, properties.internalServiceToken())
                        .build();
    }

    public AgentResponse process(InternalMessage message) {
        return restClient
                .post()
                .uri("/v1/messages")
                .body(message)
                .retrieve()
                .body(AgentResponse.class);
    }
}
