"""Celery application for RAZOR async tasks (diagnosis + explanation).

Run the worker with:  celery -A agents.celery_app worker --loglevel=info
Broker/backend point to ``config.settings.redis_url``.
"""
from __future__ import annotations

from celery import Celery

from config import settings

celery_app = Celery(
    "razor",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["agents.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_always_eager=False,
)
