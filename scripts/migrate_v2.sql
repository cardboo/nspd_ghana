-- =============================================
-- NSPD Ghana v2 Migration Script
-- Run this on an existing v1 database to upgrade
-- =============================================

-- 1. Convert applications table from MyISAM to InnoDB
ALTER TABLE `applications` ENGINE = InnoDB;

-- 2. Add status column for application workflow
ALTER TABLE `applications`
  ADD COLUMN `status` enum('Pending','Under Review','Approved','Rejected')
    COLLATE utf8mb4_general_ci NOT NULL DEFAULT 'Pending'
    AFTER `medicals`,
  ADD COLUMN `reviewed_by` int DEFAULT NULL
    AFTER `status`,
  ADD COLUMN `reviewed_at` timestamp NULL DEFAULT NULL
    AFTER `reviewed_by`;

-- 3. Add indexes for commonly queried columns
ALTER TABLE `applications`
  ADD INDEX `idx_position_rank` (`position_rank`),
  ADD INDEX `idx_submitted_at` (`submitted_at`),
  ADD INDEX `idx_email` (`email`),
  ADD INDEX `idx_status` (`status`),
  ADD INDEX `idx_surname_firstname` (`surname`, `first_name`);

-- 4. Add unique constraint to prevent duplicate submissions
-- Uses email + telephone as a combined unique key
ALTER TABLE `applications`
  ADD UNIQUE INDEX `idx_unique_submission` (`email`, `telephone`);

-- 5. Add foreign key from reviewed_by to users
ALTER TABLE `applications`
  ADD CONSTRAINT `fk_reviewed_by` FOREIGN KEY (`reviewed_by`) REFERENCES `users` (`id`)
    ON DELETE SET NULL ON UPDATE CASCADE;
