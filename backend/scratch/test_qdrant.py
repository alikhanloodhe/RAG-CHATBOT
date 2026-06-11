import os
from qdrant_client import QdrantClient
from dotenv import load_dotenv

# Load env from .env file
load_dotenv()

def test_url(url, api_key):
    print(f"\nTesting: {url}")
    try:
        client = QdrantClient(
            url=url,
            api_key=api_key,
            timeout=5.0
        )
        collections = client.get_collections()
        print("SUCCESS: Connected to Qdrant Cloud!")
        print(f"Collections: {collections}")
        return True
    except Exception as e:
        print(f"FAILED: {e}")
        return False

def main():
    # Parse env directly
    url = None
    api_key = None
    with open(".env", "r") as f:
        for line in f:
            if "QDRANT_URL" in line:
                url = line.split("=", 1)[1].strip()
            elif "QDRANT_API_KEY" in line:
                api_key = line.split("=", 1)[1].strip()

    # Test original URL
    test_url(url, api_key)

    # Test URL without port (default HTTPS port 443)
    if ":" in url.replace("https://", ""):
        clean_url = url.split(":6333")[0]
        test_url(clean_url, api_key)

if __name__ == "__main__":
    main()
