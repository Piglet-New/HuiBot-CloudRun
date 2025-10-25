import asyncio
from db import run_migrations, init_engine

async def main():
    await init_engine()
    await run_migrations()
    print("migrations ok")

if __name__ == "__main__":
    asyncio.run(main())
