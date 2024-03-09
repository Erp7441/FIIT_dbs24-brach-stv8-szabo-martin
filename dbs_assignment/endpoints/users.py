from fastapi import APIRouter
from dbs_assignment.utils import get_results_as_dict, get_connection

from dbs_assignment.config import settings

router = APIRouter()


@router.get("/v2/users/{user_id}/users")
@router.get("/v2/users/{user_id}/friends")
async def get_users_friends(user_id: int):
    query = f"""
        SELECT *
        FROM users -- Vyber userov
        WHERE id IN (
            SELECT DISTINCT userid
            FROM comments
            WHERE postid IN ( -- Ktory komentovali
                SELECT id
                FROM posts
                WHERE posts.owneruserid = {user_id} -- Na poste vytvorenym userom s ID (parentid)
            ) -- AND userid != {user_id} -- Odfiltrovanie usera na ktoreho pozerame TODO:: Podla zadania to mame mat kamarata sameho seba
            GROUP BY userid
        )
        OR id IN (
            SELECT DISTINCT userid
            FROM comments
            WHERE postid IN (
                SELECT postid
                FROM comments
                WHERE userid = {user_id}  -- Je ID postu kde komentoval user
            ) -- AND userid != {user_id} -- Odfiltrovanie usera na ktoreho pozerame TODO:: Podla zadania to mame mat kamarata sameho seba
        )
        ORDER BY users.creationdate
    """

    connection = get_connection(settings)
    cursor = connection.cursor()
    cursor.execute(query)
    results = get_results_as_dict(cursor)
    connection.close()

    return {
        'items': results
    }
