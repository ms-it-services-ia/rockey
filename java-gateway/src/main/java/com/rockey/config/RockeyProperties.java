package com.rockey.config;

import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties(prefix = "rockey")
public record RockeyProperties(String internalServiceToken, String pythonAgentUrl) {}
