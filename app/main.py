import logging
import pathlib
import sys
from contextlib import asynccontextmanager

import redis.asyncio as aioredis
import uvicorn
from aiokafka.producer import AIOKafkaProducer
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator
from sqlalchemy.ext.asyncio import AsyncSession

from app import schemas, settings
from db import models
from db.main import get_db, sessionmanager
from kafka.main import get_kafka_producer

project_dir = pathlib.Path(__file__).resolve().parents[1]
sys.path.append(str(project_dir))
project_dir = pathlib.Path(__file__).resolve().parents[0]
sys.path.append(str(project_dir))
project_dir = pathlib.Path(__file__).resolve().parents[2]
sys.path.append(str(project_dir))

redis = aioredis.from_url(
    settings.REDIS_URL,
    encoding="utf-8",
    decode_responses=True,
)

sessionmanager.init(settings.POSTGRES_URL)


@asynccontextmanager
async def lifespan(fastapi_app: FastAPI):  # pylint: disable=W0613
    yield
    if sessionmanager._engine is not None:  # pylint: disable=W0212
        await sessionmanager.close()


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
)
Instrumentator().instrument(app).expose(app)


class EndpointFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return record.getMessage().find("/metrics") == -1


# Filter out /metrics
logging.getLogger("uvicorn.access").addFilter(EndpointFilter())


@app.middleware("http")
async def rate_limiter_middleware(
    request: Request,
    call_next,
):
    if request.method != "OPTIONS":
        ip_address = (
            request.headers.get("X-Real-IP") or request.client.host
        )

        current_time_tuple = await redis.execute_command("TIME")
        current_time = float(
            f"{current_time_tuple[0]}.{current_time_tuple[1]}"
        )

        last_request_time = await redis.get(ip_address)

        if (
            last_request_time is not None
            and current_time - float(last_request_time) < 1
        ):
            return JSONResponse(
                content={"detail": "Too many requests"}, status_code=429
            )

        await redis.set(ip_address, str(current_time), ex=2)

    response = await call_next(request)
    return response


@app.post("/api/submit-form")
async def send_message(
    form: schemas.FormSend,
    request: Request,
    producer: AIOKafkaProducer = Depends(get_kafka_producer),
    db: AsyncSession = Depends(get_db),
):
    ip_address = request.headers.get("X-Real-IP") or request.client.host

    if user_in_db := await models.Client.get_by_phone(db, form.phone):
        await user_in_db.increment_submission_amount(db)
        await user_in_db.add_ip_address(db, ip_address)
        raise HTTPException(status_code=400, detail="User already exists")

    new_client = await models.Client.create(
        db, submission_amount=1, **form.model_dump()
    )
    await new_client.add_ip_address(db, ip_address)
    try:
        await producer.send(
            "telegram-newclient-notify", value=form.model_dump()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


# @app.get("/api/request")
# async def get_request(request: Request):
#     return JSONResponse(
#         content={
#         "client": request.client,
#         "headers": request.headers.items()
#         }
#     )


@app.get("/healthz")
async def healthz():
    return JSONResponse(status_code=200, content={"health": "ok"})


# @app.get("/api/db")
# async def get_all_users(key: str, db: AsyncSession = Depends(get_db), ):
#     secret_key, timestamp = (str(base64.b64decode(key).decode('utf-8'))
#                              .replace('\n', '')
#                              .split(':'))
#     if not secret_key or not timestamp:
#         raise HTTPException(status_code=400, detail="Invalid secret key")
#     if secret_key != settings.SECRET_KEY:
#         raise HTTPException(status_code=400, detail="Invalid secret key")
#     if float(timestamp) < time.time():
#         raise HTTPException(status_code=400, detail="Invalid secret key")
#
#     return await models.Client.get_all(db)


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.LISTEN_ADDR,
        port=settings.LISTEN_PORT,
        reload=settings.DEBUG,
        log_level=0,
        use_colors=True,
    )
