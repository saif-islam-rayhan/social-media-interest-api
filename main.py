# main.py

from fastapi import FastAPI
from pymongo import MongoClient
import pandas as pd
from transformers import pipeline
from threading import Timer


# 1. Load pretrained model

classifier = pipeline(
    "zero-shot-classification",
    model="facebook/bart-large-mnli"
)

# Topics you want to detect
candidate_labels = ["Cricket", "Football", "government", "politics", "Love", "Friendship", "Technology", "Business", "Entertainment", "News"]


# 2. MongoDB connection

client = MongoClient("mongodb+srv://db_user:WcoEqUnPZTKwACY8@cluster0.5iz2xl.mongodb.net/?appName=Cluster0")
db = client["social_media"]
collection = db["posts"]


# 3. Storage for user interests

user_interests = {}  # {userId: {topic: score}}

# 4. Function: detect topic

def detect_topic(text: str):
    if not text or text.strip() == "":
        return "Unknown"
    result = classifier(text, candidate_labels)
    return result["labels"][0]

# 5. Function: update interests from database

def update_interests():
    global user_interests
    posts = list(collection.find({}))
    interests = {}  # temporary dictionary

    for post in posts:
        user = str(post.get("userId"))
        content = post.get("content", "")
        likes = post.get("likes", [])
        comments = post.get("comments", [])

        topic = detect_topic(content)

        # own post
        if user not in interests:
            interests[user] = {}
        if topic not in interests[user]:
            interests[user][topic] = 0
        interests[user][topic] += 1

        # likes
        for like in likes:
            lid = str(like.get("userId"))
            if lid not in interests:
                interests[lid] = {}
            if topic not in interests[lid]:
                interests[lid][topic] = 0
            interests[lid][topic] += 1

        # comments
        for comment in comments:
            cid = str(comment.get("userId"))
            if cid not in interests:
                interests[cid] = {}
            if topic not in interests[cid]:
                interests[cid][topic] = 0
            interests[cid][topic] += 2

    user_interests = interests
    # Schedule next update (every 30 seconds)
    Timer(30, update_interests).start()


# 6. Start periodic update
update_interests()

# 7. FastAPI
app = FastAPI()

@app.get("/")
def home():
    return {"message": "User Interest Service Running"}

@app.get("/interests")
def get_all_interests():
    return user_interests

@app.get("/interests/{user_id}")
def get_user_interest(user_id: str):
    return user_interests.get(user_id, {})
