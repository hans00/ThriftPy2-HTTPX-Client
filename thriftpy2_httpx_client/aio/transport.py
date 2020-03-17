import io
import logging
import asyncio as aio
from typing import Union, Optional

from thriftpy2.transport.base import TTransportException
from thriftpy2.contrib.aio.transport import TAsyncTransportBase

import httpx

logger = logging.getLogger(__name__)


class TAsyncHTTPXClient(TAsyncTransportBase):
    def __init__(self, url: Union[str, httpx.URL], **kwargs):
        if kwargs.pop('base_url', None) is not None:
            logger.warning("Ignoring provided 'base_url', use 'url' instead.")
        self._url = httpx.URL(url)
        self._kwargs = kwargs
        kwargs['base_url'] = self._url

        self._client: Optional[httpx.AsyncClient] = None
        self._wbuf = io.BytesIO()
        self._rbuf = io.BytesIO()

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            raise TTransportException(
                type=TTransportException.NOT_OPEN,
                message=f"Transport is not open!",
            )
        return self._client

    def is_open(self) -> bool:
        return self._client is not None

    async def open(self) -> None:
        if self.is_open():
            logger.debug("Ignoring open on already open client")
            return
        self._client = httpx.AsyncClient(**self._kwargs)
        logger.debug(f"Opened new HTTP client: {self._client!r}")

        headers = self._client.headers
        headers['HOST'] = self._url.host
        headers['Content-Type'] = 'application/x-thrift'
        headers.setdefault('User-Agent', 'Python/THTTPClient')

    def close(self) -> None:
        if not self.is_open():
            logger.debug("Ignoring close on already closed client")
            return  # Already closed
        logger.debug(f"Closing {self._client!r}")
        # Close must be sync, so create a task to handle cleanup soon
        aio.get_event_loop().create_task(self._client.aclose())
        self._client = None
        self._wbuf = io.BytesIO()  # Faster to make a new one than clear

    async def read(self, sz: int) -> bytes:
        logger.debug(f"Reading {sz} from buffer")
        data = self._rbuf.read(sz)
        if not data:
            raise EOFError("No more data from server")
        return data

    _read = read

    def write(self, buf: bytes) -> None:
        logger.debug(f"Writing {len(buf)} bytes to buffer")
        self._wbuf.write(buf)

    async def flush(self) -> None:
        logger.debug(f"Flushing write buffer ({self._wbuf.tell()} bytes)")
        data = self._wbuf.getvalue()
        self._wbuf = io.BytesIO()

        logger.debug("Sending request to server")
        response = await self.client.post(url='', data=data)
        # Assume all content has been read
        self._rbuf = io.BytesIO(response.content)
        logger.debug(f"Received {self._rbuf.tell()} bytes")