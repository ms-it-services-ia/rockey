package com.rockey.config;

import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configurers.AbstractHttpConfigurer;
import org.springframework.security.web.SecurityFilterChain;

/**
 * POC-stage security: internal endpoints are protected by {@link
 * com.rockey.gateway.filter.InternalTokenFilter}, not Spring Security's own auth chain
 * (constitution IV.2 — internal services authenticate via X-Internal-Token, not JWT).
 * CSRF is disabled since this gateway is a stateless JSON/WebSocket API.
 */
@Configuration
@EnableConfigurationProperties(RockeyProperties.class)
public class SecurityConfig {

    @Bean
    public SecurityFilterChain securityFilterChain(HttpSecurity http) throws Exception {
        http.csrf(AbstractHttpConfigurer::disable)
                .authorizeHttpRequests(
                        auth ->
                                auth.requestMatchers("/actuator/health", "/api/**", "/ws/**")
                                        .permitAll()
                                        .anyRequest()
                                        .permitAll());
        return http.build();
    }
}
