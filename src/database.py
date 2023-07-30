import aiohttp
import asyncio
import aiosqlite

DB = "phrases.db"


class Database:
    def __init__(self, debug: bool):
        self.debug = debug

    async def __aenter__(self):
        self.conn = await aiosqlite.connect(DB)
        self.cursor = await self.conn.cursor()
        await self.create_table()
        await self.create_unique_index()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.cursor.close()
        await self.conn.commit()
        await self.conn.close()

    async def create_table(self):
        await self.cursor.execute('''CREATE TABLE IF NOT EXISTS phrases (id INTEGER PRIMARY KEY AUTOINCREMENT, phrase TEXT)''')
        await self.conn.commit()

    async def create_unique_index(self):
        await self.cursor.execute('''CREATE UNIQUE INDEX IF NOT EXISTS idx_phrase ON phrases (phrase)''')
        await self.conn.commit()

    async def phrases(self):
        """Returns the phrases dataset.

        [
            (1, "I'll think about it."), ...
        ]
        """
        await self.cursor.execute("SELECT * FROM phrases")
        return await self.cursor.fetchall()


    async def add_phrase(self, phrase: str):
        try:
            await self.cursor.execute("INSERT INTO phrases (phrase) VALUES (?)", (phrase,))
            await self.conn.commit()
            if self.debug:
                print(f"Added \"{phrase}\" to the database")
        except aiosqlite.IntegrityError:
            if self.debug:
                print(f"\"{phrase}\" already exists in the database")

    async def fetch_data_and_insert(self, offset):
        link = f"https://datasets-server.huggingface.co/rows?dataset=tatoeba&config=en-mr&split=train&offset={offset}"
        async with aiohttp.ClientSession() as session:
            async with session.get(link) as response:
                if response.status == 200:
                    data = await response.json()
                    rows = data["rows"]
                    for row in rows:
                        phrase = row["row"]["translation"]["en"].replace('"', '')
                        await self.add_phrase(phrase)

    async def setup_database(self):
        tasks = [self.fetch_data_and_insert(offset) for offset in range(0, 53401, 100)]
        await asyncio.gather(*tasks)

