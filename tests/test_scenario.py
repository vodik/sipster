import asyncio

import pytest
from sipster.scenarios import fastanswer


@pytest.mark.asyncio
async def test_fastanswer():
    useragents = await fastanswer()
    await asyncio.gather(*useragents)
