package com.rockey.gateway.controller;

import com.rockey.gateway.dto.AgentResponse;
import java.util.List;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

/**
 * Constitution VI.1: no raw technical error may ever reach the customer. Scoped to
 * {@link WebChatController} only — internal controllers (eligibility, dossiers, etc.) must
 * keep propagating real HTTP errors so the Python Agent's circuit breaker can retry/escalate.
 */
@RestControllerAdvice(assignableTypes = WebChatController.class)
public class ChatErrorHandler {

    private static final Logger log = LoggerFactory.getLogger(ChatErrorHandler.class);

    @ExceptionHandler(Exception.class)
    public ResponseEntity<AgentResponse> handleUnexpectedError(Exception exception) {
        log.error("Unhandled error while processing a chat message", exception);
        return ResponseEntity.ok(
                new AgentResponse(
                        null,
                        "ERROR",
                        "Sorry, something went wrong on our end. Please try again in a moment.",
                        List.of(),
                        false,
                        null));
    }
}
