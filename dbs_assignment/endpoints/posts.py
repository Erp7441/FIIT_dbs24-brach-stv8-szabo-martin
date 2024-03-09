from typing import Optional

from fastapi import APIRouter
from dbs_assignment.utils import get_results_as_dict, get_connection

from dbs_assignment.config import settings

router = APIRouter()


@router.get("/v2/posts/{post_id}/users")
async def get_post_comments(post_id: int):
    query = f"""
        WITH user_comments AS (
            SELECT userid, creationdate
            FROM comments
            WHERE postid = {post_id}
            ORDER BY creationdate DESC
        ),
        unique_users AS (
            SELECT DISTINCT ON (userid) userid, creationdate AS lastcommentcreationdate
            FROM user_comments
        )
        SELECT users.*
        FROM users
        JOIN unique_users ON users.id = unique_users.userid
        ORDER BY lastcommentcreationdate DESC
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
async def posts_args(limit: int, duration: Optional[int] = None, query: Optional[str] = None):
    if duration is not None:
        return await get_solved_posts(duration, limit)
    if query is not None:
        return await search_for_posts(limit, query)


async def get_solved_posts(duration: int, limit: int):
    query = f"""
        WITH closed_posts_duration AS (
            SELECT id, round((extract(EPOCH from (closeddate - creationdate))::decimal / 60), 2) as duration
            FROM posts
            WHERE closeddate IS NOT NULL
            ORDER BY id
        )
        SELECT posts.id, creationdate, viewcount, lasteditdate, lastactivitydate, title, closeddate, duration
        FROM closed_posts_duration
        JOIN posts ON posts.id = closed_posts_duration.id
        WHERE duration <= {duration}
        ORDER BY creationdate DESC
        LIMIT {limit}
    """

    connection = get_connection(settings)
    cursor = connection.cursor()
    cursor.execute(query)
    results = get_results_as_dict(cursor)
    connection.close()

    return {
        'items': results
    }


async def search_for_posts(limit: int, query: str):
    sql_query = f"""
        WITH post_id_tags AS (
            SELECT post_id, array_agg(tagname) as tags
            FROM post_tags
            JOIN tags ON post_tags.tag_id = tags.id
            GROUP BY post_id
        )
        SELECT id, creationdate, viewcount, lasteditdate, lastactivitydate, title, body, answercount, closeddate, tags
        FROM posts
        JOIN post_id_tags ON post_id = posts.id
        WHERE posts.title LIKE '%{query}%' OR posts.body LIKE '%{query}%'
        ORDER BY creationdate DESC
        LIMIT {limit}
    """

    connection = get_connection(settings)
    cursor = connection.cursor()
    cursor.execute(sql_query)
    results = get_results_as_dict(cursor)
    connection.close()

    return {
        'items': results
    }
