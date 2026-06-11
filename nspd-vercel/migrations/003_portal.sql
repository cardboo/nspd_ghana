-- =============================================
-- NSPD Ghana — feature migration 003: applicant portal
--
-- Seafarers get their own accounts (separate from staff `users` for
-- security), self-register with email verification, and own at most
-- one application which they can edit while it is Pending/Rejected.
--
-- Run AFTER 002_features.sql.
-- =============================================

CREATE TABLE IF NOT EXISTS `applicants` (
  `id` int NOT NULL AUTO_INCREMENT,
  `email` varchar(150) COLLATE utf8mb4_general_ci NOT NULL,
  `password_hash` varchar(255) COLLATE utf8mb4_general_ci NOT NULL,
  `full_name` varchar(150) COLLATE utf8mb4_general_ci NOT NULL,
  `email_verified` tinyint(1) NOT NULL DEFAULT 0,
  `verify_token` varchar(64) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `last_login` timestamp NULL DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `email` (`email`),
  KEY `idx_applicant_verify` (`verify_token`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- Link portal-submitted applications to their owning account.
-- Legacy/imported applications keep NULL here.
ALTER TABLE `applications`
  ADD COLUMN `applicant_id` int DEFAULT NULL AFTER `reviewed_at`,
  ADD INDEX `idx_applications_applicant` (`applicant_id`),
  ADD CONSTRAINT `fk_app_applicant` FOREIGN KEY (`applicant_id`) REFERENCES `applicants` (`id`)
    ON DELETE SET NULL ON UPDATE CASCADE;
