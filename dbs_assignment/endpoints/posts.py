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

@router.get("/v2/posts/")
async def get_post_comments(limit: int, query: str):
    sql_query = """

    """

    connection = get_connection(settings)
    cursor = connection.cursor()
    cursor.execute(sql_query)
    results = get_results_as_dict(cursor)
    connection.close()

    return {
        'items': results
    }
