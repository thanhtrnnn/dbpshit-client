-- ID: 85c86c6f-99f1-452b-bf0c-1edd9a0bcd77
-- Code: SQL2001
-- Title: Thêm cồn 'CBD' 'Thư giãn' vào phòng cấp phát 'Healing Haven'.
-- Yêu cầu: Viết câu lệnh SQL bên dưới
-- ********************************************

INSERT INTO inventory (product_id, dispensary_id, price, quantity)
SELECT
  (SELECT product_id FROM products WHERE name = 'CBD Tincture' AND type = 'Relax'),
  (SELECT dispensary_id FROM dispensaries WHERE name = 'Healing Haven'),
  0, -- Assuming price is 0 initially as not specified
  0; -- Assuming quantity is 0 initially as not specified