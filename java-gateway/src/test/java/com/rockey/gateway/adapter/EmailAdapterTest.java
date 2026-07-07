package com.rockey.gateway.adapter;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.when;

import com.rockey.gateway.dto.AgentResponse;
import com.rockey.gateway.dto.InternalMessage;
import jakarta.mail.BodyPart;
import jakarta.mail.Message;
import jakarta.mail.MessagingException;
import jakarta.mail.Multipart;
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
    void edgeCase_multipartAlternativeUsesTheTextPlainPartNotTheMultipartObjectsToString() throws Exception {
        // Real clients (Gmail's web UI included) send multipart/alternative
        // (text/plain + text/html), never a bare String — without walking the tree, this
        // used to silently feed the agent a useless "jakarta.mail.internet.MimeMultipart@..."
        // string, so identification could never find an order number or email in a real reply.
        // HTML part listed first, plain part second — the plain part must still win.
        BodyPart htmlPart = org.mockito.Mockito.mock(BodyPart.class);
        when(htmlPart.isMimeType("text/plain")).thenReturn(false);
        when(htmlPart.getContent()).thenReturn("<p>Order CMD-2026-00001, email marie.dupont@email.com</p>");

        BodyPart plainPart = org.mockito.Mockito.mock(BodyPart.class);
        when(plainPart.isMimeType("text/plain")).thenReturn(true);
        when(plainPart.getDisposition()).thenReturn(null);
        when(plainPart.getContent()).thenReturn("Order CMD-2026-00001, email marie.dupont@email.com");

        Multipart multipart = org.mockito.Mockito.mock(Multipart.class);
        when(multipart.getCount()).thenReturn(2);
        when(multipart.getBodyPart(0)).thenReturn(htmlPart);
        when(multipart.getBodyPart(1)).thenReturn(plainPart);

        when(email.getHeader("Message-ID")).thenReturn(new String[] {"<abc123@mail.example.com>"});
        when(email.getFrom()).thenReturn(new jakarta.mail.Address[] {new InternetAddress("marie.dupont@email.com")});
        when(email.getContent()).thenReturn(multipart);

        InternalMessage result = emailAdapter.toInternal("vinted", email);

        assertThat(result.message()).isEqualTo("Order CMD-2026-00001, email marie.dupont@email.com");
    }

    @Test
    void edgeCase_multipartWithOnlyHtmlFallsBackToAStrippedVersionOfIt() throws Exception {
        BodyPart htmlPart = org.mockito.Mockito.mock(BodyPart.class);
        when(htmlPart.isMimeType("text/plain")).thenReturn(false);
        when(htmlPart.isMimeType("text/html")).thenReturn(true);
        when(htmlPart.getDisposition()).thenReturn(null);
        when(htmlPart.getContent()).thenReturn("<div>Order <b>CMD-2026-00001</b>, email marie.dupont@email.com</div>");

        Multipart multipart = org.mockito.Mockito.mock(Multipart.class);
        when(multipart.getCount()).thenReturn(1);
        when(multipart.getBodyPart(0)).thenReturn(htmlPart);

        when(email.getHeader("Message-ID")).thenReturn(new String[] {"<abc123@mail.example.com>"});
        when(email.getFrom()).thenReturn(new jakarta.mail.Address[] {new InternetAddress("marie.dupont@email.com")});
        when(email.getContent()).thenReturn(multipart);

        InternalMessage result = emailAdapter.toInternal("vinted", email);

        assertThat(result.message()).contains("CMD-2026-00001", "marie.dupont@email.com");
        assertThat(result.message()).doesNotContain("<div>", "<b>");
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
        assertThat(html).contains("jointe à cet email");
    }

    @Test
    void formatOutboundSubject_includesCaseId() {
        assertThat(emailAdapter.formatOutboundSubject("TCK-abcd1234")).contains("TCK-abcd1234");
    }
}
