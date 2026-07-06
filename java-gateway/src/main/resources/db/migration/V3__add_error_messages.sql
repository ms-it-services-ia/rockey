-- Normalized customer-facing error messages (constitution VI.4): sourced per-tenant from
-- the retailer's own config, the same POC stand-in as tenant_config's other Drive-sourced
-- fields (agent_first_name, agent_tone, etc. — see V2's seed comment) — a live sync job
-- would populate this from Drive in production; PolicyLoader.java's javadoc documents the
-- same simplification for policy thresholds (T090).
ALTER TABLE tenant_config
    ADD COLUMN error_message_generic TEXT,
    ADD COLUMN error_message_channel_unavailable TEXT;

UPDATE tenant_config
SET error_message_generic = 'Sorry, something went wrong on our end. Please try again in a moment.',
    error_message_channel_unavailable = 'Sorry, this contact channel isn''t available right now. Please reach us instead through our web chat widget.'
WHERE tenant_id = 'vinted';
