SELECT year, COUNT(*) AS count
FROM (
    SELECT
        CASE
            WHEN date LIKE '%2021%' THEN '2021'
            WHEN date LIKE '%2022%' THEN '2022'
            WHEN date LIKE '%2023%' THEN '2023'
            WHEN date LIKE '%2024%' THEN '2024'
            WHEN date LIKE '%2025%' THEN '2025'
            WHEN date LIKE '%2026%' THEN '2026'
        END AS year
    FROM texts
)
WHERE year IS NOT NULL
GROUP BY year

UNION ALL

SELECT 'TOTAL', COUNT(*)
FROM (
    SELECT
        CASE
            WHEN date LIKE '%2021%' THEN '2021'
            WHEN date LIKE '%2022%' THEN '2022'
            WHEN date LIKE '%2023%' THEN '2023'
            WHEN date LIKE '%2024%' THEN '2024'
            WHEN date LIKE '%2025%' THEN '2025'
            WHEN date LIKE '%2026%' THEN '2026'
        END AS year
    FROM texts
)
WHERE year IS NOT NULL;