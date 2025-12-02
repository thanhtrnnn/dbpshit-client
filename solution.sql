-- ID: a930864c-30f6-4b17-b760-e198578b0139
-- Code: SQL2759
-- Title: Có bao nhiêu khu bảo tồn ở mỗi quốc gia
-- Yêu cầu: Viết câu lệnh SQL bên dưới
-- ********************************************

SELECT
    c.country_name,
    COUNT(pa.area_id) AS total_areas
FROM
    countries AS c
LEFT JOIN
    protected_areas AS pa ON c.country_id = pa.country_id
GROUP BY
    c.country_name;