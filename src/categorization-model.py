import asyncio
from dedalus_labs import AsyncDedalus, DedalusRunner
from dotenv import load_dotenv
from dedalus_labs.utils.stream import stream_async

load_dotenv()

async def main():
    client = AsyncDedalus()
    runner = DedalusRunner(client)

    response = await runner.run(
        input="What was the score of the 2025 Wimbledon final for men single",
        model="openai/gpt-4.1"
    )

    print(response.final_output)

if __name__ == "__main__":
    asyncio.run(main())