# Zadanie 3 - Dokumentacia

## Table of contents
<!-- TOC -->
* [Zadanie 3 - Dokumentacia](#zadanie-3---dokumentacia)
  * [Table of contents](#table-of-contents)
  * [Endpoint 1 - /v3/users/:userid/badge history](#endpoint-1---v3usersuseridbadge-history)
  * [Endpoint 2 - /v3/tags/:tag/comments?count=:count](#endpoint-2---v3tagstagcommentscountcount)
  * [Endpoint 3 - /v3/tags/:tagname/comments/:position?limit=:limit](#endpoint-3---v3tagstagnamecommentspositionlimitlimit)
  * [Endpoint 4 - /v3/posts/:postid?limit=:limit](#endpoint-4---v3postspostidlimitlimit)
<!-- TOC -->


## Endpoint 1 - /v3/users/:userid/badge history
V subquery získam si badge data spolu s postami ktoré boli vytvorené skôr ako badge pre userid zadane na vstupe (v
tomto prípade 120). Potom v ďalšej subquery vysortujem zoznam predchádzajúcej subquery podľa creation date postu a
zoberiem si len unikátne hodnoty. Keďže v zadaní je uvedene pokiaľ jednému komentáru prislúchajú viaceré badge.
V hlavnej query beriem len prvý badge podľa creation date.

```sql
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
			WHERE users.id = 120 AND b2.date >= p2.creationdate  -- userid je parameter
		) AS bp
		ORDER BY badge_id, bp.post_date DESC  -- Toto zaruci ze zaznamy su zoradene od najnovsieho postu.
		-- To znamena ze DISTINCT na zaciatku odfiltruje vsetky stare posty
	) AS s
	ORDER BY post_date, post_id
) AS m
```


## Endpoint 2 - /v3/tags/:tag/comments?count=:count
V subquery si napojím ku komentárom post ktorému patria, usera ktorý ho vytvoril a tagy postu ktorému patri.
Následne odfiltrujem 'tagname' a počet komentárov na poste. V selecte tejto subquery pomocou 'COALESCE' pridám nový
stĺpec 'last_comment_date' ktorý obsahuje dátum komentáru ktorý bol vytvorený pred 'aktuálnym' komentárom. V
hlavnej query potom zoradím podľa 'post_created_at' a využijem 'last_comment_date' stĺpec na výpočet 'diff' a získanie
'avg' pomocou window function.

```sql
SELECT
	post_id, title, displayname, text,
	TO_CHAR(posts_created_at AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.MSOF:TZM') AS posts_created_at,
	TO_CHAR(created_at AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.MSOF:TZM') AS created_at,
	-- Kedze mam datum posledneho komentu alebo vytvorenia postu v 'last_comment_date', tak sa vypocitam cas
	-- medzi vytvorenim komentara a 'last_comment_date' ako diff. To iste aj pre average diff od prveho po
	-- "momentalny" komentar.
	TO_CHAR((created_at - last_comment_date), 'HH24:MI:SS.MS') AS diff,
	TO_CHAR(AVG((created_at - last_comment_date)) OVER (PARTITION BY post_id ORDER BY created_at), 'HH24:MI:SS.MS') AS
	avg_diff
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
	WHERE tagname = 'networking' AND p.commentcount > 40  -- Parametre
) AS m
ORDER BY posts_created_at, created_at
```

## Endpoint 3 - /v3/tags/:tagname/comments/:position?limit=:limit
V subquery si napojím dohromady komentáre, posty ktorým patria, tagy tých postov a userov ktorý vytvorili daný
komentár. Následne si odfiltrujem tag a v selecte okrem dát o komentári a userovi si vyrátam aj position komentára
v tabuľke komentárov. Ratám to pomocou window function 'ROW_NUMBER()' ktorá mi zoradí komentáre podľa idcky ale len
v rámci postu. To znamená že pre post A bude mat komentár position 1, 2, 3,... a pre post B bude mat znovu komentár
position 1, 2, 3,... Následne zoradím podľa creationdate odfiltrujem position pre každý K-ty komentár a limitujem
output.

```sql
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
	WHERE tagname = 'linux'  -- Parameter
) AS s
-- Filtrovanie kazdeho K komentara podla pozicie
WHERE position = 2  -- Parameter
ORDER BY creationdate
LIMIT 1  -- Parameter
```

## Endpoint 4 - /v3/posts/:postid?limit=:limit
Pripojím si dohromady posty a ownerov postov. Následne odfiltrujem postid alebo parentid. Tým získam thread postov
aj s údajmi ownera.

```sql
SELECT
	displayname, body,
	TO_CHAR(p.creationdate AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.MSOF:TZM') AS creationdate
FROM posts p
LEFT JOIN users u ON p.owneruserid = u.id
-- Filtrovanie podla ID a parent ID postu pre ziskanie celeho threadu daneho post id.
WHERE p.id = 2154 OR p.parentid = 2154  -- Parametre
ORDER BY p.creationdate
LIMIT 2  -- Parameter
```

