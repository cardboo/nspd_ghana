-- =============================================
-- NSPD Ghana — feature migration 007: document verification
--
-- Applicants upload their own documents (including certificate renewals
-- after approval), so staff need a way to mark each file as checked.
--
-- Run AFTER 006_voyages_totp.sql.
-- =============================================

ALTER TABLE `documents`
  ADD COLUMN `verify_status` varchar(20) COLLATE utf8mb4_general_ci NOT NULL DEFAULT 'Pending' AFTER `storage_key`,
  ADD COLUMN `verified_by` int DEFAULT NULL AFTER `verify_status`,
  ADD COLUMN `verified_at` timestamp NULL DEFAULT NULL AFTER `verified_by`,
  ADD CONSTRAINT `fk_doc_verifier` FOREIGN KEY (`verified_by`) REFERENCES `users` (`id`) ON DELETE SET NULL;
