from fastapi import APIRouter
from dbs_assignment.utils import get_results_as_kev_val_pair, get_results_as_dict, get_connection

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
        return {"error": "tag_name is required"}

    connection = get_connection(settings)
    cursor = connection.cursor()
    cursor.execute(query)
    results = get_results_as_kev_val_pair(cursor)
    connection.close()

    return {
        'result': results
    }


# Zadanie 3 endpoint 2
@router.get("/v3/tags/{tag_name}/comments")
async def get_tag_comments(tag_name: str, count: int):
    query = f"""
        SELECT
            post_id, title, displayname, text,
            TO_CHAR(posts_created_at AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.MSOF:TZM') AS posts_created_at,
            TO_CHAR(created_at AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.MSOF:TZM') AS created_at,
            -- Kedze mam datum posledneho komentu alebo vytvorenia postu v 'last_comment_date', tak sa vypocitam cas
            -- medzi vytvorenim komentara a 'last_comment_date' ako diff. To iste aj pre average diff od prveho po
            -- "momentalny" komentar.
            TO_CHAR((created_at - last_comment_date), 'HH24:MI:SS.MS') AS diff,
            TO_CHAR(AVG((created_at - last_comment_date)) OVER (ORDER BY created_at), 'HH24:MI:SS.MS') AS avg_diff
        FROM (
            -- Vyber komentarov s postami usermi a tagmi.
            SELECT
                p.id AS post_id,
                title,
                displayname,
                c.text AS text,
                p.creationdate AS posts_created_at,
                c.creationdate AS created_at,
                -- Ziskanie datumu posledneho komentara ALEBO datumu vytvorenia postu pokial komentar neexistuje.
                COALESCE((
                    SELECT creationdate
                    FROM comments
                    WHERE postid = p.id AND creationdate < c.creationdate
                    ORDER BY creationdate DESC
                    LIMIT 1
                ),(
                    SELECT creationdate
                    FROM posts
                    WHERE id = p.id
                )) AS last_comment_date
            FROM
                comments c
                JOIN posts p ON c.postid = p.id
                LEFT JOIN users u ON c.userid = u.id
                JOIN post_tags pt on p.id = pt.post_id
                JOIN tags t on t.id = pt.tag_id
            -- Filtrovanie tagu a poctu komentarov na poste
            WHERE tagname = '{tag_name}' AND p.commentcount > {count}  -- Parametre
        ) AS m
        ORDER BY posts_created_at, created_at
    """

    if tag_name is None or count is None:
        return {"error": "Missing parameters."}

    connection = get_connection(settings)
    cursor = connection.cursor()
    cursor.execute(query)
    results = get_results_as_dict(cursor)
    connection.close()

    return {
        'items': results
    }


# Zadanie 3 endpoint 3
@router.get("/v3/tags/{tag_name}/comments/{position}")
async def get_tag_k_comments(tag_name: str, position: int, limit: int):
    query = f"""
        SELECT
            id, displayname, body, text, score, position
        FROM (
            -- Tabulka kde si najoinujem dohromady komentare, posty ktorym patria, tagoch tych postov a userov ktory
            -- vytvorili ten komentar
            SELECT
                c.id AS id,
                displayname, body, text,
                c.score AS score,
                -- Kalkulacia pozicie komentara v tabulke comments pomocou row number window funkcie
                -- Pozicia komentara je relativna v ramci postu
                ROW_NUMBER() OVER (PARTITION BY p.id ORDER BY c.id) AS position,
                TO_CHAR(p.creationdate AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.MSOF:TZM') AS creationdate
            FROM comments c
            JOIN posts p ON c.postid = p.id
            JOIN post_tags pt on pt.post_id = p.id
            JOIN tags t on pt.tag_id = t.id
            LEFT JOIN users ON c.userid = users.id
            -- Odfiltrovanie podla tagnamu
            WHERE tagname = '{tag_name}'  -- Parameter
        ) AS s
        -- Filtrovanie kazdeho K komentara podla pozicie
        WHERE position = {position}  -- Parameter
        ORDER BY creationdate
        LIMIT {limit}  -- Parameter
    """

    if tag_name is None or position is None or limit is None:
        return {"error": "Missing parameters."}

    connection = get_connection(settings)
    cursor = connection.cursor()
    cursor.execute(query)
    results = get_results_as_dict(cursor)
    connection.close()

    return {
        'items': results
    }
