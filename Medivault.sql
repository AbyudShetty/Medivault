CREATE DATABASE MediVault;
USE MediVault;

-- User table: Core user information
CREATE TABLE user (
    user_id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    phone VARCHAR(15),
    dob DATE,
    gender VARCHAR(10),
    blood_group VARCHAR(5),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_email (email)
);

-- Prescription table: Stores user prescriptions with OCR-extracted data
CREATE TABLE prescription (
    prescription_id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    issue VARCHAR(200) NOT NULL,
    description TEXT,
    doctor_name VARCHAR(100),
    prescription_date DATE,
    notes TEXT,
    file_path VARCHAR(255),
    extracted_text TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES user(user_id) ON DELETE CASCADE,
    INDEX idx_user_issue (user_id, issue),
    INDEX idx_user_date (user_id, prescription_date),
    FULLTEXT idx_issue_desc (issue, description)
);

-- Add medicine_count column after prescription table creation
ALTER TABLE prescription ADD COLUMN medicine_count INT DEFAULT 0;

-- Prescription Medication table: Links medicines to prescriptions
CREATE TABLE prescription_medication (
    pm_id INT PRIMARY KEY AUTO_INCREMENT,
    prescription_id INT NOT NULL,
    medicine_name VARCHAR(100) NOT NULL,
    dosage VARCHAR(50),
    frequency VARCHAR(50),
    duration VARCHAR(50),
    notes TEXT,
    FOREIGN KEY (prescription_id) REFERENCES prescription(prescription_id) ON DELETE CASCADE,
    INDEX idx_prescription (prescription_id),
    INDEX idx_medicine_name (medicine_name)
);

-- Medicine table: Master data for medicines
CREATE TABLE medicine (
    medicine_id INT PRIMARY KEY AUTO_INCREMENT,
    medicine_name VARCHAR(100) UNIQUE NOT NULL,
    common_dosage VARCHAR(50),
    common_frequency VARCHAR(50),
    INDEX idx_name (medicine_name)
);

-- Modify prescription_medication to reference medicine table (3NF compliant)
ALTER TABLE prescription_medication ADD COLUMN medicine_id INT,
ADD FOREIGN KEY (medicine_id) REFERENCES medicine(medicine_id);

-- Prescription Log table: For auditing prescription changes (used by triggers)
CREATE TABLE IF NOT EXISTS prescription_log (
    log_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    prescription_id INT,
    action_type VARCHAR(50),
    action_timestamp DATETIME,
    FOREIGN KEY (user_id) REFERENCES user(user_id) ON DELETE CASCADE
);

-- Show created tables
SHOW TABLES;

DELIMITER //

-- TRIGGER 1: Auto-log prescription creation
CREATE TRIGGER after_prescription_insert
AFTER INSERT ON prescription
FOR EACH ROW
BEGIN
    INSERT INTO prescription_log (user_id, prescription_id, action_type, action_timestamp)
    VALUES (NEW.user_id, NEW.prescription_id, 'CREATED', NOW());
END//

-- TRIGGER 2: Auto-log prescription deletion
CREATE TRIGGER after_prescription_delete
AFTER DELETE ON prescription
FOR EACH ROW
BEGIN
    INSERT INTO prescription_log (user_id, prescription_id, action_type, action_timestamp)
    VALUES (OLD.user_id, OLD.prescription_id, 'DELETED', NOW());
END//

-- TRIGGER 3: Auto-update medicine count on insertion
CREATE TRIGGER after_medicine_insert
AFTER INSERT ON prescription_medication
FOR EACH ROW
BEGIN
    UPDATE prescription
    SET medicine_count = medicine_count + 1
    WHERE prescription_id = NEW.prescription_id;
END//

DELIMITER ;

DELIMITER //

-- PROCEDURE 1: Get prescription summary for a user
CREATE PROCEDURE GetPrescriptionSummary(IN userId INT)
BEGIN
    SELECT
        COUNT(*) as total_prescriptions,
        COUNT(DISTINCT doctor_name) as total_doctors,
        COUNT(DISTINCT DATE_FORMAT(created_at, '%Y-%m')) as active_months
    FROM prescription
    WHERE user_id = userId;
END//

-- PROCEDURE 2: Search medicines by query for a user
CREATE PROCEDURE SearchMedicines(IN userId INT, IN searchQuery VARCHAR(255))
BEGIN
    SELECT
        p.prescription_id,
        p.issue,
        p.doctor_name,
        p.prescription_date,
        pm.medicine_name,
        pm.dosage,
        pm.frequency
    FROM prescription p
    INNER JOIN prescription_medication pm ON p.prescription_id = pm.prescription_id
    WHERE p.user_id = userId
    AND (
        LOWER(pm.medicine_name) LIKE CONCAT('%', LOWER(searchQuery), '%')
        OR LOWER(p.issue) LIKE CONCAT('%', LOWER(searchQuery), '%')
    )
    ORDER BY p.created_at DESC;
END//

-- PROCEDURE 3: Get medicine usage statistics for a user
CREATE PROCEDURE GetMedicineStats(IN userId INT)
BEGIN
    SELECT
        pm.medicine_name,
        COUNT(*) as usage_count,
        GROUP_CONCAT(DISTINCT pm.dosage) as dosages_used,
        AVG(DATEDIFF(NOW(), p.created_at)) as avg_days_since_last_use
    FROM prescription p
    INNER JOIN prescription_medication pm ON p.prescription_id = pm.prescription_id
    WHERE p.user_id = userId
    GROUP BY pm.medicine_name
    ORDER BY usage_count DESC
    LIMIT 10;
END//

DELIMITER ;

DELIMITER //

-- FUNCTION 1: Calculate days since last prescription for a specific issue
CREATE FUNCTION GetDaysSinceLastIssue(userId INT, issueText VARCHAR(200))
RETURNS INT
DETERMINISTIC
BEGIN
    DECLARE days INT;
    SELECT DATEDIFF(NOW(), MAX(prescription_date)) INTO days
    FROM prescription
    WHERE user_id = userId AND issue = issueText;
    RETURN COALESCE(days, -1);
END//

-- FUNCTION 2: Get total medicine count for a user
CREATE FUNCTION GetTotalMedicinesUsed(userId INT)
RETURNS INT
DETERMINISTIC
BEGIN
    DECLARE total INT;
    SELECT COUNT(*) INTO total
    FROM prescription_medication pm
    INNER JOIN prescription p ON pm.prescription_id = p.prescription_id
    WHERE p.user_id = userId;
    RETURN total;
END//

DELIMITER ;
