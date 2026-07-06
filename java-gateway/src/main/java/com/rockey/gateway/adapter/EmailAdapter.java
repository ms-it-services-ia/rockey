package com.rockey.gateway.adapter;

import com.rockey.gateway.dto.AgentResponse;
import com.rockey.gateway.dto.InternalMessage;
import jakarta.mail.Address;
import jakarta.mail.Message;
import jakarta.mail.MessagingException;
import jakarta.mail.internet.InternetAddress;
import java.io.IOException;
import org.springframework.stereotype.Component;

/**
 * Converts between the Email channel's native format (IMAP {@link Message}, SMTP HTML body)
 * and the unified internal format (contracts/internal-message.md). Parsing/formatting are
 * pure functions, independently testable without a live IMAP/SMTP connection —
 * {@link com.rockey.gateway.controller.EmailController} owns the actual polling/sending.
 */
@Component
public class EmailAdapter {

    /** {@code sessionId} is the email's own Message-ID (unique per message, useful for
     * correlation/logging). {@code clientId} — what {@code session_store.build_session_key}
     * actually uses for resumption ("same customer + same channel = same session", per its
     * own docstring, spec FR-012) — MUST be the sender's address instead: a reply is a brand
     * new message with its own Message-ID, so using that for resumption would put every
     * single reply in a fresh session, permanently stuck replaying GREETING. */
    public InternalMessage toInternal(String tenantId, Message email) throws MessagingException, IOException {
        String messageId = firstHeaderOrFallback(email, "Message-ID", "email-" + email.getMessageNumber());
        String senderEmail = extractSenderAddress(email);
        String bodyText = extractPlainText(email);
        return new InternalMessage(messageId, tenantId, "email", bodyText, senderEmail);
    }

    private String extractSenderAddress(Message email) throws MessagingException {
        Address[] from = email.getFrom();
        if (from == null || from.length == 0) {
            throw new MessagingException("email has no From address");
        }
        return from[0] instanceof InternetAddress internetAddress ? internetAddress.getAddress() : from[0].toString();
    }

    private String firstHeaderOrFallback(Message email, String headerName, String fallback) throws MessagingException {
        String[] values = email.getHeader(headerName);
        return (values != null && values.length > 0) ? values[0] : fallback;
    }

    /** POC-level simplification: reads the message content as text, without walking a
     * multipart MIME tree for the text/plain part specifically — sufficient for the
     * plain-text confirmation emails this POC's test fixtures use. */
    public String extractPlainText(Message email) throws MessagingException, IOException {
        Object content = email.getContent();
        String text = content instanceof String s ? s : String.valueOf(content);
        return text.strip();
    }

    public String formatOutboundSubject(String caseId) {
        return "Re: Your customer service request — Case #" + (caseId != null ? caseId : "pending");
    }

    /** HTML body per constitution I.4b: "formatted HTML ... formal tone, complete summary",
     * vs. the Web Widget's terse raw-JSON reply (spec User Story 7 AC3 — same decision,
     * different formatting per channel). The PDF attachment itself is handled by
     * EmailController (it needs the JavaMailSender's MimeMessageHelper, not a pure string
     * builder). */
    public String formatOutboundHtml(AgentResponse response) {
        StringBuilder html = new StringBuilder("<html><body>");
        html.append("<p>Hello,</p>");
        html.append("<p>").append(escapeHtml(response.reply())).append("</p>");
        if (response.caseId() != null) {
            html.append("<p>Case reference: ").append(escapeHtml(response.caseId())).append("</p>");
        }
        if (response.attachments() != null) {
            for (AgentResponse.Attachment attachment : response.attachments()) {
                if ("return_label".equals(attachment.type())) {
                    html.append("<p>Your return label is attached to this email.</p>");
                }
            }
        }
        html.append("<p>Best regards,<br/>Your customer service team</p>");
        html.append("</body></html>");
        return html.toString();
    }

    private String escapeHtml(String text) {
        if (text == null) {
            return "";
        }
        return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;");
    }
}
