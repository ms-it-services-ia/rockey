package com.rockey.gateway.filter;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoInteractions;

import com.rockey.config.RockeyProperties;
import jakarta.servlet.FilterChain;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.mock.web.MockHttpServletRequest;
import org.springframework.mock.web.MockHttpServletResponse;

/**
 * This filter is the only gate in front of every {@code /internal/**} and {@code /admin/**}
 * route (constitution IV.2) — Spring Security itself permits all requests (see
 * SecurityConfig), so a gap here would leave the entire internal service-to-service API
 * (and the T082 admin RAG-sync trigger) open to the public internet.
 */
class InternalTokenFilterTest {

    private static final String VALID_TOKEN = "test-internal-token";

    private InternalTokenFilter filter;

    @BeforeEach
    void setUp() {
        filter = new InternalTokenFilter(new RockeyProperties(VALID_TOKEN, "http://localhost:8000"));
    }

    @Test
    void happyPath_allowsAnInternalRouteWithTheCorrectToken() throws Exception {
        MockHttpServletRequest request = new MockHttpServletRequest("GET", "/internal/tenant-config/vinted");
        request.addHeader("X-Internal-Token", VALID_TOKEN);
        MockHttpServletResponse response = new MockHttpServletResponse();
        FilterChain chain = mock(FilterChain.class);

        filter.doFilter(request, response, chain);

        verify(chain).doFilter(request, response);
    }

    @Test
    void edgeCase_rejectsAnInternalRouteWithNoToken() throws Exception {
        MockHttpServletRequest request = new MockHttpServletRequest("GET", "/internal/orders/CMD-2026-00001");
        MockHttpServletResponse response = new MockHttpServletResponse();
        FilterChain chain = mock(FilterChain.class);

        filter.doFilter(request, response, chain);

        assertThat(response.getStatus()).isEqualTo(401);
        verifyNoInteractions(chain);
    }

    @Test
    void edgeCase_rejectsAnInternalRouteWithTheWrongToken() throws Exception {
        MockHttpServletRequest request = new MockHttpServletRequest("POST", "/internal/refunds");
        request.addHeader("X-Internal-Token", "not-the-right-token");
        MockHttpServletResponse response = new MockHttpServletResponse();
        FilterChain chain = mock(FilterChain.class);

        filter.doFilter(request, response, chain);

        assertThat(response.getStatus()).isEqualTo(401);
        verifyNoInteractions(chain);
    }

    @Test
    void edgeCase_rejectsAnAdminRouteWithNoToken() throws Exception {
        MockHttpServletRequest request = new MockHttpServletRequest("POST", "/admin/rag/sync");
        MockHttpServletResponse response = new MockHttpServletResponse();
        FilterChain chain = mock(FilterChain.class);

        filter.doFilter(request, response, chain);

        assertThat(response.getStatus()).isEqualTo(401);
        verifyNoInteractions(chain);
    }

    @Test
    void happyPath_allowsAnAdminRouteWithTheCorrectToken() throws Exception {
        MockHttpServletRequest request = new MockHttpServletRequest("POST", "/admin/rag/sync");
        request.addHeader("X-Internal-Token", VALID_TOKEN);
        MockHttpServletResponse response = new MockHttpServletResponse();
        FilterChain chain = mock(FilterChain.class);

        filter.doFilter(request, response, chain);

        verify(chain).doFilter(request, response);
    }

    @Test
    void edgeCase_letsThroughNonInternalRoutesWithoutRequiringAToken() throws Exception {
        MockHttpServletRequest request = new MockHttpServletRequest("POST", "/api/v1/chat");
        MockHttpServletResponse response = new MockHttpServletResponse();
        FilterChain chain = mock(FilterChain.class);

        filter.doFilter(request, response, chain);

        verify(chain).doFilter(request, response);
    }
}
