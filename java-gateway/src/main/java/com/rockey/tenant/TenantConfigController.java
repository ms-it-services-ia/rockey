package com.rockey.tenant;

import com.rockey.gateway.dto.TenantConfigResponse;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RestController;

/**
 * Exposes tenant_config (relational data) to the Python Agent — constitution III.5:
 * relational tables are only ever read via Java REST, never queried directly from Python.
 */
@RestController
public class TenantConfigController {

    private final TenantConfigRepository repository;

    public TenantConfigController(TenantConfigRepository repository) {
        this.repository = repository;
    }

    @GetMapping("/internal/tenant-config/{tenantId}")
    public ResponseEntity<TenantConfigResponse> getTenantConfig(@PathVariable String tenantId) {
        return repository
                .findById(tenantId)
                .map(
                        tc ->
                                ResponseEntity.ok(
                                        new TenantConfigResponse(
                                                tc.getTenantId(),
                                                tc.getAgentFirstName(),
                                                tc.getAgentTone(),
                                                tc.getAgentFormality(),
                                                tc.getAgentLanguage(),
                                                tc.isChannelEmailActive(),
                                                tc.isChannelSlackActive(),
                                                tc.getChannelSlackChannel(),
                                                tc.getDriveFolderId(),
                                                tc.getErrorMessageGeneric(),
                                                tc.getErrorMessageChannelUnavailable())))
                .orElseGet(() -> ResponseEntity.notFound().build());
    }
}
