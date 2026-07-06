package com.rockey.gateway.controller;

import com.rockey.gateway.dto.AgentResponse;
import com.rockey.tenant.TenantConfigRepository;
import jakarta.servlet.http.HttpServletRequest;
import java.util.List;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.slf4j.MDC;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

/**
 * Constitution VI.1: no raw technical error may ever reach the customer. Scoped to
 * {@link WebChatController} only — internal controllers (eligibility, dossiers, etc.) must
 * keep propagating real HTTP errors so the Python Agent's circuit breaker can retry/escalate.
 *
 * <p>Only ever fires for {@code handleRestFallback} — {@code @RestControllerAdvice} is a
 * Spring MVC concept and doesn't apply to {@code handleWebSocketMessage}'s STOMP mapping —
 * so the tenant is always identifiable from the {@code X-Tenant-ID} header, the same header
 * that endpoint itself requires.
 */
@RestControllerAdvice(assignableTypes = WebChatController.class)
public class ChatErrorHandler {

    private static final Logger log = LoggerFactory.getLogger(ChatErrorHandler.class);

    // Constitution VI.4: the real copy lives in the retailer's own config (tenant_config,
    // this POC's stand-in for a Drive-sourced value — see V3__add_error_messages.sql) so
    // it's never a hardcoded platform string; this is only the last-resort fallback for
    // when that lookup itself can't run (constitution VI.1 always requires *some* normalized
    // message, even if the tenant config is unreachable).
    private static final String FALLBACK_GENERIC_ERROR_MESSAGE =
            "Sorry, something went wrong on our end. Please try again in a moment.";

    private final TenantConfigRepository tenantConfigRepository;

    public ChatErrorHandler(TenantConfigRepository tenantConfigRepository) {
        this.tenantConfigRepository = tenantConfigRepository;
    }

    @ExceptionHandler(Exception.class)
    public ResponseEntity<AgentResponse> handleUnexpectedError(Exception exception, HttpServletRequest request) {
        String tenantId = request.getHeader("X-Tenant-ID");
        // Some failures (e.g. malformed JSON) happen during argument resolution, before
        // WebChatController's own MDC.put ever runs — set it here too so this log line
        // still carries tenant_id (constitution VI.1) even in that case. session_id can't be
        // recovered the same way: for handleRestFallback it lives inside the very body that
        // failed to parse.
        MDC.put("tenant_id", tenantId);
        try {
            log.error("Unhandled error while processing a chat message", exception);

            String message =
                    tenantConfigRepository
                            .findById(tenantId == null ? "" : tenantId)
                            .map(tc -> tc.getErrorMessageGeneric())
                            .filter(msg -> msg != null && !msg.isBlank())
                            .orElse(FALLBACK_GENERIC_ERROR_MESSAGE);

            return ResponseEntity.ok(new AgentResponse(null, "ERROR", message, List.of(), false, null));
        } finally {
            MDC.remove("tenant_id");
        }
    }
}
