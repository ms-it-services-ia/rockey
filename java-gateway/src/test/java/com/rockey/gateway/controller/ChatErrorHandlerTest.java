package com.rockey.gateway.controller;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.when;

import com.rockey.tenant.TenantConfig;
import com.rockey.tenant.TenantConfigRepository;
import java.util.Optional;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.mock.web.MockHttpServletRequest;

@ExtendWith(MockitoExtension.class)
class ChatErrorHandlerTest {

    @Mock private TenantConfigRepository tenantConfigRepository;

    private ChatErrorHandler handler;

    private TenantConfig buildTenantConfig(String errorMessageGeneric) throws Exception {
        var constructor = TenantConfig.class.getDeclaredConstructor();
        constructor.setAccessible(true);
        TenantConfig tc = constructor.newInstance();
        var field = TenantConfig.class.getDeclaredField("errorMessageGeneric");
        field.setAccessible(true);
        field.set(tc, errorMessageGeneric);
        return tc;
    }

    @Test
    void happyPath_usesTheTenantsOwnConfiguredMessageRatherThanARawTechnicalError() throws Exception {
        // Constitution VI.4: the copy comes from the retailer's own config, not a hardcoded
        // platform string.
        handler = new ChatErrorHandler(tenantConfigRepository);
        when(tenantConfigRepository.findById("vinted"))
                .thenReturn(Optional.of(buildTenantConfig("Une erreur est survenue, veuillez réessayer.")));
        var request = new MockHttpServletRequest();
        request.addHeader("X-Tenant-ID", "vinted");

        var response = handler.handleUnexpectedError(new RuntimeException("connection refused to postgres:5432"), request);

        assertThat(response.getStatusCode().is2xxSuccessful()).isTrue();
        assertThat(response.getBody().reply()).isEqualTo("Une erreur est survenue, veuillez réessayer.");
        assertThat(response.getBody().reply()).doesNotContain("postgres", "connection refused", "Exception");
    }

    @Test
    void edgeCase_fallsBackToTheDefaultMessageWhenTheTenantHasNoneConfigured() throws Exception {
        handler = new ChatErrorHandler(tenantConfigRepository);
        when(tenantConfigRepository.findById("vinted")).thenReturn(Optional.of(buildTenantConfig(null)));
        var request = new MockHttpServletRequest();
        request.addHeader("X-Tenant-ID", "vinted");

        var response = handler.handleUnexpectedError(new NullPointerException(), request);

        assertThat(response.getBody().reply()).doesNotContain("null");
        assertThat(response.getBody().reply()).contains("réessayer");
        assertThat(response.getBody().escalated()).isFalse();
    }

    @Test
    void edgeCase_fallsBackToTheDefaultMessageWhenTheTenantIsUnknown() {
        // Constitution VI.1: some normalized message is always mandatory, even if the
        // tenant lookup itself fails or the header is missing/wrong.
        handler = new ChatErrorHandler(tenantConfigRepository);
        when(tenantConfigRepository.findById("")).thenReturn(Optional.empty());
        var request = new MockHttpServletRequest();

        var response = handler.handleUnexpectedError(new RuntimeException("boom"), request);

        assertThat(response.getBody().reply()).contains("réessayer");
    }
}
