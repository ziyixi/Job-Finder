import os
import sqlite3
from datetime import datetime

from loguru import logger
from notion_client import Client
from notion_client.helpers import iterate_paginated_api

from job_finder.settings import SQLITE_DB_PATH


def construct_properties(title, id, company, location, url, created_at):
    properties = {
        "Title": {
            "title": [
                {
                    "text": {
                        "content": title
                    }
                }
            ]
        },
        "Id": {
            "rich_text": [
                {
                    "text": {
                        "content": id
                    }
                }
            ]
        },
        "Company": {
            "rich_text": [
                {
                    "text": {
                        "content": company
                    }
                }
            ]
        },
        "Location": {
            "rich_text": [
                {
                    "text": {
                        "content": location
                    }
                }
            ]
        },
        "URL": {
            "url": url
        },
        "Created At": {
            "date": {
                "start": created_at
            }
        }
    }
    return properties


def construct_children(description):
    children = [
        {
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [
                    {
                        "text": {
                            "content": description[:2000]
                        }
                    }
                ]
            }
        }
    ]
    return children


def get_all_new_jobs_today():
    # references new jobs table:
    # CREATE TABLE NEW_JOBS  (
    #   id TEXT,
    #   title TEXT,
    #   company TEXT,
    #   location TEXT,
    #   description TEXT,
    #   url TEXT,
    #   date DATE,
    #   created_at DATE,
    #   PRIMARY KEY(id,company)
    # )
    conn = sqlite3.connect(SQLITE_DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
    --beginsql
    SELECT * FROM NEW_JOBS WHERE created_at >= ?
    --endsql
    """, (str(datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)),))

    rows = cursor.fetchall()
    conn.close()
    return rows


def get_id_and_company_from_notion(notion, page_id):
    # only query today's results
    id_and_company = []
    for rows in iterate_paginated_api(notion.databases.query, **{
        "database_id": page_id,
        "filter": {
            "property": "Created At",
            "date": {
                "on_or_after": str(datetime.now().replace(hour=0, minute=0, second=0, microsecond=0))
            }
        }
    }):
        if rows:
            for row in rows:
                id_and_company.append((row["properties"]["Id"]["rich_text"][0]["plain_text"],
                                      row["properties"]["Company"]["rich_text"][0]["plain_text"],))
    return id_and_company


def filter_jobs(new_job_rows, id_and_company_from_notion):
    # filter out jobs that are already in notion (primary key is id and company)
    id_and_company_from_notion = set(id_and_company_from_notion)
    filtered_jobs = []
    for row in new_job_rows:
        if (row[0], row[2]) not in id_and_company_from_notion:
            filtered_jobs.append(row)
    return filtered_jobs


if __name__ == "__main__":
    notion = Client(auth=os.getenv("NOTION_TOKEN"))
    page_id = os.getenv("NOTION_PAGE_ID")
    id_and_company_from_notion = get_id_and_company_from_notion(
        notion, page_id)
    new_job_rows = get_all_new_jobs_today()
    filtered_jobs = filter_jobs(new_job_rows, id_and_company_from_notion)
    for i, job in enumerate(filtered_jobs):
        logger.info(
            f"Creating page {i+1} of {len(filtered_jobs)}, with id {job[0]} and company {job[2]}")
        notion.pages.create(**{
            "parent": {
                "database_id": page_id
            },
            "properties": construct_properties(
                title=job[1],
                id=job[0],
                company=job[2],
                location=job[3],
                url=job[5],
                created_at=job[7].split(" ")[0]
            ),
            "children": construct_children(job[4])
        })
