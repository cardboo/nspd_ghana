-- =============================================
-- NSPD Ghana — feature migration 002
-- Adds: application review workflow, user administration columns,
-- reviewer comments, document storage metadata, audit logging,
-- login throttling, and an outbound notification log.
--
-- Run AFTER 001_init.sql (or against an imported v1 database).
-- =============================================

-- ---------------------------------------------
-- 1. Applications: review workflow
--    (from the original scripts/migrate_v2.sql)
-- ---------------------------------------------

-- InnoDB is required for the foreign keys below (v1 dumps used MyISAM)
ALTER TABLE `applications` ENGINE = InnoDB;

ALTER TABLE `applications`
  ADD COLUMN `status` enum('Pending','Under Review','Approved','Rejected')
    COLLATE utf8mb4_general_ci NOT NULL DEFAULT 'Pending'
    AFTER `medicals`,
  ADD COLUMN `reviewed_by` int DEFAULT NULL
    AFTER `status`,
  ADD COLUMN `reviewed_at` timestamp NULL DEFAULT NULL
    AFTER `reviewed_by`;

ALTER TABLE `applications`
  ADD INDEX `idx_position_rank` (`position_rank`),
  ADD INDEX `idx_submitted_at` (`submitted_at`),
  ADD INDEX `idx_email` (`email`),
  ADD INDEX `idx_status` (`status`),
  ADD INDEX `idx_surname_firstname` (`surname`, `first_name`);

ALTER TABLE `applications`
  ADD CONSTRAINT `fk_reviewed_by` FOREIGN KEY (`reviewed_by`) REFERENCES `users` (`id`)
    ON DELETE SET NULL ON UPDATE CASCADE;

-- NOTE: the original migrate_v2.sql also added a UNIQUE (email, telephone)
-- index. It is intentionally NOT applied here because existing data contains
-- duplicate submissions — clean them with the Data Quality page first, then:
--   ALTER TABLE `applications` ADD UNIQUE INDEX `idx_unique_submission` (`email`, `telephone`);

-- ---------------------------------------------
-- 2. Users: administration columns
-- ---------------------------------------------

ALTER TABLE `users`
  ADD COLUMN `is_active` tinyint(1) NOT NULL DEFAULT 1 AFTER `email`,
  ADD COLUMN `must_change_password` tinyint(1) NOT NULL DEFAULT 0 AFTER `is_active`;

-- ---------------------------------------------
-- 3. Reviewer comments on applications
-- ---------------------------------------------

CREATE TABLE IF NOT EXISTS `application_comments` (
  `id` int NOT NULL AUTO_INCREMENT,
  `application_id` int NOT NULL,
  `user_id` int DEFAULT NULL,
  `username` varchar(50) COLLATE utf8mb4_general_ci NOT NULL,
  `comment` text COLLATE utf8mb4_general_ci NOT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_comment_app` (`application_id`),
  CONSTRAINT `fk_comment_app` FOREIGN KEY (`application_id`) REFERENCES `applications` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_comment_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- ---------------------------------------------
-- 4. Uploaded documents (metadata; file bytes live in
--    local disk storage or Vercel Blob depending on driver)
-- ---------------------------------------------

CREATE TABLE IF NOT EXISTS `documents` (
  `id` int NOT NULL AUTO_INCREMENT,
  `application_id` int NOT NULL,
  `doc_type` varchar(50) COLLATE utf8mb4_general_ci NOT NULL DEFAULT 'Other',
  `original_name` varchar(255) COLLATE utf8mb4_general_ci NOT NULL,
  `content_type` varchar(100) COLLATE utf8mb4_general_ci NOT NULL,
  `size_bytes` int NOT NULL,
  `storage_driver` varchar(20) COLLATE utf8mb4_general_ci NOT NULL,
  `storage_key` varchar(500) COLLATE utf8mb4_general_ci NOT NULL,
  `uploaded_by` int DEFAULT NULL,
  `uploaded_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_doc_app` (`application_id`),
  CONSTRAINT `fk_doc_app` FOREIGN KEY (`application_id`) REFERENCES `applications` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_doc_user` FOREIGN KEY (`uploaded_by`) REFERENCES `users` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- ---------------------------------------------
-- 5. Audit log (exports, status changes, user admin, auth events)
-- ---------------------------------------------

CREATE TABLE IF NOT EXISTS `audit_log` (
  `id` int NOT NULL AUTO_INCREMENT,
  `user_id` int DEFAULT NULL,
  `username` varchar(50) COLLATE utf8mb4_general_ci NOT NULL,
  `action` varchar(50) COLLATE utf8mb4_general_ci NOT NULL,
  `entity` varchar(50) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `entity_id` int DEFAULT NULL,
  `details` varchar(500) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `ip_address` varchar(45) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_audit_username` (`username`),
  KEY `idx_audit_action` (`action`),
  KEY `idx_audit_created` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- ---------------------------------------------
-- 6. Login attempts (DB-backed rate limiting — serverless functions
--    cannot keep in-memory counters between invocations)
-- ---------------------------------------------

CREATE TABLE IF NOT EXISTS `login_attempts` (
  `id` int NOT NULL AUTO_INCREMENT,
  `username` varchar(50) COLLATE utf8mb4_general_ci NOT NULL,
  `ip_address` varchar(45) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `success` tinyint(1) NOT NULL DEFAULT 0,
  `attempted_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_attempt_user_time` (`username`, `attempted_at`),
  KEY `idx_attempt_ip_time` (`ip_address`, `attempted_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- ---------------------------------------------
-- 7. Outbound notification log (status-change emails to applicants)
-- ---------------------------------------------

CREATE TABLE IF NOT EXISTS `notifications` (
  `id` int NOT NULL AUTO_INCREMENT,
  `application_id` int DEFAULT NULL,
  `recipient` varchar(150) COLLATE utf8mb4_general_ci NOT NULL,
  `subject` varchar(200) COLLATE utf8mb4_general_ci NOT NULL,
  `body` text COLLATE utf8mb4_general_ci NOT NULL,
  `status` varchar(20) COLLATE utf8mb4_general_ci NOT NULL DEFAULT 'pending',
  `error` varchar(300) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_notif_app` (`application_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
