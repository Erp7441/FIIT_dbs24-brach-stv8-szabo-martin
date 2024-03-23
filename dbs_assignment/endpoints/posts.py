from typing import Optional

from fastapi import APIRouter
from dbs_assignment.utils import get_results_as_dict, get_connection

from dbs_assignment.config import settings

router = APIRouter()


@router.get("/v2/posts/{post_id}/users")
async def get_post_comments(post_id: int):
    query = f"""
        -- Docastna tabulka CTE s komentarami userov na danom poste zoradena od najnovsieho po najstarsi
        WITH user_comments AS (
            SELECT userid, creationdate  -- Select userov a datumom kedy vytvorili komentar
            FROM comments  -- Z tabulky comments
            WHERE postid = {post_id}  -- Postu s ID
            ORDER BY creationdate DESC -- Zorad od najnovejsieho po najstarsi
        ),
        -- CTE s unikatnymi usermi s poslednimi komentarami
        unique_users AS (
            -- Vyber unikatnych userov z CTE user_comments s datumom ich poslednimi komentarami
            SELECT DISTINCT ON (userid) userid, creationdate AS lastcommentcreationdate
            FROM user_comments
        )
        SELECT
            id, reputation,
            -- Konverzia casu do UTC ISO8601
            (to_char(creationdate AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.MSOF')) AS creationdate,
            displayname,
            (to_char(lastaccessdate::TIMESTAMP AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.MSOF')) AS lastaccessdate,
            websiteurl, location, aboutme, views, upvotes, downvotes, profileimageurl, age, accountid
        FROM users
        -- Spojenie tabuliek o userov a unique_users CTE aby sme naparovali k userom datum ich latest komentare
        JOIN unique_users ON users.id = unique_users.userid
        ORDER BY lastcommentcreationdate DESC  -- Sort od najnovsieho po najstarsi komentar
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
async def posts_args(limit: int, duration: Optional[int] = None, query: Optional[str] = None):
    if duration is not None:
        return await get_solved_posts(duration, limit)
    if query is not None:
        return await search_for_posts(limit, query)


async def get_solved_posts(duration: int, limit: int):
    query = f"""
        -- CTE s zavretymi postami a casom ich trvania (closed - creation time) v minutach zaokruhlenym na 2 desatinne miesta
        WITH closed_posts_duration AS (
            SELECT
                posts.id,
                (to_char(creationdate AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.MSOF')) AS creationdate,
                viewcount,
                (to_char(lasteditdate AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.MSOF')) AS lasteditdate,
                (to_char(lastactivitydate AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.MSOF')) AS lastactivitydate,
                title,
                (to_char(closeddate AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.MSOF')) AS closeddate,
                round((extract(EPOCH from (closeddate - creationdate))::decimal / 60), 2) as duration
            FROM posts
            WHERE closeddate IS NOT NULL
        )
        -- Vyber vsetkych udajov o postoch ktore su kratsie alebo rovnako dlhe ako duration
        SELECT *
        FROM closed_posts_duration
        WHERE duration <= {duration}  -- Parameter duration
        ORDER BY creationdate DESC
        LIMIT {limit}  -- Limit poctu postov vyobrazenych
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
        -- CTE postov s zoznamom tagov
        WITH post_id_tags AS (
            -- Vyber vsetkych post_id s zoznamom tagov
            SELECT post_id, array_agg(tagname) as tags
            FROM post_tags
            -- Spojenie tabuliek mien tagov a posts_tags podla ID aby sme dostali tabulku post_id s listom mien ich tagov
            JOIN tags ON post_tags.tag_id = tags.id
            GROUP BY post_id
        )
        SELECT
            id,
            (to_char(creationdate AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.MSOF')) AS creationdate,
            viewcount,
            (to_char(lasteditdate AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.MSOF')) AS lasteditdate,
            (to_char(lastactivitydate AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.MSOF')) AS lastactivitydate,
            title, body, answercount,
            (to_char(closeddate AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.MSOF')) AS closeddate,
            tags
        FROM posts
        -- Spojenie s posts tabulkou na IDcke aby sme dostali zoznam postov s ich atributmi + novym zoznamom tags
        JOIN post_id_tags ON post_id = posts.id
        -- Vyhladavanie stringu v tele a v titulku postu
        WHERE posts.title LIKE '%{query}%' OR posts.body LIKE '%{query}%'
        ORDER BY creationdate DESC
        LIMIT {limit}  -- Limit poctu postov
    """

    connection = get_connection(settings)
    cursor = connection.cursor()
    cursor.execute(sql_query)
    results = get_results_as_dict(cursor)
    connection.close()

    return {
        'items': results
    }


@router.get("/v3/posts/{post_id}")
async def get_post_thread(post_id: int, limit: int):
    sql_query = f"""
        SELECT
            displayname, body,
            TO_CHAR(p.creationdate AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.MSOF:TZM') AS creationdate
        FROM posts p
        LEFT JOIN users u ON p.owneruserid = u.id
        WHERE p.id = {post_id} OR p.parentid = {post_id}  -- Parametre
        ORDER BY p.creationdate
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
