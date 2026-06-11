-- =============================================
-- NSPD Ghana — initial schema for the Python/Vercel version
--
-- Identical to the PHP version's schema with one change: the
-- applications table uses InnoDB instead of MyISAM, because cloud
-- MySQL providers (PlanetScale, Railway, Aiven, RDS) do not support
-- or recommend MyISAM. Columns, types, keys, and defaults are
-- otherwise preserved exactly.
--
-- To migrate existing data, import your mysqldump of nspd_db after
-- running this file (the dump's INSERT statements are compatible).
-- =============================================

-- Users table for authentication & RBAC
CREATE TABLE IF NOT EXISTS `users` (
  `id` int NOT NULL AUTO_INCREMENT,
  `username` varchar(50) COLLATE utf8mb4_general_ci NOT NULL,
  `password_hash` varchar(255) COLLATE utf8mb4_general_ci NOT NULL,
  `full_name` varchar(100) COLLATE utf8mb4_general_ci NOT NULL,
  `role` enum('Administrator','Reviewer','Viewer') COLLATE utf8mb4_general_ci NOT NULL DEFAULT 'Viewer',
  `email` varchar(150) COLLATE utf8mb4_general_ci NOT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `last_login` timestamp NULL DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `username` (`username`),
  UNIQUE KEY `email` (`email`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- Seafarer applications table
CREATE TABLE IF NOT EXISTS `applications` (
  `id` int NOT NULL AUTO_INCREMENT,
  `submitted_at` datetime NOT NULL,
  `surname` varchar(100) COLLATE utf8mb4_general_ci NOT NULL,
  `first_name` varchar(100) COLLATE utf8mb4_general_ci NOT NULL,
  `other_names` varchar(100) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `short_courses_rmu` enum('Yes','No') COLLATE utf8mb4_general_ci NOT NULL,
  `familiarisation_isps_gma` enum('Yes','No') COLLATE utf8mb4_general_ci NOT NULL,
  `position_rank` varchar(100) COLLATE utf8mb4_general_ci NOT NULL,
  `telephone` varchar(100) COLLATE utf8mb4_general_ci NOT NULL,
  `email` varchar(150) COLLATE utf8mb4_general_ci NOT NULL,
  `attachment` text COLLATE utf8mb4_general_ci,
  `sea_experience` text COLLATE utf8mb4_general_ci,
  `total_sea_experience_years` decimal(4,1) DEFAULT NULL,
  `last_ship_type` varchar(150) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `medicals` text COLLATE utf8mb4_general_ci,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- Default admin user (password: admin123)
-- Note: the PHP repo's create_users_table.sql shipped a hash that was
-- actually for the string "password" despite its comment saying admin123;
-- this hash genuinely corresponds to admin123. PHP password_verify()
-- accepts $2b$ hashes too, and the Python backend accepts PHP's $2y$.
-- IMPORTANT: change this password immediately after first login.
INSERT INTO `users` (`username`, `password_hash`, `full_name`, `role`, `email`) VALUES
('admin', '$2b$12$ghyPgA90ka6uJnJhqCtmBe2exZd/ikH3mo5ZHCz7biZDpJFv45jr6', 'Admin User', 'Administrator', 'admin@maritime.port')
ON DUPLICATE KEY UPDATE `username` = `username`;
