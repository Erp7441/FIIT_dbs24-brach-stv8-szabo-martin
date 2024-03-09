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


@router.get("/v2/posts/")
async def get_post_comments(duration: int, limit: int):
    query = """
        WITH closed_posts_duration AS (
            SELECT id, round((extract(EPOCH from (closeddate - creationdate))::decimal / 60), 2) as duration
            FROM posts
            WHERE closeddate IS NOT NULL
            ORDER BY id
        )
        SELECT posts.id, creationdate, viewcount, lasteditdate, lastactivitydate, title, closeddate, duration
        FROM closed_posts_duration
        JOIN posts ON posts.id = closed_posts_duration.id
        WHERE duration <= 5
        ORDER BY creationdate DESC
        LIMIT 2
    """

    connection = get_connection(settings)
    cursor = connection.cursor()
    cursor.execute(query)
    results = get_results_as_dict(cursor)
    connection.close()

    return {
        'items': results
    }
