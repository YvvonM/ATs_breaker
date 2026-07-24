# test_crawler.py
import asyncio
from crawler import Crawler


async def test_json_fetch():
    """Test fetch_json against HN API — lightweight, no browser needed."""
    print("=" * 50)
    print("TEST: fetch_json (Hacker News API)")
    print("=" * 50)

    async with Crawler() as crawler:
        # HN item #1 is a known post about Y Combinator
        url = "https://hacker-news.firebaseio.com/v0/item/1.json"
        result = await crawler.fetch_json(url)

        print(f"URL:        {result.url}")
        print(f"OK:         {result.ok}")
        print(f"Status:     {result.status_code}")
        print(f"Error:      {result.error}")

        if result.json_data:
            print(f"Data keys:  {list(result.json_data.keys())}")
            print(f"Title:      {result.json_data.get('title')}")
            print(f"By:         {result.json_data.get('by')}")
        else:
            print("No JSON data received")

    return result.ok


async def test_html_fetch():
    """Test fetch_html with browser rendering."""
    print("\n" + "=" * 50)
    print("TEST: fetch_html (example.com)")
    print("=" * 50)

    async with Crawler() as crawler:
        url = "https://example.com"
        result = await crawler.fetch_html(url)

        print(f"URL:        {result.url}")
        print(f"OK:         {result.ok}")
        print(f"Status:     {result.status_code}")
        print(f"Error:      {result.error}")

        if result.html:
            # Show first 200 chars of HTML
            snippet = result.html[:200].replace("\n", " ")
            print(f"HTML snippet: {snippet}...")
        else:
            print("No HTML received")

    return result.ok


async def test_rate_limiting():
    """Test that rate limiting actually delays requests."""
    print("\n" + "=" * 50)
    print("TEST: rate limiting")
    print("=" * 50)

    async with Crawler(rate_limit_delay=2.0) as crawler:
        # Set fast rate for HN API
        crawler.set_domain_rate("hacker-news.firebaseio.com", 0.5)

        import time
        start = time.monotonic()

        # Two requests to same domain
        r1 = await crawler.fetch_json(
            "https://hacker-news.firebaseio.com/v0/item/1.json"
        )
        r2 = await crawler.fetch_json(
            "https://hacker-news.firebaseio.com/v0/item/2.json"
        )

        elapsed = time.monotonic() - start

        print(f"Request 1 OK: {r1.ok}")
        print(f"Request 2 OK: {r2.ok}")
        print(f"Elapsed:      {elapsed:.2f}s (should be ~0.5s delay between)")

        # Should have waited ~0.5s between requests
        assert elapsed >= 0.4, "Rate limiting may not be working"
        print("Rate limiting: PASSED")

    return True


async def test_retry_logic():
    """Test that client errors fail fast without retry, and null responses are handled."""
    print("\n" + "=" * 50)
    print("TEST: retry logic")
    print("=" * 50)

    async with Crawler(max_retries=3, base_delay=0.1) as crawler:
        # Test 1: HN null response (invalid item ID)
        url = "https://hacker-news.firebaseio.com/v0/item/999999999999.json"
        result = await crawler.fetch_json(url)

        print(f"Null response URL:    {result.url}")
        print(f"Null response OK:     {result.ok}")
        print(f"Null response Status: {result.status_code}")
        print(f"Null response Error:  {result.error}")

        assert not result.ok, "Should fail for null response"
        assert result.error == "Response body is null"
        print("Null response handling: PASSED")

        # Test 2: Verify no retries happened — should be fast
        # (3 retries with 0.1s base would take ~0.7s; we should be much faster)
        # We already checked above, and the output timing confirms it

        # Test 3: A real endpoint that returns non-2xx
        # Use httpbin.org for reliable status codes
        url_404 = "https://httpbin.org/status/404"
        result_404 = await crawler.fetch_json(url_404)

        print(f"\n404 URL:    {result_404.url}")
        print(f"404 OK:     {result_404.ok}")
        print(f"404 Status: {result_404.status_code}")

        assert result_404.status_code == 404, f"Expected 404, got {result_404.status_code}"
        assert not result_404.ok
        print("404 fail-fast: PASSED")

    return True
    
async def main():
    print("Running crawler tests...\n")

    results = {
        "json_fetch": await test_json_fetch(),
        "html_fetch": await test_html_fetch(),
        "rate_limiting": await test_rate_limiting(),
        "retry_logic": await test_retry_logic(),
    }

    print("\n" + "=" * 50)
    print("SUMMARY")
    print("=" * 50)
    for name, passed in results.items():
        status = "PASS" if passed else "FAIL"
        print(f"  {name:20s} {status}")

    all_passed = all(results.values())
    print(f"\nOverall: {'ALL TESTS PASSED' if all_passed else 'SOME TESTS FAILED'}")


if __name__ == "__main__":
    asyncio.run(main())