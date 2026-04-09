-- Create users table for authentication
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

-- Insert default admin user (password: admin123)
INSERT INTO `users` (`username`, `password_hash`, `full_name`, `role`, `email`) VALUES
('admin', '$2y$10$92IXUNpkjO0rOQ5byMi.Ye4oKoEa3Ro9llC/.og/at2.uheWG/igi', 'Admin User', 'Administrator', 'admin@maritime.port');

-- Insert a sample reviewer (password: reviewer123)
INSERT INTO `users` (`username`, `password_hash`, `full_name`, `role`, `email`) VALUES
('reviewer', '$2y$10$eR8FKXhM0XjKQVzwYkGXsuBJZzXqVJ5JZQX5rW5gQX5rW5gQX5rW5', 'Review User', 'Reviewer', 'reviewer@maritime.port');
