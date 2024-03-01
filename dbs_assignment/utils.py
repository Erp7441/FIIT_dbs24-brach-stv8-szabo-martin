import psycopg2


def get_results_as_dict(cursor):
    return [dict(zip([desc[0] for desc in cursor.description], row)) for row in cursor.fetchall()]

def get_connection(settings):
    return psycopg2.connect(
        host=settings.DATABASE_HOST,
        database=settings.DATABASE_NAME,
        user=settings.DATABASE_USER,
        password=settings.DATABASE_PASSWORD
    )
