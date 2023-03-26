#!/usr/bin/env python3

import tweepy
import csv
import argparse
import re
from notion_client import Client
from datetime import datetime
import os


def fetch_filtered_tweets(api, user_id, keyword=None):
    filtered_tweets = []

    if keyword:
        print(f"Fetching tweets from {user_id} containing '{keyword}'...")
    else:
        print(f"Fetching all tweets from {user_id}...")

    for status in tweepy.Cursor(api.user_timeline, screen_name=user_id, tweet_mode="extended").items():
        if not keyword or keyword.lower() in status.full_text.lower():
            prompt_text = re.search(r'(?i)prompt:\s*(.*)', status.full_text)
            if prompt_text:
                status.filtered_text = prompt_text.group(1)
            else:
                status.filtered_text = ""
            filtered_tweets.append(status)

    print(f"Found {len(filtered_tweets)} tweets.")
    return filtered_tweets

def save_to_notion(tweets, database_id, notion_api_key):
    print(f"Saving tweets to Notion database...")

    notion = Client(auth=notion_api_key)

    for tweet in tweets:
        existing_record = find_existing_record(notion, database_id, tweet.id_str)

        if existing_record:
            print(f"Tweet with ID {tweet.id_str} already exists in Notion database. Skipping.")
            continue

        new_page = {
            "ID": {"title": [{"text": {"content": f"{tweet.id_str}"}}]},
            "Date": {"date": {"start": f"{tweet.created_at.isoformat()}"}},
            "Original Text": {"rich_text": [{"text": {"content": f"{tweet.full_text}"}}]},
            "Filtered Text": {"rich_text": [{"text": {"content": f"{tweet.filtered_text}"}}]},
        }
        notion.pages.create(parent={"type": "database_id", "database_id": database_id}, properties=new_page)

    print(f"Tweets saved to Notion database.")

def find_existing_record(notion, database_id, tweet_id):
    existing_records = notion.databases.query(
        **{
            "database_id": database_id,
            "filter": {
                "property": "ID",
                "title": {
                    "equals": tweet_id
                }
            }
        }
    ).get("results")

    return existing_records[0] if existing_records else None

def save_to_csv(tweets, filename):
    print(f"Saving tweets to {filename}...")
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["id", "created_at", "original_text", "filtered_text"])
        for tweet in tweets:
            writer.writerow([tweet.id_str, tweet.created_at, tweet.full_text, tweet.filtered_text])
    print(f"Tweets saved to {filename}.")

def main(api, user_id, keyword=None, notion_api_key=None, database_id=None):
    filtered_tweets = fetch_filtered_tweets(api, user_id, keyword)

    if notion_api_key and database_id:
        save_to_notion(filtered_tweets, database_id, notion_api_key)

    # save_to_csv(filtered_tweets, f"{user_id}_filtered_tweets.csv")

if __name__ == "__main__":
    # Retrieve API keys and credentials from environment variables
    consumer_key = os.environ.get("TWITTER_CONSUMER_KEY")
    consumer_secret = os.environ.get("TWITTER_CONSUMER_SECRET")
    access_token = os.environ.get("TWITTER_ACCESS_TOKEN")
    access_token_secret = os.environ.get("TWITTER_ACCESS_TOKEN_SECRET")
    notion_api_key = os.environ.get("NOTION_API_KEY")
    database_id = "97cc22e911a34e439598792fd37dea63"

    # Set up argument parsing
    parser = argparse.ArgumentParser(description="Fetch filtered tweets from a specific Twitter user and save them to a Notion database")
    parser.add_argument("user_id", help="Twitter user_id")
    parser.add_argument("keyword", nargs="?", default=None, help="Keyword to filter tweets (optional)")

    # Parse arguments
    args = parser.parse_args()

    # Authenticate with the Twitter API
    auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
    auth.set_access_token(access_token, access_token_secret)
    api = tweepy.API(auth)

    # Call the main function with the specified user_id, keyword, and Notion details
    main(api, user_id=args.user_id, keyword=args.keyword, notion_api_key=notion_api_key, database_id=database_id)
