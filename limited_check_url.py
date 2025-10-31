import random
import re
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
]

async def limited_check_url(url, proxy_url, semaphore, timeout=20000):
    async with semaphore:
        proxy_dict = None
        if proxy_url:
            proxy_dict = {"server": proxy_url}

        async def _check(playwright):
            browser = None
            context = None
            page = None
            try:
                browser = await playwright.chromium.launch(
                    headless=True,
                    args=["--no-sandbox", "--disable-gpu"]
                )
                if not browser:
                    print("Failed to launch browser")
                    return (False, None)

                ua = random.choice(USER_AGENTS)
                context_kwargs = {
                    "user_agent": ua,
                    "viewport": {"width": 1280, "height": 800}
                }

                if proxy_dict:
                    context_kwargs["proxy"] = proxy_dict

                context = await browser.new_context(**context_kwargs)
                if not context:
                    print("Failed to create context")
                    return (False, None)

                page = await context.new_page()
                if not page:
                    print("Failed to create page")
                    return (False, None)

                await page.add_init_script("""
                () => {
                    Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                    window.chrome = { runtime: {} };
                    Object.defineProperty(navigator, 'languages', {get: () => ['en-US','en']});
                    Object.defineProperty(navigator, 'plugins', {get: () => [1,2,3]});
                }
                """)

                await page.set_default_navigation_timeout(timeout)
                await page.goto(url, wait_until="domcontentloaded")

                content = await page.content()

                if "Pardon Our Interruption" in content or "Checking your browser" in content:
                    return ("bot_detected", None)

                if "This listing was ended" in content or "This listing has ended" in content:
                    return ("ended", None)

                if "Sold" in content or "OutOfStock" in content or "Ended" in content:
                    price_el = await page.query_selector("span[itemprop='price'], .s-item__price, .notranslate")
                    if price_el:
                        txt = (await price_el.inner_text()).replace("$", "").replace(",", "")
                        match = re.search(r"(\d+(\.\d{1,2})?)", txt)
                        if match:
                            return ("sold", float(match.group(1)))
                    return ("sold", None)

                # If price exists, listing is active
                if await page.query_selector(".s-item__price, span[itemprop='price'], .notranslate"):
                    return ("active", None)

                return ("bot_detected", None)

            except PlaywrightTimeoutError:
                return ("bot_detected", None)
            except Exception as e:
                print(f"[Playwright error] {e}")
                return (False, None)
            finally:
                try:
                    if page is not None:
                        await page.close()
                except Exception as e:
                    print(f"[Playwright close error] page: {e}")
                try:
                    if context is not None:
                        await context.close()
                except Exception as e:
                    print(f"[Playwright close error] context: {e}")
                try:
                    if browser is not None:
                        await browser.close()
                except Exception as e:
                    print(f"[Playwright close error] browser: {e}")

        try:
            async with async_playwright() as p:
                return await _check(p)
        except Exception as e:
            print(f"[Playwright outer error] {e}")
            return (False, None)

if __name__ == "__main__":
    import asyncio

    # Example usage:
    test_url = "https://www.ebay.com/itm/404684282326"  # Replace with a real eBay item URL
    proxy = None  # Or set to your proxy string if needed

    async def main():
        # Use a dummy semaphore for testing
        semaphore = asyncio.Semaphore(1)
        result = await limited_check_url(test_url, proxy, semaphore)
        print("RESULT:", result)

    asyncio.run(main())
