import database
import data
import asyncio
import os


async def main():
    database_exists = os.path.exists('phrases.db')
    async with database.Database(debug=True) as db:
        if not database_exists:
            await db.setup_database()
        phrases = await db.phrases()
    sn = data.DrSbaitsoAudioCollector(data.CHROME)
    sn.produce_audio(phrases)


if __name__ == "__main__":
    asyncio.run(main())
