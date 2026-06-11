-- =============================================
-- NSPD Ghana — feature migration 008: portal invitations
--
-- Staff proactively invite seafarers whose imported records predate the
-- portal: an account is created from the record's email, the record is
-- linked, and the seafarer receives a set-your-password link (7 days).
-- invited_at tracks outreach so unused invitations can be resent.
--
-- Run AFTER 007_doc_verification.sql.
-- =============================================

ALTER TABLE `applicants`
  ADD COLUMN `invited_at` timestamp NULL DEFAULT NULL AFTER `verify_token`;
