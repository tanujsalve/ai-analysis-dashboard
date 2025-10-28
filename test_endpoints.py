import requests
import json

BASE_URL = 'http://localhost:5000'

def test_register_endpoint():
    """Test the /register endpoint"""
    print("Testing /register endpoint...")

    data = {
        'email': 'test@example.com',
        'name': 'Test User'
    }

    try:
        response = requests.post(f'{BASE_URL}/register', json=data)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_process_pas_endpoint():
    """Test the modified /process-pas endpoint"""
    print("\nTesting /process-pas endpoint...")

    # Test data - simple CSV
    csv_data = "name,age,city\nJohn,25,NYC\nJane,30,LA\nBob,35,Chicago"

    try:
        response = requests.post(
            f'{BASE_URL}/process-pas?filename=test.csv',
            data=csv_data,
            headers={'Content-Type': 'text/plain'}
        )
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"Response: {result}")
            print(f"File ID: {result.get('file_id')}")
            print(f"Filename: {result.get('filename')}")
            print(f"Row Count: {result.get('row_count')}")
            print(f"Columns: {result.get('columns')}")
            return True
        else:
            print(f"Error Response: {response.text}")
            return False
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_process_pas_empty_data():
    """Test /process-pas with empty data"""
    print("\nTesting /process-pas with empty data...")

    try:
        response = requests.post(
            f'{BASE_URL}/process-pas?filename=empty.csv',
            data="",
            headers={'Content-Type': 'text/plain'}
        )
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        return response.status_code == 400
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_process_pas_invalid_csv():
    """Test /process-pas with invalid CSV"""
    print("\nTesting /process-pas with invalid CSV...")

    invalid_data = "This is not CSV data\nJust random text"

    try:
        response = requests.post(
            f'{BASE_URL}/process-pas?filename=invalid.csv',
            data=invalid_data,
            headers={'Content-Type': 'text/plain'}
        )
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"Response: {result}")
            return True
        else:
            print(f"Error Response: {response.text}")
            return False
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_load_sample():
    """Test the /load-sample endpoint"""
    print("\nTesting /load-sample endpoint...")

    try:
        response = requests.get(f'{BASE_URL}/load-sample')
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"Sample loaded: {result.get('filename')}")
            print(f"Row Count: {result.get('row_count')}")
            return True
        else:
            print(f"Error Response: {response.text}")
            return False
    except Exception as e:
        print(f"Error: {e}")
        return False

def run_all_tests():
    """Run all endpoint tests"""
    print("🚀 Starting API Endpoint Tests")
    print("=" * 50)

    tests = [
        ("Register Endpoint", test_register_endpoint),
        ("Process Paste - Valid CSV", test_process_pas_endpoint),
        ("Process Paste - Empty Data", test_process_pas_empty_data),
        ("Process Paste - Invalid CSV", test_process_pas_invalid_csv),
        ("Load Sample Data", test_load_sample),
    ]

    results = []
    for test_name, test_func in tests:
        print(f"\n📋 {test_name}")
        print("-" * 30)
        success = test_func()
        results.append((test_name, success))
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"Result: {status}")

    print("\n" + "=" * 50)
    print("📊 Test Summary:")
    passed = sum(1 for _, success in results if success)
    total = len(results)
    print(f"Passed: {passed}/{total}")

    for test_name, success in results:
        status = "✅" if success else "❌"
        print(f"  {status} {test_name}")

    return passed == total

if __name__ == '__main__':
    success = run_all_tests()
    exit(0 if success else 1)
