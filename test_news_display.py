"""
Test script to display today's high-impact news
"""
import os
import django
import sys

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fxfront.settings')
django.setup()

from django.utils import timezone
from dateutil import parser as date_parser
import requests

# FX News API URL
FX_NEWS_API_URL = 'https://fxnews-scraper-develop.up.railway.app/weekly_ecocar.json'

def get_today_high_impact_news():
    """
    Fetch high-impact news for today from FX News API.
    """
    try:
        print(f"📡 Fetching news from: {FX_NEWS_API_URL}")
        print()
        
        # Fetch news data
        response = requests.get(FX_NEWS_API_URL, timeout=5)
        response.raise_for_status()
        
        news_data = response.json()
        print(f"✅ Received {len(news_data)} total events")
        print()
        
        # Get today's date
        today = timezone.now().date()
        print(f"📅 Today's date (local): {today}")
        print()
        
        # Filter for today's high-impact news
        today_news = []
        high_impact_count = 0
        
        for event in news_data:
            if event.get('impact') == 'HIGH':
                high_impact_count += 1
                try:
                    # Parse event time
                    event_time_str = event.get('event_time_utc')
                    if event_time_str:
                        event_time = date_parser.parse(event_time_str)
                        # Convert to local timezone
                        event_time_local = timezone.localtime(event_time)
                        
                        # Check if event is today
                        if event_time_local.date() == today:
                            today_news.append({
                                'time': event_time_local.strftime('%H:%M'),
                                'currency': event.get('currency', ''),
                                'event': event.get('event', ''),
                                'time_obj': event_time_local,
                            })
                except Exception as e:
                    print(f"⚠️  Error parsing event: {e}")
                    continue
        
        print(f"🔍 Found {high_impact_count} HIGH impact events in total")
        print(f"📰 Found {len(today_news)} HIGH impact events for today")
        print()
        
        # Sort by time
        today_news.sort(key=lambda x: x['time_obj'])
        
        # Display results
        if today_news:
            print("=" * 70)
            print("TODAY'S HIGH IMPACT NEWS")
            print("=" * 70)
            for i, news in enumerate(today_news, 1):
                print(f"\n{i}. Time: {news['time']}")
                print(f"   Currency: {news['currency']}")
                print(f"   Event: {news['event']}")
                print(f"   Full datetime: {news['time_obj']}")
        else:
            print("ℹ️  No high-impact news events found for today")
            print()
            print("Sample of HIGH impact events from API:")
            print("-" * 70)
            sample_count = 0
            for event in news_data:
                if event.get('impact') == 'HIGH' and sample_count < 5:
                    event_time_str = event.get('event_time_utc')
                    event_time = date_parser.parse(event_time_str)
                    event_time_local = timezone.localtime(event_time)
                    print(f"\n  Time: {event_time_local.strftime('%Y-%m-%d %H:%M')}")
                    print(f"  Currency: {event.get('currency')}")
                    print(f"  Event: {event.get('event')}")
                    sample_count += 1
        
        print("\n" + "=" * 70)
        
        return today_news
        
    except requests.RequestException as e:
        print(f"❌ Error fetching FX news: {e}")
        return []
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return []


if __name__ == '__main__':
    print("\n🚀 Testing News Display Feature")
    print("=" * 70)
    print()
    
    news = get_today_high_impact_news()
    
    print("\n✨ Test completed!")
    print(f"📊 Total news items that would be displayed: {len(news)}")
