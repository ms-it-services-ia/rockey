package com.rockey.gateway.dto;

/** Relational data (constitution III.5) exposed to Python only via this Java REST endpoint. */
public record TenantConfigResponse(
        String tenantId,
        String agentFirstName,
        String agentTone,
        String agentFormality,
        String agentLanguage,
        boolean channelEmailActive,
        boolean channelSlackActive,
        String channelSlackChannel,
        String driveFolderId,
        String errorMessageGeneric,
        String errorMessageChannelUnavailable) {}
