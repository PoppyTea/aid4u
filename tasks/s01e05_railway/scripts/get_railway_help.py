import json
import time

import httpx


def main():
    url = "https://hub.ag3nts.org/verify"
    apikey = "7a6dcc7c-07a0-4dce-93f8-f81d68ca0f53"
    payload = {
        "apikey": apikey,
        "task": "railway",
        "answer": {
            "action": "help"
        }
    }

    print("Querying railway API for help...")

    # Simple retry loop for 503 errors and rate limits
    for attempt in range(10):
        try:
            response = httpx.post(url, json=payload, timeout=20.0)

            # Print headers for rate limit info
            print(f"Status Code: {response.status_code}")
            print(f"Headers: {dict(response.headers)}")

            if response.status_code == 503:
                print("Got 503, retrying in 5 seconds...")
                time.sleep(5)
                continue

            if response.status_code == 429:
                print("Got 429 Rate Limit. Checking retry headers...")
                retry_after = response.headers.get("retry-after", "5")
                try:
                    sleep_time = int(retry_after)
                except ValueError:
                    sleep_time = 5
                print(f"Waiting {sleep_time} seconds before retry...")
                time.sleep(sleep_time)
                continue

            response.raise_for_status()
            data = response.json()

            with open("/home/lis/projekty/10_izolowane_projekty/00_aid4u/aid4u/strategy/s01e05_api_help.md", "w") as f:
                f.write("# Railway API Help Documentation\n\n")
                f.write("```json\n")
                f.write(json.dumps(data, indent=2, ensure_ascii=False))
                f.write("\n```\n")

            print("Successfully saved API documentation to strategy/s01e05_api_help.md")
            return

        except Exception as e:
            print(f"Error on attempt {attempt + 1}: {e}")
            time.sleep(5)

    print("Failed to get help after 10 attempts.")

if __name__ == "__main__":
    main()
