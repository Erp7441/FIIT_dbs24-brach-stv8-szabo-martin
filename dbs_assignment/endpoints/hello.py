import psycopg2
from fastapi import APIRouter

from dbs_assignment.config import settings

router = APIRouter()
connection = psycopg2.connect(
    host=settings.DATABASE_HOST,
    database=settings.DATABASE_NAME,
    user=settings.DATABASE_USER,
    password=settings.DATABASE_PASSWORD
)

@router.get("/v1/hello")
async def hello():
    return {
        'hello': settings.NAME
    }

@router.get("/v1/status")
async def status():
    cursor = connection.cursor()
    cursor.execute("SELECT version();")
    results = cursor.fetchone()
    return {
        'version': results[0]
    }
