package com.rockey.gateway.adapter;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.when;

import com.rockey.gateway.dto.AgentResponse;
import com.rockey.gateway.dto.InternalMessage;
import jakarta.mail.Message;
import jakarta.mail.MessagingException;
import jakarta.mail.internet.InternetAddress;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

@ExtendWith(MockitoExtension.class)
class EmailAdapterTest {

    private final EmailAdapter emailAdapter = new EmailAdapter();

    @Mock private Message email;

    @Test
    void toInternal_usesMessageIdAsSessionIdAndSenderAddressAsClientId() throws Exception {
        // session_store resumes by (tenant, channel, client_id) — a reply has its own new
        // Message-ID, so client_id must be the stable sender address, not the Message-ID,
        // or every reply would start a brand new session stuck replaying GREETING.
        when(email.getHeader("Message-ID")).thenReturn(new String[] {"<abc123@mail.example.com>"});
        when(email.getFrom()).thenReturn(new jakarta.mail.Address[] {new InternetAddress("marie.dupont@email.com")});
        when(email.getContent()).thenReturn("I'd like to return my order.");

        InternalMessage result = emailAdapter.toInternal("vinted", email);

        assertThat(result.sessionId()).isEqualTo("<abc123@mail.example.com>");
        assertThat(result.clientId()).isEqualTo("marie.dupont@email.com");
        assertThat(result.tenantId()).isEqualTo("vinted");
        assertThat(result.channel()).isEqualTo("email");
        assertThat(result.message()).isEqualTo("I'd like to return my order.");
    }

    @Test
    void edgeCase_missingMessageIdHeaderFallsBackToMessageNumber() throws Exception {
        when(email.getHeader("Message-ID")).thenReturn(null);
        when(email.getMessageNumber()).thenReturn(7);
        when(email.getFrom()).thenReturn(new jakarta.mail.Address[] {new InternetAddress("marie.dupont@email.com")});
        when(email.getContent()).thenReturn("Hello");

        InternalMessage result = emailAdapter.toInternal("vinted", email);

        assertThat(result.sessionId()).isEqualTo("email-7");
    }

    @Test
    void edgeCase_missingFromAddressRaisesRatherThanSilentlyMisidentifyingTheCustomer() throws Exception {
        when(email.getHeader("Message-ID")).thenReturn(new String[] {"<abc123@mail.example.com>"});
        when(email.getFrom()).thenReturn(null);

        org.junit.jupiter.api.Assertions.assertThrows(
                MessagingException.class, () -> emailAdapter.toInternal("vinted", email));
    }

    @Test
    void formatOutboundHtml_wrapsReplyAndMentionsAttachedLabel() {
        AgentResponse response =
                new AgentResponse(
                        "s1",
                        "CONFIRMATION",
                        "Your return has been approved.",
                        List.of(new AgentResponse.Attachment("return_label", "https://returns.vinted.local/x.pdf")),
                        false,
                        "RET-abcd1234");

        String html = emailAdapter.formatOutboundHtml(response);

        assertThat(html).contains("Your return has been approved.");
        assertThat(html).contains("RET-abcd1234");
        assertThat(html).contains("attached to this email");
    }

    @Test
    void formatOutboundSubject_includesCaseId() {
        assertThat(emailAdapter.formatOutboundSubject("TCK-abcd1234")).contains("TCK-abcd1234");
    }
}
