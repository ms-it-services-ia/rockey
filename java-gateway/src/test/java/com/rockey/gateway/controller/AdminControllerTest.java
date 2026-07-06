package com.rockey.gateway.controller;

import static org.assertj.core.api.Assertions.assertThat;

import com.rockey.config.RockeyProperties;
import com.sun.net.httpserver.HttpServer;
import java.io.IOException;
import java.io.OutputStream;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.atomic.AtomicReference;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;

class AdminControllerTest {

    private HttpServer server;

    @AfterEach
    void tearDown() {
        if (server != null) {
            server.stop(0);
        }
    }

    @Test
    void happyPath_proxiesTheSyncTriggerToPythonAgentAndReturnsTheCounts() throws IOException {
        AtomicReference<String> receivedQuery = new AtomicReference<>();
        AtomicReference<String> receivedToken = new AtomicReference<>();

        server = HttpServer.create(new InetSocketAddress("localhost", 0), 0);
        server.createContext(
                "/internal/rag/sync",
                exchange -> {
                    receivedQuery.set(exchange.getRequestURI().getQuery());
                    receivedToken.set(exchange.getRequestHeaders().getFirst("X-Internal-Token"));
                    String body = "{\"tenantId\":\"vinted\",\"chunksIndexed\":22,\"articlesEmbedded\":4}";
                    byte[] bytes = body.getBytes(StandardCharsets.UTF_8);
                    exchange.getResponseHeaders().add("Content-Type", "application/json");
                    exchange.sendResponseHeaders(200, bytes.length);
                    try (OutputStream os = exchange.getResponseBody()) {
                        os.write(bytes);
                    }
                });
        server.start();

        var properties = new RockeyProperties("test-internal-token", "http://localhost:" + server.getAddress().getPort());
        var controller = new AdminController(properties);

        var response = controller.syncRag("vinted");

        assertThat(response.getStatusCode().is2xxSuccessful()).isTrue();
        assertThat(response.getBody()).isEqualTo(new AdminController.RagSyncResponse("vinted", 22, 4));
        assertThat(receivedQuery.get()).isEqualTo("tenant_id=vinted");
        assertThat(receivedToken.get()).isEqualTo("test-internal-token");
    }

    @Test
    void edgeCase_propagatesPythonAgentsErrorStatusAndBodyRatherThanA500() throws IOException {
        // Drive not configured for this tenant -> python-agent returns 503; the operator
        // hitting this endpoint needs that real status/body, not a generic gateway error.
        server = HttpServer.create(new InetSocketAddress("localhost", 0), 0);
        server.createContext(
                "/internal/rag/sync",
                exchange -> {
                    String body = "{\"detail\":\"Google Drive is not configured\"}";
                    byte[] bytes = body.getBytes(StandardCharsets.UTF_8);
                    exchange.sendResponseHeaders(503, bytes.length);
                    try (OutputStream os = exchange.getResponseBody()) {
                        os.write(bytes);
                    }
                });
        server.start();

        var properties = new RockeyProperties("test-internal-token", "http://localhost:" + server.getAddress().getPort());
        var controller = new AdminController(properties);

        var response = controller.syncRag("vinted");

        assertThat(response.getStatusCode().value()).isEqualTo(503);
        assertThat(response.getBody().toString()).contains("Google Drive is not configured");
    }
}
