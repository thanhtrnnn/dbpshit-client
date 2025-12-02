-- ID: 360518cb-fb15-47bb-9b98-b76e01a39f40
-- Code: SQL130
-- Title: Product  Sales Anaysis
-- Yêu cầu: Viết câu lệnh SQL bên dưới
-- ********************************************

SELECT p.product_name, s.year, s.price
FROM Sales s
JOIN Product p ON s.product_id = p.product_id;  