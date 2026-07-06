package com.rockey.gateway.controller;

import static org.mockito.Mockito.verifyNoInteractions;
import static org.mockito.Mockito.when;

import com.rockey.gateway.adapter.EmailAdapter;
import com.rockey.gateway.client.AgentClient;
import com.rockey.tenant.TenantConfig;
import com.rockey.tenant.TenantConfigRepository;
import java.util.Optional;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.mail.javamail.JavaMailSender;

/** EmailController's IMAP polling itself can't be exercised without a real mailbox (see its
 * class Javadoc) — this covers the one part that's pure business logic: the gate deciding
 * whether the email channel is even configured for this tenant before attempting to connect. */
@ExtendWith(MockitoExtension.class)
class EmailControllerTest {

    @Mock private TenantConfigRepository tenantConfigRepository;
    @Mock private EmailAdapter emailAdapter;
    @Mock private AgentClient agentClient;
    @Mock private JavaMailSender mailSender;

    private EmailController controller;

    private void setEmailPassword(String value) throws Exception {
        var field = EmailController.class.getDeclaredField("emailPassword");
        field.setAccessible(true);
        field.set(controller, value);
    }

    private TenantConfig buildTenantConfig(boolean channelEmailActive) throws Exception {
        var constructor = TenantConfig.class.getDeclaredConstructor();
        constructor.setAccessible(true);
        TenantConfig tc = constructor.newInstance();
        var field = TenantConfig.class.getDeclaredField("channelEmailActive");
        field.setAccessible(true);
        field.set(tc, channelEmailActive);
        return tc;
    }

    @Test
    void edgeCase_noTenantConfigSkipsPollingWithoutError() throws Exception {
        controller = new EmailController(tenantConfigRepository, emailAdapter, agentClient, mailSender);
        setEmailPassword("some-password");
        when(tenantConfigRepository.findById("vinted")).thenReturn(Optional.empty());

        controller.pollEmails();

        verifyNoInteractions(emailAdapter, agentClient, mailSender);
    }

    @Test
    void edgeCase_channelInactiveSkipsPollingEvenWithAPasswordConfigured() throws Exception {
        controller = new EmailController(tenantConfigRepository, emailAdapter, agentClient, mailSender);
        setEmailPassword("some-password");
        when(tenantConfigRepository.findById("vinted")).thenReturn(Optional.of(buildTenantConfig(false)));

        controller.pollEmails();

        verifyNoInteractions(emailAdapter, agentClient, mailSender);
    }

    @Test
    void edgeCase_blankPasswordSkipsPollingEvenWhenChannelIsActive() throws Exception {
        controller = new EmailController(tenantConfigRepository, emailAdapter, agentClient, mailSender);
        setEmailPassword("");
        when(tenantConfigRepository.findById("vinted")).thenReturn(Optional.of(buildTenantConfig(true)));

        controller.pollEmails();

        verifyNoInteractions(emailAdapter, agentClient, mailSender);
    }
}
