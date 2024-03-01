from fastapi import APIRouter

from dbs_assignment.endpoints import hello
from dbs_assignment.endpoints import posts

router = APIRouter()
router.include_router(hello.router, tags=["hello"])
router.include_router(posts.router, tags=["posts"])
