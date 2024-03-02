from fastapi import APIRouter
from dbs_assignment.utils import get_results_as_dict, get_connection

from dbs_assignment.config import settings

router = APIRouter()


@router.get("/v2/posts/{post_id}/users")
async def get_post_comments(post_id: int):
    query = f"""
SELECT *
FROM users
WHERE id IN (                       -- Vyber vsetko z tabulky users
    SELECT userid
    FROM comments                   -- o useroch v "userid" stlpci tabulky comments
    WHERE postid = {post_id}        -- konkretneho prispevku
    GROUP BY userid                 -- Toto zoskupi riadky podla userid (tym padom removne duplicity)
    ORDER BY MAX(creationdate) DESC -- Zoradit od najnovsieho po najstarsi s tym ze berieme vzdy najnovejsi prispevok
)
"""

    if post_id is None:
        return {"error": "post_id is required"}

    connection = get_connection(settings)
    cursor = connection.cursor()
    cursor.execute(query)
    results = get_results_as_dict(cursor)
    connection.close()

    return {
        'items': results
    }
