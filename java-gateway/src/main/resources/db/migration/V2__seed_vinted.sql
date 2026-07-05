-- Seed tenant_config — Vinted powered by Rockey (constitution Article II)
INSERT INTO tenant_config (
    tenant_id, product,
    agent_first_name, agent_tone, agent_formality, agent_language,
    channel_web_active, channel_email_active, channel_email_imap, channel_email_address,
    channel_slack_active, channel_slack_channel,
    drive_folder_id
) VALUES (
    'vinted', 'rockey',
    'Léa', 'warm, empathetic and passionate about vintage fashion', 'formal', 'fr',
    true, true, 'imap.gmail.com:993', 'sav@vinted.com',
    true, '#support-vinted',
    'VINTED_DRIVE_FOLDER_ID_HERE'
);

-- Seed articles (14 reference items, constitution II.2)
INSERT INTO articles (id, tenant_id, name, category, sub_category, era, material, price, returnable, non_return_reason, article_type, description) VALUES
('VTG-001', 'vinted', '70s Printed Midi Dress',       'dresses',   'standard',      '1970s','100% viscose',             68.00, true, NULL,           'standard',    '70s floral printed midi dress.'),
('VTG-002', 'vinted', '90s Velvet Evening Dress',      'dresses',   'standard',      '1990s','90% velvet, 10% elastane',145.00, true, NULL,           'standard',    'Burgundy velvet sheath dress, midi length.'),
('VTG-003', 'vinted', '60s Sundress (Unique Piece)',   'dresses',   'piece_unique',  '1960s','100% hand-embroidered cotton',210.00,false,'piece_unique','piece_unique', 'Hand-embroidered designer dress, unique item.'),
('VTG-010', 'vinted', '80s Oversize Blazer',           'jackets',   'standard',      '1980s','65% wool, 35% polyester',  89.00, true, NULL,           'standard',    'Oversize blazer with marked shoulders, camel color.'),
('VTG-011', 'vinted', '70s Wool Cashmere Coat',        'coats',     'premium',       '1970s','80% wool, 20% cashmere',  265.00, true, NULL,           'premium',     'Long double-breasted wool and cashmere coat.'),
('VTG-012', 'vinted', '90s Leather Perfecto Jacket',   'jackets',   'standard',      '1990s','100% genuine leather',    179.00, true, NULL,           'standard',    'Black leather perfecto, rock style.'),
('VTG-020', 'vinted', '70s Embroidered Shirt',         'tops',      'standard',      '1970s','100% cotton',              42.00, true, NULL,           'standard',    'Cotton shirt with floral embroidery on placket.'),
('VTG-021', 'vinted', '80s Mohair Sweater',            'tops',      'knitwear',      '1980s','70% mohair, 30% wool',     58.00, true, NULL,           'standard',    'Turtleneck sweater in powder pink mohair.'),
('VTG-030', 'vinted', '90s High-waist Jeans',          'pants',     'standard',      '1990s','100% cotton denim',        55.00, true, NULL,           'standard',    'Straight-cut high-waist jeans, natural wash.'),
('VTG-031', 'vinted', '60s Pleated Skirt (Unique)',    'skirts',    'piece_unique',  '1960s','100% silk',               185.00, false,'piece_unique', 'piece_unique', 'Ivory silk pleated skirt, unique item.'),
('VTG-040', 'vinted', '70s Structured Leather Bag',    'bags',      'standard',      '1970s','Genuine leather',          95.00, true, NULL,           'standard',    'Rigid camel leather handbag with golden clasp.'),
('VTG-041', 'vinted', '50s Glass Pearl Necklace',      'jewelry',   'jewelry',       '1950s','Blown glass pearls',       38.00, false,'bijou',        'bijou',       'Blown glass pearl necklace, gold-plated clasp.'),
('VTG-042', 'vinted', '80s Golden Leather Belt',       'belts',     'belts',         '1980s','Patent leather',           28.00, false,'ceinture',     'ceinture',    'Wide black patent leather belt with golden buckle.'),
('VTG-050', 'vinted', '80s Dress — Clearance',         'dresses',   'destockage',    '1980s', NULL,                      19.00, false,'destockage',   'destockage',  'Puff sleeve dress with slight stains. Sold as-is.');

-- Seed test orders (7 reference orders, spec.md test scenarios)
INSERT INTO orders (id, tenant_id, client_email, client_name, article_id, amount, status, order_date, delivery_date) VALUES
('CMD-2026-00001', 'vinted', 'marie.dupont@email.com',   'Marie Dupont',   'VTG-001',  68.00, 'delivered', '2026-06-10', '2026-06-13'),
('CMD-2026-00002', 'vinted', 'thomas.martin@email.com',  'Thomas Martin',  'VTG-010',  89.00, 'delivered', '2026-06-15', '2026-06-18'),
('CMD-2026-00003', 'vinted', 'sophie.bernard@email.com', 'Sophie Bernard', 'VTG-011', 265.00, 'delivered', '2026-06-20', '2026-06-24'),
('CMD-2026-00004', 'vinted', 'lucas.petit@email.com',    'Lucas Petit',    'VTG-003', 210.00, 'delivered', '2026-06-25', '2026-06-28'),
('CMD-2026-00005', 'vinted', 'emma.richard@email.com',   'Emma Richard',   'VTG-012', 179.00, 'delivered', '2026-06-30', '2026-07-03'),
('CMD-2026-00006', 'vinted', 'julie.moreau@email.com',   'Julie Moreau',   'VTG-002', 145.00, 'delivered', '2026-05-01', '2026-05-05'),
('CMD-2026-00007', 'vinted', 'pierre.simon@email.com',   'Pierre Simon',   'VTG-041',  38.00, 'delivered', '2026-06-28', '2026-07-01');
