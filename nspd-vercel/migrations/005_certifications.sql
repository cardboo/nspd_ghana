-- =============================================
-- NSPD Ghana — feature migration 005: compliance tracking
--
-- 1. Certifications with real issue/expiry dates (the registry only
--    stored Yes/No flags before), enabling the expiry watchlist and
--    automated expiry alerts.
-- 2. Ghana Card number on applications — a true national identity key.
--    The UNIQUE index structurally prevents duplicate submissions going
--    forward (MySQL allows multiple NULLs, so legacy rows are unaffected).
--
-- Run AFTER 004_account_recovery.sql.
-- =============================================

CREATE TABLE IF NOT EXISTS `certifications` (
  `id` int NOT NULL AUTO_INCREMENT,
  `application_id` int NOT NULL,
  `cert_type` varchar(50) COLLATE utf8mb4_general_ci NOT NULL DEFAULT 'Other',
  `title` varchar(150) COLLATE utf8mb4_general_ci NOT NULL,
  `issued_on` date DEFAULT NULL,
  `expires_on` date DEFAULT NULL,
  `issuer` varchar(150) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `added_by` int DEFAULT NULL,
  `last_alerted_at` timestamp NULL DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_cert_app` (`application_id`),
  KEY `idx_cert_expiry` (`expires_on`),
  CONSTRAINT `fk_cert_app` FOREIGN KEY (`application_id`) REFERENCES `applications` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_cert_user` FOREIGN KEY (`added_by`) REFERENCES `users` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

ALTER TABLE `applications`
  ADD COLUMN `ghana_card_number` varchar(30) COLLATE utf8mb4_general_ci DEFAULT NULL AFTER `telephone`,
  ADD UNIQUE INDEX `idx_ghana_card` (`ghana_card_number`);
