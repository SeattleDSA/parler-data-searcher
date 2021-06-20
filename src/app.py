#!/usr/bin/env python
from quart import Quart, render_template, request, redirect
from quart_motor import Motor
import os
from dotenv import load_dotenv

from api_types import User, Post
import api

load_dotenv()

MONGO_USER = os.environ.get("MONGO_USER")
MONGO_PASS = os.environ.get("MONGO_PASS")
MONGO_ENDPOINT = os.environ.get("MONGO_ENDPOINT")
MONGO_PORT = os.environ.get("MONGO_PORT")

app = Quart(__name__, static_folder="public", template_folder="views")

mongo = Motor(
    app, uri=f"mongodb://{MONGO_USER}:{MONGO_PASS}@{MONGO_ENDPOINT}:{MONGO_PORT}/parler"
)


################################################################################
# Home page reroute
################################################################################
ROUTE_PARAMS = {
    "search_type",
}


@app.route("/")
async def home():
    search_type = request.args.get("search_type")

    if search_type is not None:
        query_params = []
        for key, value in request.args.items():
            if key in ROUTE_PARAMS:
                continue
            query_params.append(f"{key}={value}")

        return redirect(f"/{search_type}?{'&'.join(query_params)}")

    return await render_template("index.html")


@app.route("/posts", strict_slashes=False)
async def posts():
    search_term = request.args.get("search_term", "")
    search_content = request.args.get("search_content", "")
    page = request.args.get("page", 0)
    try:
        page = int(page)
    except ValueError:
        page = 0

    if not search_term and not search_content:
        return await render_template("posts.html")

    page_count, results = await api.get_entities(
        mongo,
        "posts",
        api.get_post_query(search_term, search_content),
        page,
        Post,
    )

    return await render_template(
        "posts.html",
        posts=results,
        page=page,
        search_term=search_term,
        search_content=search_content,
        page_count=page_count,
        search_type="posts",
    )


@app.route("/users", strict_slashes=False)
async def users():
    search_term = request.args.get("search_term")
    page = request.args.get("page", 0)
    try:
        page = int(page)
    except ValueError:
        page = 0

    if not search_term:
        return await render_template("users.html")

    page_count, results = await api.get_entities(
        mongo,
        "users",
        api.get_users_query(search_term),
        page,
        User,
    )

    return await render_template(
        "users.html",
        users=results,
        page=page,
        search_term=search_term,
        page_count=page_count,
        search_type="users",
    )


if __name__ == "__main__":
    app.run()
