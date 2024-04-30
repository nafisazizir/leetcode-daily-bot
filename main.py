import requests
from markdownify import markdownify as md
import discord
from datetime import datetime
import os
from dotenv import load_dotenv

BASE_URL = "https://leetcode.com"


def get_csrf_token(session):
    response = session.get(f"{BASE_URL}/graphql")
    return response.cookies.get("csrftoken")


def get_daily_metadata(session, csrf_token):
    query = """
            query leetcodeDaily {
                activeDailyCodingChallengeQuestion {
                    date
                    link
                    question {
                        difficulty
                        questionId
                        title
                        titleSlug
                    }
                }
            }
            """
    payload = {"query": query}

    session.headers["Referer"] = BASE_URL
    session.headers["X-CSRFToken"] = csrf_token
    response = session.post(f"{BASE_URL}/graphql", data=payload)
    response = response.json()
    response_data = response["data"]["activeDailyCodingChallengeQuestion"]

    return {
        "date": response_data["date"],
        "link": response_data["link"],
        "difficulty": response_data["question"]["difficulty"],
        "id": response_data["question"]["questionId"],
        "title": response_data["question"]["title"],
        "title_slug": response_data["question"]["titleSlug"],
    }


def get_daily_question_details(session, csrf_token, title_slug):
    query = """
            query questionContent($titleSlug: String!) {
                question(titleSlug: $titleSlug) {
                    content
                }
            }
            """
    variables = {"titleSlug": title_slug}
    payload = {"query": query, "variables": variables}

    session.headers["Referer"] = BASE_URL
    session.headers["X-CSRFToken"] = csrf_token
    response = session.post(f"{BASE_URL}/graphql", json=payload)
    response = response.json()

    return response["data"]["question"]["content"]


def convert_html_to_markdown(html, link):
    markdown = md(html)
    final_md = [f"[Question link]({BASE_URL}{link})", ""]

    for line in markdown.split("\n"):
        if line.strip() == "" and final_md[-1] == "":
            continue
        final_md.append(line.strip())

    return "\n".join(final_md)


intents = discord.Intents.default()
client = discord.Client(intents=intents)

load_dotenv()
CHANNEL_ID = int(os.environ.get("CHANNEL_ID"))
BOT_TOKEN = os.environ.get("BOT_TOKEN")


async def create_thread():
    print(f"Logged in as {client.user.name}")
    print(f"Bot ID: {client.user.id}")

    channel = client.get_channel(CHANNEL_ID)
    if channel:
        tag_map = {}
        for tag in channel.available_tags:
            tag_map[tag.name] = tag

        session = requests.Session()
        csrf_token = get_csrf_token(session)
        daily_metadata = get_daily_metadata(session, csrf_token)
        question_details_html = get_daily_question_details(
            session, csrf_token, daily_metadata["title_slug"]
        )

        date_obj = datetime.strptime(daily_metadata["date"], "%Y-%m-%d")
        date = date_obj.strftime("%B %d %Y")
        id = daily_metadata["id"]
        question_title = daily_metadata["title"]
        title = f"{date} - {id}. {question_title}"

        question_details_md = convert_html_to_markdown(
            question_details_html, daily_metadata["link"]
        )

        await channel.create_thread(
            name=title,
            content=question_details_md,
            applied_tags=[tag_map[daily_metadata["difficulty"]]],
        )
        await client.close()

    else:
        print("Error: Channel not found")


@client.event
async def on_ready():
    await create_thread()


client.run(BOT_TOKEN)
