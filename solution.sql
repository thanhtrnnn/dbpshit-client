-- ID: a
-- Code: SQL1987
-- Title: Đếm số lượng loài sinh vật biển trong mỗi lưu vực đại dương, không bao gồm các loài có tình trạng bảo tồn 'Ít quan tâm'
-- Yêu cầu: Viết câu lệnh SQL bên dưới
-- ********************************************

INSERT INTO ocean_basin (name, species_count)
SELECT 
    habitat, 
    COUNT(id)
FROM 
    species
WHERE 
    conservation_status <> 'Least Concern'
GROUP BY 
    habitat;