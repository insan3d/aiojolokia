# -*- mode: python ; coding: utf-8 -*-

"""
Jolokia API models.

See https://jolokia.org/reference/html/protocol.html.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Iterable, Literal, Mapping

from pydantic import BaseModel  # pylint: disable=no-name-in-module
from pydantic import validator  # type: ignore
from pydantic import Field


# pylint: disable=unused-argument
def _convert_timestamp(cls: object, timestamp: int | None) -> datetime | None:
    """Convert timestamp field with unixtime into `datetime.datetime()` object."""

    return datetime.fromtimestamp(timestamp) if timestamp is not None else None


class Operation(Enum):
    """
    See section 6.2 of Jolokia protocol specification:

    https://jolokia.org/reference/html/protocol.html#jolokia-operations.
    """

    READ = "read"
    WRITE = "write"
    EXEC = "exec"
    SEARCH = "search"
    LIST = "list"
    VERSION = "version"

    def __str__(self) -> str:
        return self.value


# pylint: disable=too-few-public-methods
class RequestConfig(BaseModel):
    """
    Jolokia operations can be influenced by so-called processing parameters.

    See https://jolokia.org/reference/html/protocol.html#processing-parameters.
    """

    maxDepth: int | None = Field(
        default=None,
        alias="max_depth",
        description="Maximum depth of the tree traversal into a bean's properties. The maximum value as configured in the agent's configuration is a hard limit and cannot be exceeded by a query parameter.",
    )

    maxCollectionSize: int | None = Field(
        default=None,
        alias="max_collection_size",
        description="For collections (lists, maps) this is the maximum size.",
    )

    maxObjects: int | None = Field(
        default=None,
        alias="max_objects",
        description="Number of objects to visit in total. A hard limit can be configured in the agent's configuration.",
    )

    ignoreErrors: bool | None = Field(
        default=False,
        alias="ignore_errors",
        description="If set to `True`, a Jolokia operation will not return an error if an JMX operation fails, but includes the exception message as value. This is useful for e.g. the read operation when requesting multiple attributes' values.",
    )

    mimeType: Literal["text/plain"] | Literal["application/json"] = Field(
        default=Literal["text/plain"],
        alias="mime_type",
        description="The MIME type to return for the response. By default, this is `text/plain`, but it can be useful for some tools to change it to `application/json`. Init parameters can be used to change the default mime type. Only `text/plain` and `application/json` are allowed. For any other value Jolokia will fallback to `text/plain`.",
    )

    canonicalNaming: bool = Field(
        default=True,
        alias="canonical_naming",
        description="Defaults to `True` to return the canonical format of property lists. If set to `False` then the default unsorted property list is returned.",
    )

    includeStackTrace: bool | Literal["runtime"] = Field(
        default=True,
        alias="include_stack_trace",
        description="If set to `True`, then in case of an error the stack trace is included. With `False` no stack trace will be returned, and when this parameter is set to `runtime` only for RuntimeExceptions a stack trace is put into the error response. Default is `True` if not set otherwise in the global agent configuration.",
    )

    serializeException: bool = Field(
        default=False,
        alias="serialize_exception",
        description="If this parameter is set to `True` then a serialized version of the exception is included in an error response. This value is put under the key `error_value` in the response value. By default this is set to `False` except when the agent global configuration option is configured otherwise.",
    )

    ifModifiedSince: int | None = Field(
        default=None,
        alias="if_modified_since",
        description="If this parameter is given, its value is interpreted as epoch time (seconds since 01.01.1970) and if the requested value did not change since this time, an empty response (with no value) is returned and the response status code is set to `304 Not modified`. This option is currently only supported for `.list()` requests. The time value can be extracted from a previous response timestamp.",
    )


# pylint: disable=too-few-public-methods
class ProxyTarget(BaseModel):
    """
    Proxy request `target` section.

    `url` within the `target` section is a JSR-160 service URL for the target server reachable from within the proxy agent.
    `user` and `password` are optional credentials used for the JSR-160 communication.

    See https://jolokia.org/reference/html/protocol.html#protocol-proxy.
    """

    url: str
    user: str | None = None
    password: str | None = None


# pylint: disable=too-few-public-methods
class JolokiaRequest(BaseModel):
    """Base class for Jolokia requests."""

    type: Operation

    # Common arguments
    mbean: str | None = None
    attribute: str | None = None
    path: str | None = None

    # For write requests
    value: Any | None = None

    # For exec requests
    operation_name: str | None = None
    arguments: Iterable[Any] | None = None

    def __eq__(self, __value: object) -> bool:
        if not isinstance(__value, JolokiaRequest):
            return False

        # Order sligtly matters for performance
        for attr in ("type", "mbean", "attribute", "path", "value", "operation_name", "arguments"):
            if self.__getattribute__(attr) != __value.__getattribute__(attr):
                return False

        return True


# pylint: disable=too-few-public-methods
class HistoricalValue(BaseModel):
    """
    Represents sequence of historical values if tracking enabled.

    https://jolokia.org/reference/html/protocol.html#history.
    """

    value: Any
    timestamp: int | None = None

    _convert_timestamp = validator("timestamp", allow_reuse=True)(_convert_timestamp)  # type: ignore


# pylint: disable=too-few-public-methods
class JolokiaResponse(BaseModel):
    """Response JSON model."""

    status: int
    value: Any | None = None
    history: Iterable[HistoricalValue] | None = None
    request: JolokiaRequest | None = None
    timestamp: int | None = None

    error_type: str | None = None
    error: str | None = None
    stacktrace: str | None = None

    _convert_timestamp = validator("timestamp", allow_reuse=True)(_convert_timestamp)  # type: ignore


# pylint: disable=too-few-public-methods
class _JolokiaVersionInfo(BaseModel):
    """`info` part of `JolokiaVersion`."""

    product: str
    vendor: str
    version: str
    extraInfo: Mapping[str, Any] = Field(alias="extra_info", default={})


# pylint: disable=too-few-public-methods
class JolokiaVersion(BaseModel):
    """
    `version` operation responce model, for convinience.

    See https://jolokia.org/reference/html/protocol.html#version.
    """

    protocol: str
    agent: str
    config: Mapping[str, Any] = {}
    info: _JolokiaVersionInfo
