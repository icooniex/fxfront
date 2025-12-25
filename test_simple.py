#!/usr/bin/env python
"""
Simple Test Script - ทดสอบ Celery แบบง่ายๆ

ทดสอบทีละ function เพื่อให้เข้าใจว่า Celery ทำงานยังไง

Run:
    python test_simple.py
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fxfront.settings')
django.setup()


def test_1_hello_world():
    """Test 1: Task ง่ายสุด - Hello World"""
    print("\n" + "="*50)
    print("TEST 1: Hello World Task")
    print("="*50)
    
    from trading.tasks_simple import hello_world
    
    print("📤 Sending task to Celery...")
    result = hello_world.delay()
    
    print(f"✅ Task submitted! ID: {result.id}")
    print("⏳ Waiting for result...")
    
    try:
        output = result.get(timeout=10)
        print(f"✅ SUCCESS!")
        print(f"   Message: {output['message']}")
        print(f"   Time: {output['timestamp']}")
        return True
    except Exception as e:
        print(f"❌ FAILED: {e}")
        print("   💡 Make sure Celery worker is running:")
        print("   celery -A fxfront worker --loglevel=info")
        return False


def test_2_add_numbers():
    """Test 2: Task ที่รับ parameters"""
    print("\n" + "="*50)
    print("TEST 2: Add Numbers Task")
    print("="*50)
    
    from trading.tasks_simple import add_numbers
    
    x, y = 10, 25
    print(f"📤 Calculating {x} + {y}...")
    
    result = add_numbers.delay(x, y)
    
    try:
        output = result.get(timeout=10)
        print(f"✅ SUCCESS!")
        print(f"   {output['message']}")
        return True
    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False


def test_3_redis():
    """Test 3: Celery + Redis"""
    print("\n" + "="*50)
    print("TEST 3: Redis Connection")
    print("="*50)
    
    from trading.tasks_simple import test_redis_connection
    
    print("📤 Testing Redis connection...")
    result = test_redis_connection.delay()
    
    try:
        output = result.get(timeout=10)
        print(f"Status: {output['status']}")
        print(f"Message: {output['message']}")
        
        if output['status'] == 'success':
            print("✅ SUCCESS!")
            return True
        else:
            print("❌ FAILED!")
            return False
    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False


def test_4_database():
    """Test 4: Celery + Database"""
    print("\n" + "="*50)
    print("TEST 4: Database Access")
    print("="*50)
    
    from trading.tasks_simple import test_database_access
    
    print("📤 Testing database access...")
    result = test_database_access.delay()
    
    try:
        output = result.get(timeout=10)
        print(f"Status: {output['status']}")
        print(f"Message: {output['message']}")
        
        if output['status'] == 'success':
            print("✅ SUCCESS!")
            return True
        else:
            print("❌ FAILED!")
            return False
    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False


def test_5_async():
    """Test 5: Async Execution"""
    print("\n" + "="*50)
    print("TEST 5: Async Execution (Slow Task)")
    print("="*50)
    
    from trading.tasks_simple import slow_task
    
    print("📤 Starting 5-second task...")
    print("   (Task will run in background)")
    
    result = slow_task.delay(5)
    
    print(f"✅ Task submitted! ID: {result.id}")
    print("💡 You can do other things while waiting...")
    print("⏳ Now waiting for result...")
    
    try:
        output = result.get(timeout=15)
        print(f"✅ SUCCESS!")
        print(f"   {output['message']}")
        return True
    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False


def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("🧪 SIMPLE CELERY TEST SUITE")
    print("="*60)
    print("\n📋 Prerequisites:")
    print("   1. Redis is running")
    print("   2. Celery worker is running:")
    print("      celery -A fxfront worker --loglevel=info")
    print("\n" + "="*60)
    
    input("\nPress ENTER to start tests...")
    
    results = {}
    
    # Run tests
    results["Hello World"] = test_1_hello_world()
    
    if results["Hello World"]:
        results["Add Numbers"] = test_2_add_numbers()
        results["Redis"] = test_3_redis()
        results["Database"] = test_4_database()
        results["Async"] = test_5_async()
    else:
        print("\n⚠️ Skipping other tests - Worker not running")
        return False
    
    # Summary
    print("\n" + "="*60)
    print("📊 TEST SUMMARY")
    print("="*60)
    
    for test_name, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test_name:.<30} {status}")
    
    passed_count = sum(results.values())
    total_count = len(results)
    
    print(f"\n{'Total:':<30} {passed_count}/{total_count} passed")
    
    if passed_count == total_count:
        print("\n🎉 All tests passed! Celery is working correctly!")
        print("\n📚 Next steps:")
        print("   1. Deploy to Railway")
        print("   2. Test on production")
        print("   3. Move to complex tasks (trade processing)")
    else:
        print("\n⚠️ Some tests failed. Check the errors above.")
    
    return passed_count == total_count


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
