import requests
import pandas as pd
import base64
from io import BytesIO
import matplotlib.pyplot as plt
import requests
from dagster import (
    AssetKey,
    DagsterInstance,
    MetadataValue,
    Output,
    asset,
    get_dagster_logger,
)


@asset(
    group_name="hackernews",
)
def topstory_ids():
    logger = get_dagster_logger()
    newstories_url = "https://hacker-news.firebaseio.com/v0/topstories.json"
    top_new_story_ids = requests.get(newstories_url).json()[:100]
    logger.info(top_new_story_ids)
    return top_new_story_ids


@asset(
    group_name="hackernews",
    io_manager_key="database_io_manager",
)
def topstories(topstory_ids):
    logger = get_dagster_logger()

    results = []
    for item_id in topstory_ids:
        item = requests.get(
            f"https://hacker-news.firebaseio.com/v0/item/{item_id}.json"
        ).json()
        results.append(item)

        if len(results) % 20 == 0:
            logger.info(f"Got {len(results)} items so far.")

    df = pd.DataFrame(results)

    return Output(
        value=df,
        metadata={
            "num_records": len(df),
            "preview": MetadataValue.md(df.head().to_markdown())
        },
    )


@asset(
    group_name="hackernews",
)
def most_frequent_words(topstories):
    stopwords = ["a", "the", "an", "of", "to", "in", "for", "and", "with", "on", "is"]

    # loop through the titles and count the frequency of each word
    word_counts = {}
    for raw_title in topstories["title"]:
        title = raw_title.lower()
        for word in title.split():
            cleaned_word = word.strip(".,-!?:;()[]'\"-")
            if cleaned_word not in stopwords and len(cleaned_word) > 0:
                word_counts[cleaned_word] = word_counts.get(cleaned_word, 0) + 1

    # Get the top 25 most frequent words
    top_words = {
        pair[0]: pair[1]
        for pair in sorted(word_counts.items(), key=lambda x: x[1], reverse=True)[:25]
    }

    # Make a bar chart of the top 25 words
    plt.figure(figsize=(10, 6))
    plt.bar(top_words.keys(), top_words.values())
    plt.xticks(rotation=45, ha="right")
    plt.title("Top 25 Words in Hacker News Titles")
    plt.tight_layout()

    # Convert the image to a saveable format
    buffer = BytesIO()
    plt.savefig(buffer, format="png")
    image_data = base64.b64encode(buffer.getvalue())

    # Convert the image to Markdown to preview it within Dagster
    md_content = f"![img](data:image/png;base64,{image_data.decode()})"

    # Attach the Markdown content as metadata to the asset
    return Output(
        value=top_words,
        metadata={"plot": MetadataValue.md(md_content)},
    )

    
@asset(
    group_name="hello",
)
def hello(context):
    context.log.info("Hello, World!")
