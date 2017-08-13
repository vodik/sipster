import asyncio

import pytest
from sipster.scenarios import fastanswer


@pytest.mark.asyncio
def test_fastanswer():
    useragents = yield from fastanswer()
    yield from asyncio.gather(*useragents)
