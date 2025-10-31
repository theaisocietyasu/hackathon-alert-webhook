#!/usr/bin/env python3
"""
Hackathon Alert Webhook Bot
Fetches hackathons from multiple sources and sends Discord notifications
"""

import json
import os
import sys
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import requests
from bs4 import BeautifulSoup
from dateutil import parser as date_parser

# Configuration
CONFIG_FILE = "config.json"
CACHE_FILE = "hackathon_cache.json"

def load_config() -> Dict:
    """Load configuration from config.json"""
    try:
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"❌ Error: {CONFIG_FILE} not found!")
        sys.exit(1)

def load_cache() -> Dict:
    """Load cache of posted hackathons"""
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, 'r') as f:
            return json.load(f)
    return {"posted": []}

def save_cache(cache: Dict):
    """Save cache to file"""
    with open(CACHE_FILE, 'w') as f:
        json.dump(cache, f, indent=2)

def fetch_hackalist_hackathons() -> List[Dict]:
    """Fetch hackathons from Hackalist API"""
    hackathons = []
    now = datetime.now()

    # Try current year and next year, for the next 6 months
    # This handles year boundaries better
    years_to_try = [now.year, now.year + 1]

    for year in years_to_try:
        for month in range(1, 13):
            target_date = datetime(year, month, 1)

            # Skip if this month is too far in the past (more than 1 month ago)
            if target_date < now - timedelta(days=30):
                continue

            # Skip if this month is too far in the future (more than 4 months)
            if target_date > now + timedelta(days=120):
                continue

            month_str = str(month).zfill(2)

            url = f"https://www.hackalist.org/api/1.0/{year}/{month_str}.json"

            try:
                response = requests.get(url, timeout=10)
                print(f"  Trying {url}: {response.status_code}")
                if response.status_code == 200:
                    data = response.json()
                    # Hackalist returns {"MonthName": [...]} structure
                    # Get all events from all month keys
                    all_events = []
                    for month_key, events in data.items():
                        if isinstance(events, list):
                            all_events.extend(events)

                    for event in all_events:
                        try:
                            # Parse dates - Hackalist format is "Month Day" + year field
                            start_str = f"{event.get('startDate', '')} {event.get('year', year)}"
                            end_str = f"{event.get('endDate', '')} {event.get('year', year)}"

                            start_date = date_parser.parse(start_str)
                            end_date = date_parser.parse(end_str)

                            # Only future hackathons
                            if end_date > now:
                                hackathons.append({
                                    "name": event.get("title", "Untitled Hackathon"),
                                    "start_date": start_date,
                                    "end_date": end_date,
                                    "location": event.get("city", "Online") if event.get("city") else "Online",
                                    "url": event.get("url", ""),
                                    "type": "In-Person" if event.get("city") else "Online",
                                    "source": "Hackalist"
                                })
                        except (ValueError, TypeError) as e:
                            print(f"⚠️  Skipping invalid Hackalist entry: {e}")
                            continue
            except Exception as e:
                print(f"⚠️  Error fetching Hackalist {year}/{month_str}: {e}")

    return hackathons

def fetch_mlh_hackathons() -> List[Dict]:
    """Fetch hackathons from MLH website"""
    hackathons = []
    url = "https://mlh.io/seasons/2025/events"

    try:
        response = requests.get(url, timeout=15)
        if response.status_code != 200:
            print(f"⚠️  MLH returned status {response.status_code}")
            return hackathons

        soup = BeautifulSoup(response.text, 'html.parser')
        now = datetime.now()

        # Find event containers
        events = soup.find_all('div', class_='event')

        for event in events:
            try:
                name_elem = event.find('h3', class_='event-name')
                date_elem = event.find('p', class_='event-date')
                location_elem = event.find('p', class_='event-location')
                link_elem = event.find('a', class_='event-link')

                if name_elem and date_elem:
                    name = name_elem.get_text(strip=True)
                    date_text = date_elem.get_text(strip=True)
                    location = location_elem.get_text(strip=True) if location_elem else "Online"
                    url_link = link_elem['href'] if link_elem and 'href' in link_elem.attrs else ""

                    # Try to parse dates from text like "Jan 15-16, 2025"
                    try:
                        start_date = date_parser.parse(date_text, fuzzy=True)
                        end_date = start_date + timedelta(days=2)  # Assume 2-day event

                        if end_date > now:
                            hackathons.append({
                                "name": name,
                                "start_date": start_date,
                                "end_date": end_date,
                                "location": location,
                                "url": url_link,
                                "type": "Hybrid" if "online" in location.lower() else "In-Person",
                                "source": "MLH"
                            })
                    except Exception as e:
                        print(f"⚠️  Could not parse MLH date '{date_text}': {e}")

            except Exception as e:
                print(f"⚠️  Error parsing MLH event: {e}")
                continue

    except Exception as e:
        print(f"⚠️  Error fetching MLH: {e}")

    return hackathons

def fetch_devpost_hackathons() -> List[Dict]:
    """Fetch hackathons from Devpost RSS feed"""
    hackathons = []
    url = "https://devpost.com/hackathons.rss"

    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=15)

        if response.status_code != 200:
            print(f"⚠️  Devpost RSS returned status {response.status_code}")
            return hackathons

        soup = BeautifulSoup(response.text, 'xml')
        now = datetime.now()

        # Parse RSS items
        items = soup.find_all('item')
        print(f"  Found {len(items)} hackathons in Devpost RSS")

        for item in items[:30]:  # Limit to first 30
            try:
                title = item.find('title')
                link = item.find('link')
                description = item.find('description')
                pub_date = item.find('pubDate')

                if title and link:
                    name = title.get_text(strip=True)
                    url_link = link.get_text(strip=True)

                    # Parse description for dates and location
                    desc_text = description.get_text() if description else ""

                    # Try to find dates in description
                    # Devpost usually includes dates in the description
                    date_found = False
                    start_date = now
                    end_date = now + timedelta(days=3)  # Default 3-day event

                    # Look for date patterns in description
                    import re
                    date_patterns = re.findall(r'([A-Z][a-z]+ \d+,? \d{4})', desc_text)
                    if date_patterns:
                        try:
                            start_date = date_parser.parse(date_patterns[0])
                            if len(date_patterns) > 1:
                                end_date = date_parser.parse(date_patterns[1])
                            else:
                                end_date = start_date + timedelta(days=2)
                            date_found = True
                        except:
                            pass

                    # If no dates in description, use pub date as reference
                    if not date_found and pub_date:
                        try:
                            pub_datetime = date_parser.parse(pub_date.get_text())
                            start_date = pub_datetime
                            end_date = pub_datetime + timedelta(days=30)  # Assume upcoming within 30 days
                        except:
                            pass

                    # Determine type from description
                    event_type = "Online"
                    if "in-person" in desc_text.lower() or "physical" in desc_text.lower():
                        event_type = "In-Person"
                    if "hybrid" in desc_text.lower():
                        event_type = "Hybrid"

                    # Extract location
                    location = "Online"
                    if event_type != "Online":
                        # Try to find location in description
                        location_match = re.search(r'(?:in|at) ([A-Z][a-z]+(?:,? [A-Z]{2})?)', desc_text)
                        if location_match:
                            location = location_match.group(1)

                    # Only include if it seems to be in the future
                    if end_date >= now:
                        hackathons.append({
                            "name": name,
                            "start_date": start_date,
                            "end_date": end_date,
                            "location": location,
                            "url": url_link,
                            "type": event_type,
                            "source": "Devpost"
                        })

            except Exception as e:
                print(f"⚠️  Error parsing Devpost RSS item: {e}")
                continue

    except Exception as e:
        print(f"⚠️  Error fetching Devpost RSS: {e}")

    return hackathons

def deduplicate_hackathons(hackathons: List[Dict]) -> List[Dict]:
    """Remove duplicate hackathons based on name similarity"""
    unique = []
    seen_names = set()

    for h in hackathons:
        # Normalize name for comparison
        name_key = h['name'].lower().strip()

        if name_key not in seen_names:
            seen_names.add(name_key)
            unique.append(h)

    return unique

def filter_by_date_range(hackathons: List[Dict], config: Dict) -> List[Dict]:
    """Filter hackathons by date range settings"""
    settings = config.get("settings", {})
    min_days = settings.get("min_days_ahead", 0)
    max_days = settings.get("max_days_ahead", 90)

    now = datetime.now()
    min_date = now + timedelta(days=min_days)
    max_date = now + timedelta(days=max_days)

    filtered = []
    for h in hackathons:
        if min_date <= h['start_date'] <= max_date:
            filtered.append(h)

    return filtered

def is_new_hackathon(hackathon: Dict, cache: Dict) -> bool:
    """Check if hackathon is new (not in cache)"""
    posted = cache.get("posted", [])
    name_key = hackathon['name'].lower().strip()

    return name_key not in posted

def send_discord_notification(hackathon: Dict, webhook_url: str) -> bool:
    """Send hackathon notification to Discord"""
    try:
        # Format dates
        start_str = hackathon['start_date'].strftime("%b %d, %Y")
        end_str = hackathon['end_date'].strftime("%b %d, %Y")
        date_range = f"{start_str} - {end_str}" if start_str != end_str else start_str

        # Determine emoji for type
        type_emoji = {
            "Online": "🌐",
            "In-Person": "📍",
            "Hybrid": "🔄"
        }.get(hackathon['type'], "🏷️")

        # Build embed
        embed = {
            "title": f"🎯 New Hackathon: {hackathon['name']}",
            "color": 10181046,  # Purple
            "fields": [
                {"name": "📅 Dates", "value": date_range, "inline": True},
                {"name": "📍 Location", "value": hackathon['location'][:100], "inline": True},
                {"name": f"{type_emoji} Type", "value": hackathon['type'], "inline": True}
            ],
            "url": hackathon['url'] if hackathon['url'] else None,
            "timestamp": datetime.utcnow().isoformat(),
            "footer": {"text": f"Source: {hackathon['source']}"}
        }

        # Remove None values
        embed = {k: v for k, v in embed.items() if v is not None}

        payload = {"embeds": [embed]}

        response = requests.post(webhook_url, json=payload, timeout=10)

        if response.status_code == 204:
            print(f"✅ Posted: {hackathon['name']}")
            return True
        else:
            print(f"❌ Failed to post {hackathon['name']}: {response.status_code}")
            return False

    except Exception as e:
        print(f"❌ Error posting {hackathon['name']}: {e}")
        return False

def main():
    """Main execution"""
    print("🚀 Starting Hackathon Alert Bot...")

    # Load config and cache
    config = load_config()
    cache = load_cache()
    webhook_url = config.get("discord_webhook_url")

    if not webhook_url:
        print("❌ Error: discord_webhook_url not set in config.json")
        sys.exit(1)

    # Fetch from all sources
    all_hackathons = []

    for source_config in config.get("sources", []):
        if not source_config.get("enabled", True):
            continue

        source_name = source_config.get("name")
        print(f"🔍 Fetching from {source_name}...")

        if source_name == "Hackalist":
            all_hackathons.extend(fetch_hackalist_hackathons())
        elif source_name == "MLH":
            all_hackathons.extend(fetch_mlh_hackathons())
        elif source_name == "Devpost":
            all_hackathons.extend(fetch_devpost_hackathons())

    print(f"📊 Found {len(all_hackathons)} total hackathons")

    # Deduplicate
    unique_hackathons = deduplicate_hackathons(all_hackathons)
    print(f"🔍 {len(unique_hackathons)} unique hackathons")

    # Filter by date range
    filtered_hackathons = filter_by_date_range(unique_hackathons, config)
    print(f"📅 {len(filtered_hackathons)} within date range")

    # Filter new ones
    new_hackathons = [h for h in filtered_hackathons if is_new_hackathon(h, cache)]
    print(f"🆕 {len(new_hackathons)} new hackathons to post")

    # Sort by start date
    new_hackathons.sort(key=lambda h: h['start_date'])

    # Post to Discord
    posted_count = 0
    for hackathon in new_hackathons:
        if send_discord_notification(hackathon, webhook_url):
            # Add to cache
            name_key = hackathon['name'].lower().strip()
            cache.setdefault("posted", []).append(name_key)
            posted_count += 1

    # Save cache
    save_cache(cache)

    print(f"✨ Done! Posted {posted_count} new hackathons")

if __name__ == "__main__":
    main()
