BEGIN;

-- INSERT INTO management.study_information_translation (id, language_code, name, master_id) VALUES
-- (1, 'en', 'Clinical surveillance of community-acquired Klebsiella pneumoniae infections', 1),
-- (2, 'vi', 'Đặc điểm nhiễm trùng do Klebsiella pneumoniae độc lực cao mắc phải từ cộng đồng và các yếu tố liên quan', 1),
-- (3, 'vi', 'Khảo sát tỷ lệ mang và mức độ lan truyền của vi khuẩn Escherichia coli và Klebsiella pneumoniae kháng thuốc và độc lực cao trong cộng đồng', 2),
-- (4, 'en', 'Community Carriage and Transmission Rates of Drug-Resistant, Virulent E. coli and K. pneumoniae', 2);

-- INSERT INTO management.study_information (id, code, db_name, status, created_at, updated_at, created_by_id) VALUES
-- (1, '43EN', 'db_study_43en', 'active', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 1),
-- (2, '44EN', 'db_study_44en', 'archived', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 1);

INSERT INTO management.study_sites (id, code, abbreviation, created_at, updated_at) VALUES
(2, '011', 'CRH', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
(1, '003', 'HTD', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
(3, '020', 'NHTD', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);

INSERT INTO management.study_sites_translation (id, language_code, name, master_id) VALUES
(1, 'en', 'Hospital for Tropical Diseases', 1),
(2, 'vi', 'Bệnh viện Bệnh Nhiệt đới', 1),
(3, 'vi', 'Bệnh viện Chợ Rẫy', 2),
(4, 'vi', 'Bệnh viện Bệnh nhiệt đới Trung Ương', 3),
(5, 'en', 'Cho Ray Hospital', 2),
(6, 'en', 'National Hospital for Tropical Diseases', 3);

COMMIT;