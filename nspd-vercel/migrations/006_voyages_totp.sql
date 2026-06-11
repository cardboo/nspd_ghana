-- =============================================
-- NSPD Ghana — feature migration 006: placement tracking + 2FA
--
-- 1. Voyage & employment history — the "Placement" in NSPD: which
--    vessel/employer each seafarer served with and when. An open
--    voyage (signed_off IS NULL) means currently on board.
-- 2. TOTP two-factor authentication columns for staff accounts.
--
-- Run AFTER 005_certifications.sql.
-- =============================================

CREATE TABLE IF NOT EXISTS `voyages` (
  `id` int NOT NULL AUTO_INCREMENT,
  `application_id` int NOT NULL,
  `vessel_name` varchar(150) COLLATE utf8mb4_general_ci NOT NULL,
  `vessel_type` varchar(100) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `imo_number` varchar(20) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `employer` varchar(150) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `rank_held` varchar(100) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `signed_on` date DEFAULT NULL,
  `signed_off` date DEFAULT NULL,
  `remarks` varchar(500) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `added_by` int DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_voyage_app` (`application_id`),
  KEY `idx_voyage_signoff` (`signed_off`),
  CONSTRAINT `fk_voyage_app` FOREIGN KEY (`application_id`) REFERENCES `applications` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_voyage_user` FOREIGN KEY (`added_by`) REFERENCES `users` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

ALTER TABLE `users`
  ADD COLUMN `totp_secret` varchar(64) COLLATE utf8mb4_general_ci DEFAULT NULL AFTER `reset_token_expires`,
  ADD COLUMN `totp_enabled` tinyint(1) NOT NULL DEFAULT 0 AFTER `totp_secret`;
