import psycopg2

def get_results_as_kev_val_pair(cursor):
    results = cursor.fetchall()
    return {result[0]: result[1] for result in results}

def get_results_as_dict(cursor):
    results = cursor.fetchall()
    return [dict(zip([desc[0] for desc in cursor.description], row)) for row in results]

def get_connection(settings):
    return psycopg2.connect(
        host=settings.DATABASE_HOST,
        database=settings.DATABASE_NAME,
        user=settings.DATABASE_USER,
        password=settings.DATABASE_PASSWORD
    )
