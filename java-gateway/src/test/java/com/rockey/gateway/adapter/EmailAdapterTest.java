package com.rockey.gateway.adapter;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.when;

import com.rockey.gateway.dto.AgentResponse;
import com.rockey.gateway.dto.InternalMessage;
import jakarta.mail.Message;
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
    void toInternal_usesMessageIdAsSessionAndClientId() throws Exception {
        when(email.getHeader("Message-ID")).thenReturn(new String[] {"<abc123@mail.example.com>"});
        when(email.getContent()).thenReturn("I'd like to return my order.");

        InternalMessage result = emailAdapter.toInternal("vinted", email);

        assertThat(result.sessionId()).isEqualTo("<abc123@mail.example.com>");
        assertThat(result.clientId()).isEqualTo("<abc123@mail.example.com>");
        assertThat(result.tenantId()).isEqualTo("vinted");
        assertThat(result.channel()).isEqualTo("email");
        assertThat(result.message()).isEqualTo("I'd like to return my order.");
    }

    @Test
    void edgeCase_missingMessageIdHeaderFallsBackToMessageNumber() throws Exception {
        when(email.getHeader("Message-ID")).thenReturn(null);
        when(email.getMessageNumber()).thenReturn(7);
        when(email.getContent()).thenReturn("Hello");

        InternalMessage result = emailAdapter.toInternal("vinted", email);

        assertThat(result.sessionId()).isEqualTo("email-7");
    }

    @Test
    void formatOutboundHtml_wrapsReplyAndMentionsAttachedLabel() {
        AgentResponse response =
                new AgentResponse(
                        "s1",
                        "CONFIRMATION",
                        "Your return has been approved.",
                        List.of(new AgentResponse.Attachment("return_label", "https://labels.rockey.local/x.pdf")),
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
