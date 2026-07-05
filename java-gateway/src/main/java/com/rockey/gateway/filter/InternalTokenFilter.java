package com.rockey.gateway.filter;

import com.rockey.config.RockeyProperties;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.io.IOException;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

/**
 * Enforces the {@code X-Internal-Token} header (constitution IV.2) on every {@code
 * /internal/**} route. These routes are only ever called service-to-service (by the Python
 * Agent's MCP tools) and must never be reachable by an end customer.
 */
@Component
public class InternalTokenFilter extends OncePerRequestFilter {

    private static final String TOKEN_HEADER = "X-Internal-Token";

    private final RockeyProperties properties;

    public InternalTokenFilter(RockeyProperties properties) {
        this.properties = properties;
    }

    @Override
    protected void doFilterInternal(
            HttpServletRequest request, HttpServletResponse response, FilterChain filterChain)
            throws ServletException, IOException {
        if (!request.getRequestURI().startsWith("/internal/")) {
            filterChain.doFilter(request, response);
            return;
        }

        String provided = request.getHeader(TOKEN_HEADER);
        if (provided == null || !provided.equals(properties.internalServiceToken())) {
            response.setStatus(HttpServletResponse.SC_UNAUTHORIZED);
            response.setContentType("application/json");
            response.getWriter().write("{\"error\":\"missing_or_invalid_internal_token\"}");
            return;
        }

        filterChain.doFilter(request, response);
    }
}
