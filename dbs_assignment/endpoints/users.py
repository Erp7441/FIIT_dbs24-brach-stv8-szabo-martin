from fastapi import APIRouter
from dbs_assignment.utils import get_results_as_dict, get_connection

from dbs_assignment.config import settings

router = APIRouter()


@router.get("/v2/users/{user_id}/users")
@router.get("/v2/users/{user_id}/friends")
async def get_users_friends(user_id: int):
    query = f"""
        SELECT
            id, reputation,
            (to_char(creationdate AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.MSOF')) AS creationdate,
            displayname,
            (to_char(lastaccessdate::TIMESTAMP AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.MSOF') ) AS lastaccessdate,
            websiteurl, location, aboutme, views, upvotes, downvotes, profileimageurl, age, accountid
        FROM users
        -- Kde user_id sa nachadza v subquery userov ktory komentovali na poste ktory bol vytvoreny hladanym pouzivatelom
        WHERE id IN (
            -- Ziskaj userov ktory komentovali na poste ktory bol vytvoreny hladanym pouzivatelom
            SELECT DISTINCT userid
            FROM comments
            WHERE postid IN (
                SELECT id
                FROM posts
                WHERE posts.owneruserid = {user_id} -- Post vytvorenym hladanym pouzivatelom
            ) -- AND userid != 1 -- Odfiltrovanie usera na ktoreho pozerame TODO:: Podla zadania mame mat kamarata seba
            GROUP BY userid
        )
        -- Alebo sa user_id nachadza v subquery userov ktory komentovali na poste na ktorom komentoval hladany pouzivatel
        OR id IN (
            -- Ziskaj userov ktory komentovali na poste na ktorom komentoval hladany pouzivatel
            SELECT DISTINCT userid
            FROM comments
            WHERE postid IN (
                SELECT postid
                FROM comments
                WHERE userid = {user_id}  -- Post kde komentoval hladany pouzivatel
            ) -- AND userid != 1 -- Odfiltrovanie usera na ktoreho pozerame TODO:: Podla zadania mame mat kamarata seba
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


# Zadanie 3 endpoint 1
@router.get("/v3/users/{user_id}/badge_history")
async def get_user_badge_history(user_id: int):
    query = f"""
        SELECT
            badge_id, badge_name,
            TO_CHAR(badge_date AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.MSOF:TZM') AS badge_date,
            post_id, post_title,
            TO_CHAR(post_date AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.MSOF:TZM') AS post_date
        FROM (
            SELECT
                -- Filtrovanie unikatnych datumov postov kedze pokial viacero badgov bolo ziskanych za jeden
                -- post. Mame zobrat len prvy badge ktory bol ziskany za ten komentar a vylucit ho z moznosti.
                DISTINCT ON (post_date)
                *
            FROM (
                SELECT
                    DISTINCT ON (badge_id)  -- Vyfiltrovanie duplikatov z subquery
                    *
                FROM (
                    -- Ziska badge info + posty ktore boli vytvorene skor ako badge
                    SELECT
                        b2.id AS badge_id,
                        b2.name AS badge_name,
                        b2.date AS badge_date,
                        p2.id AS post_id,
                        p2.creationdate AS post_date,
                        p2.title AS post_title
                    -- Vytvori tabulu s infom o useroch, ich badges a ich postoch
                    FROM users
                        JOIN badges b2 ON users.id = b2.userid
                        JOIN posts p2 ON p2.owneruserid = b2.userid
                    -- Filtrovanie userid a vsetkych postov ktore boli vytvorene skor ako badge
                    WHERE users.id = {user_id} AND b2.date >= p2.creationdate  -- userid je parameter
                ) AS bp
                ORDER BY badge_id, bp.post_date DESC  -- Toto zaruci ze zaznamy su zoradene od najnovsieho postu.
                -- To znamena ze DISTINCT na zaciatku odfiltruje vsetky stare posty
            ) AS s
            ORDER BY post_date, post_id
        ) AS m
    """

    if user_id is None:
        return {"error": "user_id is required"}

    connection = get_connection(settings)
    cursor = connection.cursor()
    cursor.execute(query)
    results = get_results_as_dict(cursor)
    connection.close()
    formatted_results = []

    for result in results:
        formatted_results.append({
            'id': result['post_id'],
            'title': result['post_title'],
            'type': 'post',
            'created_at': result['post_date'],
            'position': results.index(result)+1
        })
        formatted_results.append({
            'id': result['badge_id'],
            'title': result['badge_name'],
            'type': 'badge',
            'created_at': result['badge_date'],
            'position': results.index(result)+1
        })

    return {
        'items': formatted_results
    }
