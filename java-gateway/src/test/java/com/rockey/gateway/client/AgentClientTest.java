package com.rockey.gateway.client;

import static org.assertj.core.api.Assertions.assertThat;

import com.rockey.config.RockeyProperties;
import com.rockey.gateway.dto.InternalMessage;
import com.sun.net.httpserver.HttpServer;
import java.io.IOException;
import java.io.OutputStream;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.atomic.AtomicReference;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;

/** AgentClient is the Java Gateway's only entry point into the Python Agent — worth a real
 * request/response round trip rather than a mock, so a lightweight embedded HTTP server
 * (JDK's own, no new test dependency) stands in for python-agent. */
class AgentClientTest {

    private HttpServer server;

    @AfterEach
    void tearDown() {
        if (server != null) {
            server.stop(0);
        }
    }

    @Test
    void happyPath_postsToVMessagesWithTheInternalTokenHeaderAndParsesTheResponse() throws IOException {
        AtomicReference<String> receivedToken = new AtomicReference<>();
        AtomicReference<String> receivedPath = new AtomicReference<>();

        server = HttpServer.create(new InetSocketAddress("localhost", 0), 0);
        server.createContext(
                "/v1/messages",
                exchange -> {
                    receivedToken.set(exchange.getRequestHeaders().getFirst("X-Internal-Token"));
                    receivedPath.set(exchange.getRequestURI().getPath());
                    String body =
                            "{\"session_id\":\"s1\",\"current_state\":\"GREETING\",\"reply\":\"Bonjour !\","
                                    + "\"attachments\":[],\"escalated\":false,\"case_id\":null}";
                    byte[] bytes = body.getBytes(StandardCharsets.UTF_8);
                    exchange.getResponseHeaders().add("Content-Type", "application/json");
                    exchange.sendResponseHeaders(200, bytes.length);
                    try (OutputStream os = exchange.getResponseBody()) {
                        os.write(bytes);
                    }
                });
        server.start();

        var properties = new RockeyProperties("test-internal-token", "http://localhost:" + server.getAddress().getPort());
        var client = new AgentClient(properties);

        var response = client.process(new InternalMessage("s1", "vinted", "web", "hello", "s1"));

        assertThat(response.reply()).isEqualTo("Bonjour !");
        assertThat(response.currentState()).isEqualTo("GREETING");
        assertThat(receivedToken.get()).isEqualTo("test-internal-token");
        assertThat(receivedPath.get()).isEqualTo("/v1/messages");
    }
}
