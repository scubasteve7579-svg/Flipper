import asyncio
from limited_check_url import limited_check_url

async def main():
    url = "https://www.ebay.com/itm/155399653056"  # sample listing
    proxy = None  # or your rotating proxy
    sem = asyncio.Semaphore(1)
    
    result = await limited_check_url(url, proxy, sem)
    print("RESULT:", result)

asyncio.run(main())
