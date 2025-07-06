#!/usr/bin/env python3
"""
Demo script to showcase the Database Health Check Application features
"""

import requests
import json
import time
import sys

BASE_URL = "http://localhost:8080"

def test_api_endpoint(endpoint, method="GET", data=None):
    """Test an API endpoint and display results"""
    try:
        if method == "GET":
            response = requests.get(f"{BASE_URL}{endpoint}")
        elif method == "POST":
            response = requests.post(f"{BASE_URL}{endpoint}", json=data)
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"❌ Error {response.status_code}: {response.text}")
            return None
    except requests.exceptions.ConnectionError:
        print(f"❌ Cannot connect to {BASE_URL}. Make sure the application is running.")
        return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def main():
    print("🏥 Database Health Check Application Demo")
    print("=" * 50)
    
    # Test current health
    print("\n1. 🔍 Testing Current Health Status...")
    health = test_api_endpoint("/api/health/current")
    if health:
        status_emoji = "✅" if health['status'] == 'healthy' else "⚠️" if health['status'] == 'warning' else "❌"
        print(f"   Status: {status_emoji} {health['status'].upper()}")
        print(f"   Response Time: {health['response_time']:.3f}s")
        print(f"   CPU Usage: {health['cpu_usage']:.1f}%")
        print(f"   Memory Usage: {health['memory_usage']:.1f}%")
    
    # Test monitoring status
    print("\n2. ⚙️ Checking Monitoring Status...")
    monitoring = test_api_endpoint("/api/monitoring/status")
    if monitoring:
        status_emoji = "🟢" if monitoring['is_monitoring'] else "🔴"
        print(f"   Monitoring: {status_emoji} {'ACTIVE' if monitoring['is_monitoring'] else 'STOPPED'}")
    
    # Test custom query
    print("\n3. 🛠️ Running Custom Query...")
    query_data = {
        "name": "Demo Query - Count Records",
        "query": "SELECT COUNT(*) as total_records FROM sample_data"
    }
    query_result = test_api_endpoint("/api/queries/run", "POST", query_data)
    if query_result:
        status_emoji = "✅" if query_result['status'] == 'success' else "⚠️" if query_result['status'] == 'warning' else "❌"
        print(f"   Query Status: {status_emoji} {query_result['status'].upper()}")
        print(f"   Execution Time: {query_result['execution_time']:.3f}s")
        print(f"   Rows Affected: {query_result['rows_affected']}")
    
    # Test health history
    print("\n4. 📊 Getting Health History...")
    history = test_api_endpoint("/api/health/history?hours=1")
    if history:
        print(f"   Found {len(history)} health checks in the last hour")
        if history:
            latest = history[0]
            print(f"   Latest check: {latest['status']} at {latest['timestamp']}")
    
    # Test query history
    print("\n5. 🔍 Getting Query History...")
    query_history = test_api_endpoint("/api/queries/history?hours=1")
    if query_history:
        print(f"   Found {len(query_history)} query checks in the last hour")
        if query_history:
            latest_query = query_history[0]
            print(f"   Latest query: {latest_query['query_name']} ({latest_query['execution_time']:.3f}s)")
    
    # Generate report
    print("\n6. 📋 Generating Health Report...")
    report = test_api_endpoint("/api/report?hours=1")
    if report:
        health_summary = report['health_summary']
        query_summary = report['query_summary']
        print(f"   Report Period: {report['period_hours']} hours")
        print(f"   Total Health Checks: {health_summary['total_checks']}")
        print(f"   Average Response Time: {health_summary['avg_response_time']:.3f}s")
        print(f"   Total Query Checks: {query_summary['total_queries']}")
        print(f"   Average Query Time: {query_summary['avg_execution_time']:.3f}s")
    
    print("\n✅ Demo completed successfully!")
    print(f"\n🌐 Access the web dashboard at: {BASE_URL}")
    print("\n📚 Available features:")
    print("   • Real-time health monitoring")
    print("   • Interactive charts and graphs")
    print("   • Custom query execution")
    print("   • Comprehensive reporting")
    print("   • Historical data analysis")

if __name__ == "__main__":
    main()