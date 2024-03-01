
import psycopg2
from fastapi import APIRouter
from dbs_assignment.utils import get_results_as_dict, get_connection

from dbs_assignment.config import settings

router = APIRouter()

@router.get("/v2/posts/{postid}/users")
async def status(postid: int):
    query = f"""
SELECT *                            -- Vyber vsetky riadky
FROM users                          -- Z tabulky users
WHERE id IN (                       -- Kde ID usera
    SELECT userid                   -- Vyber ID usera
    FROM comments                   -- Z tabulky comments
    WHERE postid = {postid}         -- Kde prispevok sa rovna postid
    GROUP BY userid                 -- Zoskupi riadky podla userid (tym padom removne duplicity)
    ORDER BY MAX(creationdate) DESC -- Zoradit od najnovsieho po najstarsi
)
"""

    if postid is None:
        return {"error": "postid is required"}

    connection = get_connection(settings)

    cursor = connection.cursor()
    cursor.execute(query)

    results = get_results_as_dict(cursor)

    connection.close()
    return {
        'items': results
    }
