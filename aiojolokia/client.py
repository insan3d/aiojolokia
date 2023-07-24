# -*- mode: python ; coding: utf-8 -*-

"""Pydantic-driven aiohttp-based Jookia API client."""

from typing import Any, AsyncGenerator, Iterable, Sequence

from aiohttp import ClientSession
from aiohttp.helpers import BasicAuth
from aiohttp.typedefs import StrOrURL

from aiojolokia.models import JolokiaRequest, JolokiaResponse, JolokiaVersion, Operation


class JavaException(Exception):
    """Raised based on error message from Jolokia if `raise_exceptions` is enabled."""


class JolokiaClient:
    """Pydantic-driven aiohttp-based Jookia API client."""

    def __init__(self, base_url: StrOrURL, auth: BasicAuth | None = None, raise_exceptions: bool = False) -> None:
        """
        Pydantic-driven aiohttp-based Jookia API client.

        Args:
            base_url: base Jolokia URL (usually `http://<host>:<post>/jolokia`)
            auth: tuple of `login` and `password` and optional `encoding` for HTTP Basic authentication.
            raise_exceptions: set to `True` to receive `ExceptionGroup` based on Jolokia error responses.
        """

        self._base_url = base_url
        self._auth: BasicAuth | None = auth
        self._raise: bool = raise_exceptions

    @staticmethod
    def _build_exception(response: JolokiaResponse) -> Exception:
        """
        Generate pythonic `Exception` from error response.

        For example if requesting `/jolokia/versio` (mistype), response will contain `error`, `error_type` and optional
        `stacktrace` fields, which will be converted into newly-generated at runtime `Exception`-inherited class.

        Last part of `error_type` field (e.g.) `java.lang.IllegalArgumentException` will be new class name,
        `error` field will be passed into exception as sole argument (`IllegalArgumentException(response.error)`) and
        `stacktrace`, if included, will be added to new exception instance with `.add_note()`.
        """

        exc_name: str = response.error_type.split(".")[-1] if response.error_type else "Throwable"

        exc_msg: str | None = None
        if response.error:
            exc_msg = ": ".join(response.error.split(": ")[1:])

        exc_cls = type(exc_name, (JavaException,), {})
        exc = exc_cls(exc_msg) if exc_msg else exc_cls()
        if response.stacktrace:
            exc.add_note(response.stacktrace)

        return exc

    async def fetch_json(self, operations: Iterable[JolokiaRequest]) -> Iterable[Any]:
        """
        Make bulk POST request to Jolokia and return JSON response.

        See https://jolokia.org/reference/html/protocol.html#post-request.
        """

        # Serialize every operation into JSON array
        data: str = "[" + ",".join(request.json(exclude_none=True) for request in operations) + "]"

        # Send POST bulk request to Jolokia. This is not good to instanciate aiohttp.ClientSession on
        # each request and better to do this in some kind of asynchonious .init() method, but this may
        # lead to the situation when JolokiaClient is created before event loop even starts (e.g. on
        # __module__ level before asyncio.run() or in .__init__() of any class, which is synchronous).
        async with ClientSession(auth=self._auth) as session:
            async with session.post(url=self._base_url, data=data) as jolokia_response:
                return await jolokia_response.json(content_type=None)

    async def request(self, operations: Iterable[JolokiaRequest]) -> AsyncGenerator[JolokiaResponse, None]:
        """
        Make bulk POST request to Jolokia and return response object.

        See https://jolokia.org/reference/html/protocol.html#post-request.
        """

        # Iterate over every response ensuring what received data is Sequence
        # (just in case of global exception happened) and try to parse every
        # item as JolokiaResponce object.

        exceptions: list[Exception] = []
        json_obj: Any = await self.fetch_json(operations)
        if not isinstance(json_obj, Sequence):
            json_obj = [json_obj]

        for result in json_obj:
            response = JolokiaResponse(**result)

            if response.status >= 400:
                exceptions.append(self._build_exception(response))

            yield response

        # Raise all exceptions if asked to
        if self._raise and exceptions:
            raise ExceptionGroup("JolokiaException", exceptions)

    @property
    async def version(self) -> JolokiaVersion:
        """Jolokia agent version information."""

        # Make bulk request with single operation and extract its (first) result
        # Ignoring type since without return_json this will always try to return JolokiaResponce
        response: JolokiaResponse = await self.request((JolokiaRequest(type=Operation.VERSION),)).__anext__()  # type: ignore

        # Convert to `JolokiaVersion` object for convenience.
        if response.status == 200:
            return JolokiaVersion(**response.value)  # type: ignore

        exc: Exception | None = self._build_exception(response)
        raise exc if exc else RuntimeError("Undefined exception happened while requesting version.")
