# Zadanie 2 - Dokumentacia

## Table of contents
<!-- TOC -->
* [Zadanie 2 - Dokumentacia](#zadanie-2---dokumentacia)
  * [Table of contents](#table-of-contents)
  * [Endpoint 1 - /v2/posts/:post id/users](#endpoint-1---v2postspost-idusers)
  * [Endpoint 2 - /v2/users/:user id/friends alebo /v2/users/:user id/users](#endpoint-2---v2usersuser-idfriends-alebo-v2usersuser-idusers)
  * [Endpoint 3 - /v2/tags/:tagname/stats](#endpoint-3---v2tagstagnamestats)
  * [Endpoint 4 - /v2/posts/?duration=:duration in minutes&limit=:limit](#endpoint-4---v2postsdurationduration-in-minuteslimitlimit)
  * [Endpoint 5 - /v2/posts?limit=:limit&query=:query](#endpoint-5---v2postslimitlimitqueryquery)
<!-- TOC -->


## Endpoint 1 - /v2/posts/:post id/users
Najskôr získam všetky komentáre userov zoradene od najnovšieho po najstarší. Tato subquery mi vráti stĺpec s user_id usera ktorý vytvoril komentár a stĺpec dátumom vytvorenia komentára.

Potom nájdem všetky unikátne user_id z tejto CTE subquery. Keďže je zoradená od najnovšieho po najstarší tak dostanem tabuľku s user_id a dátumom latest komentára ktorý spravili.

Následne selectnem info o useroch z users tabuľky a pomocou inner joinu spojím s CTE tabuľkou s unique usermi (unikátne user IDcky) a dátumom ich posledného komentára na stĺpci user_id a tým dostanem tabuľku users s dátumom latest komentára.

```sql
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
```


## Endpoint 2 - /v2/users/:user id/friends alebo /v2/users/:user id/users
Vyberiem si info z tabuľky users kde id používateľa bude:
* Z tabuľky komentárov kde post bude patriť hľadanému používateľovi.
* Alebo bude opäť z tabuľky komentárov kde post_id bude patriť postu na ktorom komentoval aj hľadaný používateľ.

```sql
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
        WHERE posts.owneruserid = {post_id} -- Post vytvorenym hladanym pouzivatelom
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
        WHERE userid = {post_id}  -- Post kde komentoval hladany pouzivatel
    ) -- AND userid != 1 -- Odfiltrovanie usera na ktoreho pozerame TODO:: Podla zadania mame mat kamarata seba
)
ORDER BY users.creationdate
```

## Endpoint 3 - /v2/tags/:tagname/stats
Najskôr si získam overall počet postov, prekonvertujem creation dátum na deň v týždni a zgrupujem podľa dna týždňa. Tým získam počet postov pre každý deň v týždni.

Následne spojím tabuľky tags, post_tags, posts CTE weekday_counts dokopy na to aby som vedel k postu priradiť jeho tagy a zároveň aby som vedel odfiltrovať v aký weekday bol post vytvorený.

Potom si odfiltrujem daný 'tag_name' a spočítam ho na to aby som dostal číslo koľko postov bolo otagovanych s tagom 'tag_name'. Výsledky zgrupujem podľa mena dna týždňa a percentuálnu reprezentáciu tagu v rámci postov získam tak že podelím počet postov otagovanych tagom a celkový počet postov krát 100.

```sql
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
```

## Endpoint 4 - /v2/posts/?duration=:duration in minutes&limit=:limit

Získam údaje o postoch ktorých close date nie je null a pridám novy stĺpec s hodnotou rozdielu medzi dátumom
uzavretia postu a dátumom vytvorenia postu. Tento udaj prekonvertujem na minúty. Tým dostanem novy stĺpec 'duration' v minútach.

Následne si odfiltrujem posty z predchádzajúcej subquery ktoré majú duration menší alebo rovný želanej hodnote a zoradím od najnovšieho po najstarší a limitujem dĺžku výstupu na želanú hodnotu.

```sql
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
```


## Endpoint 5 - /v2/posts?limit=:limit&query=:query

Najskôr spojím tabuľku post_tags ktorá ma stĺpce post_id a tag_id s tabuľkou tags ktorá obsahuje samotne mena tagov.
Potom agregujem dohromady stĺpce ktoré majú rovnakú post_id. Tým dostanem tabuľku s dvoma stĺpcami:
* post_id - ktorý je za každým unikátna hodnota
* tags - ktorý obsahuje list tagov ktorými je post otagovany.

Následne si získam info z posts tabuľky. Spojím posts tabuľku s CTE

```sql
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
```
