package com.rockey.gateway.controller;

import com.rockey.config.RockeyProperties;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientResponseException;

/**
 * Operator-only actions (T082) — guarded by {@link com.rockey.gateway.filter.InternalTokenFilter}
 * the same way {@code /internal/**} is, since this is never customer-facing.
 *
 * <p>The actual Drive sync lives in python-agent (it owns the Drive credentials and the
 * embedding model, constitution I.7) — this just proxies the trigger there, so an operator
 * who edited the retailer's policy/catalogue docs in Drive doesn't have to restart
 * python-agent to pick up the change (the startup sync only ever runs once, and skips
 * entirely once {@code rag_documents} is non-empty).
 */
@RestController
public class AdminController {

    private final RestClient restClient;

    public AdminController(RockeyProperties properties) {
        this.restClient =
                RestClient.builder()
                        .baseUrl(properties.pythonAgentUrl())
                        .defaultHeader("X-Internal-Token", properties.internalServiceToken())
                        .build();
    }

    public record RagSyncResponse(String tenantId, int chunksIndexed, int articlesEmbedded) {}

    @PostMapping("/admin/rag/sync")
    public ResponseEntity<?> syncRag(@RequestParam("tenant_id") String tenantId) {
        try {
            RagSyncResponse result =
                    restClient
                            .post()
                            .uri(uriBuilder -> uriBuilder.path("/internal/rag/sync").queryParam("tenant_id", tenantId).build())
                            .retrieve()
                            .body(RagSyncResponse.class);
            return ResponseEntity.ok(result);
        } catch (RestClientResponseException e) {
            // Proxy python-agent's status/body as-is — the caller here is a trusted operator
            // debugging a sync, not a customer, so the real error is useful (constitution
            // VI.1's "never a raw error" is scoped to customer-facing responses).
            return ResponseEntity.status(e.getStatusCode()).body(e.getResponseBodyAsString());
        }
    }
}
