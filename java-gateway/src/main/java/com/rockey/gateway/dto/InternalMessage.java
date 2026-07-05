package com.rockey.gateway.dto;

import jakarta.validation.constraints.NotBlank;

/**
 * The unified format every channel adapter converts into before calling the Python Agent.
 * See contracts/internal-message.md. The agent never branches on anything but {@code
 * channel} itself — no channel-specific fields are added here.
 */
public record InternalMessage(
        @NotBlank String sessionId,
        @NotBlank String tenantId,
        @NotBlank String channel,
        @NotBlank String message,
        @NotBlank String clientId) {}
