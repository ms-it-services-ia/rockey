package com.rockey.gateway.adapter;

import com.rockey.gateway.dto.AgentResponse;
import com.rockey.gateway.dto.InternalMessage;
import jakarta.mail.Address;
import jakarta.mail.BodyPart;
import jakarta.mail.Message;
import jakarta.mail.MessagingException;
import jakarta.mail.Multipart;
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

    /** Real mail clients (Gmail's web UI included) almost always send multipart/alternative
     * (text/plain + text/html), never a bare String body — walks that tree for the
     * text/plain part, falling back to a naive HTML-tag strip of text/html if that's all
     * there is. Without this, {@code email.getContent()} returns a {@link Multipart} object
     * whose {@code toString()} (e.g. "jakarta.mail.internet.MimeMultipart@1a2b3c") was
     * silently being fed to the agent as the "message" — never containing an order number
     * or email, so identification could never succeed on a real reply. */
    public String extractPlainText(Message email) throws MessagingException, IOException {
        Object content = email.getContent();
        if (content instanceof String s) {
            return s.strip();
        }
        if (content instanceof Multipart multipart) {
            return extractFromMultipart(multipart).strip();
        }
        return String.valueOf(content).strip();
    }

    private String extractFromMultipart(Multipart multipart) throws MessagingException, IOException {
        String htmlFallback = null;
        for (int i = 0; i < multipart.getCount(); i++) {
            BodyPart part = multipart.getBodyPart(i);
            if (part.isMimeType("text/plain") && part.getDisposition() == null) {
                return String.valueOf(part.getContent());
            }
            if (part.getContent() instanceof Multipart nested) {
                String nestedText = extractFromMultipart(nested);
                if (!nestedText.isBlank()) {
                    return nestedText;
                }
            } else if (htmlFallback == null && part.isMimeType("text/html") && part.getDisposition() == null) {
                htmlFallback = stripHtml(String.valueOf(part.getContent()));
            }
        }
        return htmlFallback != null ? htmlFallback : "";
    }

    private String stripHtml(String html) {
        return html.replaceAll("(?i)<br\\s*/?>", "\n")
                .replaceAll("<[^>]+>", " ")
                .replace("&nbsp;", " ")
                .replace("&amp;", "&")
                .strip();
    }

    public String formatOutboundSubject(String caseId) {
        return "Re : Votre demande de service client — Dossier #" + (caseId != null ? caseId : "en attente");
    }

    /** HTML body per constitution I.4b: "formatted HTML ... formal tone, complete summary",
     * vs. the Web Widget's terse raw-JSON reply (spec User Story 7 AC3 — same decision,
     * different formatting per channel). The PDF attachment itself is handled by
     * EmailController (it needs the JavaMailSender's MimeMessageHelper, not a pure string
     * builder).
     *
     * French wrapper text (constitution I.7 / the POC's French-only decision): the agent's
     * own reply text is always already French, but this wrapper around it — greeting,
     * case-reference label, attachment note, signature — was still hardcoded in English,
     * the one piece of the customer-facing email surface that hadn't been translated. */
    public String formatOutboundHtml(AgentResponse response) {
        StringBuilder html = new StringBuilder("<html><body>");
        html.append("<p>Bonjour,</p>");
        html.append("<p>").append(escapeHtml(response.reply())).append("</p>");
        if (response.caseId() != null) {
            html.append("<p>Référence du dossier : ").append(escapeHtml(response.caseId())).append("</p>");
        }
        if (response.attachments() != null) {
            for (AgentResponse.Attachment attachment : response.attachments()) {
                if ("return_label".equals(attachment.type())) {
                    html.append("<p>Votre étiquette de retour est jointe à cet email.</p>");
                }
            }
        }
        html.append("<p>Cordialement,<br/>L'équipe du service client</p>");
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
