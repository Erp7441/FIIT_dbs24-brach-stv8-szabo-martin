import psycopg2
from fastapi import APIRouter

from dbs_assignment.config import settings

router = APIRouter()
# conn = psycopg2.connect()

@router.get("/v1/hello")
async def hello():
    return {
        'hello': settings.NAME
    }

@router.get("/v1/test")
async def test():
    return {
        'test': settings.NAME
    }
