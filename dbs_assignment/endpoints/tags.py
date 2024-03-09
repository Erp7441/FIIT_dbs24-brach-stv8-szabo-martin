from fastapi import APIRouter
from dbs_assignment.utils import get_results_as_kev_val_pair, get_connection

from dbs_assignment.config import settings

router = APIRouter()


@router.get("/v2/tags/{tag_name}/stats")
async def tag_stats(tag_name: str):
    query = f"""
        -- CTE overall poctu postov per weekday
        WITH weekday_counts AS (
            SELECT
                trim(to_char(creationdate, 'day')) AS weekday,  -- Prekonvertovanie creation datumu na den tyzdna
                COUNT(id) AS total_count  -- Pocet vsetkych postov...
            FROM posts p
            GROUP BY weekday  -- ...podla tyzdna
        )
        SELECT
            trim(to_char(p.creationdate, 'day')) AS weekday,  -- Prekonvertovanie creation datumu na den tyzdna
            ROUND(((COUNT(t.tagname)::FLOAT / wc.total_count::FLOAT) * 100)::numeric, 2) AS percent  -- Vypocet percent
        FROM
            tags t
            JOIN post_tags pt ON t.id = pt.tag_id  -- Aby sme vedeli priradit tagname k post_id
            JOIN posts p ON pt.post_id = p.id  -- Aby sme vedelit priradit post_id k samotnemu postu (s jeho attribs)
            -- Spojenie CTE tabulky na tyzdnoch. Tym dostaneme tabulku kde je stlpec overall postov per weekday a
            -- Pocet postov ktore su otagovane tagom ktory zvolime nizsie
            JOIN weekday_counts wc ON trim(to_char(p.creationdate, 'day')) = wc.weekday
        WHERE t.tagname = '{tag_name}' -- odfiltrovanie konkretneho tagu
        GROUP BY trim(to_char(p.creationdate, 'day')), t.tagname, wc.total_count
        ORDER BY
            -- Zoradenie od pondelka po nedelu
            CASE
                WHEN trim(to_char(p.creationdate, 'day')) = 'monday' THEN 1
                WHEN trim(to_char(p.creationdate, 'day')) = 'tuesday' THEN 2
                WHEN trim(to_char(p.creationdate, 'day')) = 'wednesday' THEN 3
                WHEN trim(to_char(p.creationdate, 'day')) = 'thursday' THEN 4
                WHEN trim(to_char(p.creationdate, 'day')) = 'friday' THEN 5
                WHEN trim(to_char(p.creationdate, 'day')) = 'saturday' THEN 6
                WHEN trim(to_char(p.creationdate, 'day')) = 'sunday' THEN 7
            END
    """

    if tag_name is None:
        return {"error": "post_id is required"}

    connection = get_connection(settings)
    cursor = connection.cursor()
    cursor.execute(query)
    results = get_results_as_kev_val_pair(cursor)
    connection.close()

    return {
        'result': results
    }
