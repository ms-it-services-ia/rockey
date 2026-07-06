package com.rockey.gateway.controller;

import com.rockey.gateway.adapter.EmailAdapter;
import com.rockey.gateway.client.AgentClient;
import com.rockey.gateway.dto.AgentResponse;
import com.rockey.gateway.dto.InternalMessage;
import com.rockey.tenant.TenantConfigRepository;
import jakarta.mail.Flags;
import jakarta.mail.Folder;
import jakarta.mail.Message;
import jakarta.mail.Session;
import jakarta.mail.Store;
import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.net.URI;
import java.net.URLConnection;
import java.time.Duration;
import java.util.Properties;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.slf4j.MDC;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.mail.javamail.JavaMailSender;
import org.springframework.mail.javamail.MimeMessageHelper;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

/**
 * Email channel (constitution I.4b): IMAP polling every 2 minutes, SMTP HTML reply. This is
 * the one channel adapter that can't be exercised in automated tests without live
 * credentials — {@link EmailAdapter}'s parsing/formatting logic is what's unit-tested; this
 * class is the thin, mostly-untestable-without-a-mailbox glue around it.
 */
@Component
public class EmailController {

    private static final Logger log = LoggerFactory.getLogger(EmailController.class);
    private static final String TENANT_ID = "vinted"; // sole POC tenant (constitution II.1)
    private static final Duration LABEL_FETCH_TIMEOUT = Duration.ofSeconds(5);

    private final TenantConfigRepository tenantConfigRepository;
    private final EmailAdapter emailAdapter;
    private final AgentClient agentClient;
    private final JavaMailSender mailSender;

    @Value("${VINTED_EMAIL_PASSWORD:}")
    private String emailPassword;

    public EmailController(
            TenantConfigRepository tenantConfigRepository,
            EmailAdapter emailAdapter,
            AgentClient agentClient,
            JavaMailSender mailSender) {
        this.tenantConfigRepository = tenantConfigRepository;
        this.emailAdapter = emailAdapter;
        this.agentClient = agentClient;
        this.mailSender = mailSender;
    }

    @Scheduled(fixedDelay = 120_000)
    public void pollEmails() {
        var tenantConfig = tenantConfigRepository.findById(TENANT_ID).orElse(null);
        if (tenantConfig == null || !tenantConfig.isChannelEmailActive() || emailPassword.isBlank()) {
            return; // email channel not configured for this tenant — nothing to poll
        }

        String[] hostAndPort = tenantConfig.getChannelEmailImap().split(":");
        String host = hostAndPort[0];
        String port = hostAndPort.length > 1 ? hostAndPort[1] : "993";

        Properties props = new Properties();
        props.put("mail.store.protocol", "imaps");
        props.put("mail.imaps.host", host);
        props.put("mail.imaps.port", port);
        Session session = Session.getInstance(props);

        // Constitution VI.1: every error logged for this poll cycle (and any single email
        // within it) must carry tenant_id/session_id — MDC is thread-local, so this covers
        // the whole call chain for free.
        MDC.put("tenant_id", TENANT_ID);
        try (Store store = session.getStore("imaps")) {
            store.connect(host, tenantConfig.getChannelEmailAddress(), emailPassword);
            Folder inbox = store.getFolder("INBOX");
            inbox.open(Folder.READ_WRITE);

            Message[] unread = inbox.search(new jakarta.mail.search.FlagTerm(new Flags(Flags.Flag.SEEN), false));
            for (Message email : unread) {
                try {
                    handleOneEmail(email);
                    email.setFlag(Flags.Flag.SEEN, true);
                } catch (Exception e) {
                    // Never let one malformed email take down the whole poll cycle
                    // (constitution VI.1 — every external call wrapped, no silent request loss).
                    log.error("Failed to process inbound email", e);
                } finally {
                    MDC.remove("session_id");
                }
            }
            inbox.close(false);
        } catch (Exception e) {
            log.error("IMAP poll failed for tenant {}", TENANT_ID, e);
        } finally {
            MDC.remove("tenant_id");
        }
    }

    private void handleOneEmail(Message email) throws Exception {
        InternalMessage internal = emailAdapter.toInternal(TENANT_ID, email);
        // The email's own Message-ID doubles as its session_id (see EmailAdapter) — set as
        // soon as it's known so a failure reaching agentClient.process still logs it.
        MDC.put("session_id", internal.sessionId());
        AgentResponse response = agentClient.process(internal);
        sendReply(email, response);
    }

    private void sendReply(Message originalEmail, AgentResponse response) throws Exception {
        var mimeMessage = mailSender.createMimeMessage();
        var helper = new MimeMessageHelper(mimeMessage, true, "UTF-8");
        helper.setTo((jakarta.mail.internet.InternetAddress) originalEmail.getFrom()[0]);
        helper.setSubject(emailAdapter.formatOutboundSubject(response.caseId()));
        helper.setText(emailAdapter.formatOutboundHtml(response), true);

        if (response.attachments() != null) {
            for (AgentResponse.Attachment attachment : response.attachments()) {
                if ("return_label".equals(attachment.type())) {
                    attachLabelIfReachable(helper, attachment.url());
                }
            }
        }

        mailSender.send(mimeMessage);
    }

    /** Best-effort: the return label is a real PDF in production, but this POC's
     * ReturnLabelGenerator produces a URL that isn't actually served — skip the attachment
     * rather than fail the whole reply if it can't be fetched (constitution VI.1). */
    private void attachLabelIfReachable(MimeMessageHelper helper, String labelUrl) {
        try {
            URLConnection connection = URI.create(labelUrl).toURL().openConnection();
            connection.setConnectTimeout((int) LABEL_FETCH_TIMEOUT.toMillis());
            connection.setReadTimeout((int) LABEL_FETCH_TIMEOUT.toMillis());
            try (InputStream in = connection.getInputStream()) {
                ByteArrayOutputStream buffer = new ByteArrayOutputStream();
                in.transferTo(buffer);
                helper.addAttachment("return-label.pdf", new jakarta.mail.util.ByteArrayDataSource(buffer.toByteArray(), "application/pdf"));
            }
        } catch (Exception e) {
            log.warn("Could not fetch return label for email attachment: {}", labelUrl, e);
        }
    }
}
