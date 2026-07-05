package com.rockey.gateway.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import jakarta.validation.constraints.NotBlank;

/**
 * The unified format every channel adapter converts into before calling the Python Agent.
 * See contracts/internal-message.md. The agent never branches on anything but {@code
 * channel} itself — no channel-specific fields are added here.
 *
 * <p>Wire format is snake_case (matching the Python Agent's Pydantic model field names
 * exactly, per contracts/internal-message.md) — {@code @JsonProperty} bridges that to
 * idiomatic camelCase on the Java side.
 */
public record InternalMessage(
        @NotBlank @JsonProperty("session_id") String sessionId,
        @NotBlank @JsonProperty("tenant_id") String tenantId,
        @NotBlank String channel,
        @NotBlank String message,
        @NotBlank @JsonProperty("client_id") String clientId) {}
