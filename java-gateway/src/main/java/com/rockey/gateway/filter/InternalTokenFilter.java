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
 * /internal/**} route, plus {@code /admin/**} (T082's manual RAG-sync trigger and any future
 * operator-only action) — both classes of route are only ever called by a service or a
 * trusted operator, never an end customer, so they share the same POC-stage token gate
 * rather than introducing a second credential type this early.
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
        String uri = request.getRequestURI();
        if (!uri.startsWith("/internal/") && !uri.startsWith("/admin/")) {
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
