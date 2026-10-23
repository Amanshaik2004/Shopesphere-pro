from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.db.session import SessionLocal
from app.db.init_db import init_db
from app.core.logging import logger

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("ShopSphere Pro starting up...")
    db = SessionLocal()
    try:
        init_db(db)
    finally:
        db.close()
    yield
    logger.info("ShopSphere Pro shutting down...")
