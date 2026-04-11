SELECT *
FROM (
    SELECT 
        t.*,
        SUBSTR(t.url, INSTR(t.url, '//') + 2,
               INSTR(SUBSTR(t.url, INSTR(t.url, '//') + 2), '/') - 1) AS domain,
        ROW_NUMBER() OVER (
            PARTITION BY 
                SUBSTR(t.url, INSTR(t.url, '//') + 2,
                       INSTR(SUBSTR(t.url, INSTR(t.url, '//') + 2), '/') - 1)
            ORDER BY RANDOM()
        ) AS rn
    FROM texts t
)
WHERE rn = 1;