-- The POC has settled on French as the sole operating language (Léa's persona, constitution
-- II.1) rather than the bilingual detection originally floated — V3's seed values were still
-- the English placeholders they were bundled with. Cannot edit V3 directly: Flyway checksums
-- already-applied migrations, so a correction is its own migration.
UPDATE tenant_config
SET error_message_generic = 'Désolée, une erreur est survenue de notre côté. Merci de réessayer dans un instant.',
    error_message_channel_unavailable = 'Désolée, ce canal de contact n''est pas disponible pour le moment. Merci de nous contacter via notre widget de chat en ligne.'
WHERE tenant_id = 'vinted';
