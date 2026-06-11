-- =============================================
-- NSPD Ghana — feature migration 004: account recovery
--
-- Self-service password reset for both staff and applicants, plus
-- applicant account deactivation for staff administration.
--
-- Run AFTER 003_portal.sql.
-- =============================================

-- Staff password reset tokens
ALTER TABLE `users`
  ADD COLUMN `reset_token` varchar(64) COLLATE utf8mb4_general_ci DEFAULT NULL AFTER `must_change_password`,
  ADD COLUMN `reset_token_expires` timestamp NULL DEFAULT NULL AFTER `reset_token`,
  ADD INDEX `idx_users_reset` (`reset_token`);

-- Applicant password reset tokens + deactivation flag
ALTER TABLE `applicants`
  ADD COLUMN `is_active` tinyint(1) NOT NULL DEFAULT 1 AFTER `email_verified`,
  ADD COLUMN `reset_token` varchar(64) COLLATE utf8mb4_general_ci DEFAULT NULL AFTER `verify_token`,
  ADD COLUMN `reset_token_expires` timestamp NULL DEFAULT NULL AFTER `reset_token`,
  ADD INDEX `idx_applicants_reset` (`reset_token`);
