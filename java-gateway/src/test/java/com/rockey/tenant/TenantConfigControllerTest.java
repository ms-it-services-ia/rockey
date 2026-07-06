package com.rockey.tenant;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.when;

import java.util.Optional;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

@ExtendWith(MockitoExtension.class)
class TenantConfigControllerTest {

    @Mock private TenantConfigRepository repository;

    private TenantConfigController controller;

    private TenantConfig buildTenantConfig() throws Exception {
        var constructor = TenantConfig.class.getDeclaredConstructor();
        constructor.setAccessible(true);
        TenantConfig tc = constructor.newInstance();
        setField(tc, "tenantId", "vinted");
        setField(tc, "agentFirstName", "Léa");
        setField(tc, "agentTone", "warm");
        setField(tc, "agentFormality", "formal");
        setField(tc, "agentLanguage", "French");
        setField(tc, "channelEmailActive", true);
        setField(tc, "channelSlackActive", true);
        setField(tc, "channelSlackChannel", "#support-vinted");
        setField(tc, "driveFolderId", "1JE-rNzM1oi9UznCbeCDU9G_OWRGz4xXu");
        return tc;
    }

    private void setField(Object target, String name, Object value) throws Exception {
        var field = TenantConfig.class.getDeclaredField(name);
        field.setAccessible(true);
        field.set(target, value);
    }

    @Test
    void happyPath_knownTenantReturnsItsConfig() throws Exception {
        controller = new TenantConfigController(repository);
        when(repository.findById("vinted")).thenReturn(Optional.of(buildTenantConfig()));

        var response = controller.getTenantConfig("vinted");

        assertThat(response.getStatusCode().is2xxSuccessful()).isTrue();
        assertThat(response.getBody().agentFirstName()).isEqualTo("Léa");
        assertThat(response.getBody().channelSlackChannel()).isEqualTo("#support-vinted");
    }

    @Test
    void edgeCase_unknownTenantReturns404() {
        controller = new TenantConfigController(repository);
        when(repository.findById("unknown-tenant")).thenReturn(Optional.empty());

        var response = controller.getTenantConfig("unknown-tenant");

        assertThat(response.getStatusCode().value()).isEqualTo(404);
    }
}
