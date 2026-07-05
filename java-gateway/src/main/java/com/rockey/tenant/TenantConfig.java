package com.rockey.tenant;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;

@Entity
@Table(name = "tenant_config")
public class TenantConfig {

    @Id
    @Column(name = "tenant_id")
    private String tenantId;

    @Column(name = "agent_first_name")
    private String agentFirstName;

    @Column(name = "agent_tone")
    private String agentTone;

    @Column(name = "agent_formality")
    private String agentFormality;

    @Column(name = "agent_language")
    private String agentLanguage;

    @Column(name = "channel_slack_active")
    private boolean channelSlackActive;

    @Column(name = "channel_slack_channel")
    private String channelSlackChannel;

    @Column(name = "drive_folder_id")
    private String driveFolderId;

    protected TenantConfig() {}

    public String getTenantId() {
        return tenantId;
    }

    public String getAgentFirstName() {
        return agentFirstName;
    }

    public String getAgentTone() {
        return agentTone;
    }

    public String getAgentFormality() {
        return agentFormality;
    }

    public String getAgentLanguage() {
        return agentLanguage;
    }

    public boolean isChannelSlackActive() {
        return channelSlackActive;
    }

    public String getChannelSlackChannel() {
        return channelSlackChannel;
    }

    public String getDriveFolderId() {
        return driveFolderId;
    }
}
