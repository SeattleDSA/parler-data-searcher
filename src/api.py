from quart_motor import Motor
from typing import Optional, Tuple, TypeVar
from math import floor
from pymongo.errors import OperationFailure

import logging
import asyncio

from api_types import User, Post

T = TypeVar("T", User, Post)

logger = logging.getLogger(__name__)

PAGE_LIMIT = 20


def _search_users_query(username: str) -> dict:
    search_regex = {
        "$regex": f".*{username}.*",
        "$options": "i",
    }

    return {
        "$or": [
            {
                "name": search_regex,
            },
            {
                "username": search_regex,
            },
        ],
    }


def _search_posts_query(username: str, search_content: str) -> Optional[dict]:
    username_query = {}
    if username:
        formatted_username = username if username.startswith("@") else f"@{username}"
        username_query = {
            "$or": [
                {
                    "username": formatted_username,
                },
                {
                    "comments.username": formatted_username,
                },
                {
                    "echo.username": formatted_username,
                },
            ],
        }

    content_query = {}
    if search_content:
        content_regex = {
            "$regex": f".*{search_content}.*",
            "$options": "i",
        }
        content_query = {
            "$or": [
                {
                    "text": content_regex,
                },
                {
                    "media.title": content_regex,
                },
                {
                    "comment.text": content_regex,
                },
                {
                    "echo.text": content_regex,
                },
            ],
        }

    # avoid an empty $or clause which will cause an error
    if not username_query and not content_query:
        return None

    if username_query and not content_query:
        return username_query

    if content_query and not username_query:
        return content_query

    return {"$and": [username_query, content_query]}


async def _get_entities(
    mongo: Motor,
    collection: str,
    query: Optional[dict],
    page: int,
) -> Tuple[int, list[T]]:
    if query is None:
        return 0, []

    skip = page * PAGE_LIMIT

    try:
        total_count_f = mongo.db[collection].count_documents(query)
        results_f = (
            mongo.db[collection]
            .find(query)
            .skip(skip)
            .limit(PAGE_LIMIT)
            .to_list(length=PAGE_LIMIT)
        )
        await asyncio.wait(
            {total_count_f, results_f}, return_when=asyncio.FIRST_EXCEPTION
        )
        # indiscriminantly await each future, if one failed then the exception will raise as expected
        total_count: int = await total_count_f
        results: list[T] = await results_f
    except OperationFailure as err:
        logger.error(f"Failure retrieving {collection}: {err}")

        # probably an invalid regex, just return nothing
        total_count = 0
        results = []

    page_count = floor(total_count / PAGE_LIMIT) + 1

    return page_count, results


async def search_users(
    mongo: Motor, username: str, page: int
) -> Tuple[int, list[User]]:
    return await _get_entities(mongo, "users", _search_users_query(username), page)


async def search_posts(
    mongo: Motor, username: str, content: str, page: int
) -> Tuple[int, list[Post]]:
    return await _get_entities(
        mongo, "posts", _search_posts_query(username, content), page
    )
