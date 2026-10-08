import os
import requests
from google.transit import gtfs_realtime_pb2
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.environ["NTA_API_KEY"]
URL = "https://api.nationaltransport.ie/gtfsr/v2/gtfsr"

response = requests.get(URL, headers={"x-api-key": API_KEY})
response.raise_for_status()

feed = gtfs_realtime_pb2.FeedMessage()
feed.ParseFromString(response.content)

print(f"Feed timestamp: {feed.header.timestamp}")
print(f"Total entities: {len(feed.entity)}")
print("---")

# Print the first entity in full
seen = set()
for entity in feed.entity:
    seen.add(entity.trip_update.trip.route_id)
    if len(seen) >= 20:
        break
print(seen)