from fastapi import APIRouter

from dbs_assignment.endpoints import hello, posts, users, tags


router = APIRouter()
router.include_router(hello.router, tags=["hello"])
router.include_router(posts.router, tags=["posts"])
router.include_router(users.router, tags=["users"])
router.include_router(tags.router, tags=["tags"])
