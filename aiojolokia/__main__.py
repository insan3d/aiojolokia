#!/usr/bin/env python3
# -*- mode: python ; coding: utf-8 -*-

"""
Python Jookia API client module. As command-line tool, produces Jolokia JSON output.

Jolokia is a JMX-HTTP bridge giving an alternative to JSR-160 connectors. It is an agent based approach with support for many platforms. In addition to basic JMX operations it enhances JMX remoting with unique features like bulk requests and fine grained security policies.

See https://jolokia.org/reference/html/protocol.html for more information.
"""

import asyncio

from argparse import ArgumentParser, HelpFormatter, Namespace, RawDescriptionHelpFormatter
from contextlib import suppress
from typing import Any, Iterable

from aiohttp import BasicAuth

from aiojolokia.client import JolokiaClient
from aiojolokia.models import JolokiaRequest, Operation

__prog__ = "aiojolokia"
__version__ = "0.1.0"
__status__ = "Development"
__author__ = "Alexander Pozlevich"
__email__ = "apozlevich@gmail.com"
__licence__ = "WTFPL"


async def _main() -> None:
    """Run as CLI utility."""

    # Prepare root parser
    parent_parser = ArgumentParser(
        prog=__prog__,
        description=__doc__,
        epilog=f"Written by {__author__} <{__email__}>. Licensed under terms of {__licence__}.",
        formatter_class=lambda prog: RawDescriptionHelpFormatter(prog=prog, max_help_position=36),
    )

    # Root arguments
    parent_parser.add_argument("--version", action="version", version=f"{__version__} {__status__}")
    parent_parser.add_argument("base_url", help="specify base Jolokia URL (e.g. http://localhost:8080/jolokia)")
    parent_parser.add_argument("-U", "--username", metavar="username", help="specify username for HTTP Basic authentication")
    parent_parser.add_argument("-P", "--password", default="", metavar="username", help="specify password for HTTP Basic authentication")

    # Additional parser will be reused in various operations
    mbean_parser = ArgumentParser(add_help=False)
    mbean_parser.add_argument("-m", "--mbean", metavar="name", required=True, help="specify MBean name")
    attribute_parser = ArgumentParser(add_help=False)
    attribute_parser.add_argument("-a", "--attribute", metavar="name", help="specify attribute name")
    path_parser = ArgumentParser(add_help=False)
    path_parser.add_argument("-p", "--path", metavar="path", help="specify inner path for operation")

    # Create subparsers
    subparsers = parent_parser.add_subparsers(
        title="operations",
        dest="request",
        required=True,
        description=f"See {__prog__} <operation> --help for more information",
    )

    # Read argument depends on mbean, atttibute and path arguments
    subparsers.add_parser(
        "read",
        parents=(mbean_parser, attribute_parser, path_parser),
        help="read MBean attributes",
        description="Reading MBean attributes is probably the most used JMX method, especially when it comes to monitoring. Concerning Jolokia, it is also the most powerful one with the richest semantics. Obviously the value of a single attribute can be fetched, but Jolokia supports also fetching of a list of given attributes on a single MBean or even on multiple MBeans matching a certain pattern.",
        epilog="See https://jolokia.org/reference/html/protocol.html#read for more information.",
        formatter_class=lambda prog: HelpFormatter(prog=prog, max_help_position=29),
    )

    # Write parser depends on mbean, attribute and path arguments
    write_parser: ArgumentParser = subparsers.add_parser(
        "write",
        parents=(mbean_parser, attribute_parser, path_parser),
        help="write value to MBean attribute",
        description="Writing an attribute is quite similar to reading one, except that the request takes an additional value element.",
        epilog="See https://jolokia.org/reference/html/protocol.html#write for more information.",
        formatter_class=lambda prog: HelpFormatter(prog=prog, max_help_position=27),
    )
    write_parser.add_argument("-v", "--value", required=True, metavar="value", help="specify value to write")

    # Exec parser depends on mbean argument
    exec_parser: ArgumentParser = subparsers.add_parser(
        "exec",
        parents=(mbean_parser,),
        help="execute JMX operation",
        description='Beside attribute provides a way for the execution of exposed JMX operations with optional arguments. The same as for writing attributes, Jolokia must be able to serialize the arguments. See Section 6.4, "Object serialization" for details. Execution of overloaded methods is supported. The JMX specifications recommends to avoid overloaded methods when exposing them via JMX, though.',
        epilog="See https://jolokia.org/reference/html/protocol.html#exec for more information.",
        formatter_class=lambda prog: HelpFormatter(prog=prog, max_help_position=39),
    )
    exec_parser.add_argument("-o", "--operation-name", required=True, metavar="operation", help="specify name of the operation to execute")
    exec_parser.add_argument("-a", "--arguments", metavar="arg", nargs="*", help="add arguments to operation")

    # Search argument depends on mbean argument
    subparsers.add_parser(
        "search",
        parents=(mbean_parser,),
        help="query for MBeans with a given pattern",
        description="With the Jolokia search operation the agent can be queried for MBeans with a given pattern. Searching will be performed on every MBeanServer found by the agent.",
        epilog="See https://jolokia.org/reference/html/protocol.html#search for more information.",
        formatter_class=lambda prog: HelpFormatter(prog=prog, max_help_position=25),
    )

    # List parser depends on path argument
    subparsers.add_parser(
        "list",
        parents=(path_parser,),
        help="gather information about accessible MBeans",
        description="The list operation collects information about accessible MBeans. This information includes the MBean names, their attributes, operations and notifications along with type information and description (as far as they are provided by the MBean author which doesn't seem to be often the case).",
        epilog="See https://jolokia.org/reference/html/protocol.html#list for more information.",
    )

    # Version parser doesn't depend on any arguments
    subparsers.add_parser(
        "version",
        help="get Jolokia agent and protocol version information",
        description="The Jolokia command version returns the version of the Jolokia agent along with the protocol version.",
        epilog="See https://jolokia.org/reference/html/protocol.html#version for more information.",
    )

    # Parse args and build auth tuple
    args: Namespace = parent_parser.parse_args()
    auth: BasicAuth | None = None
    if args.username:
        auth = BasicAuth(login=args.username, password=args.password)

    # Instanciate client
    client = JolokiaClient(base_url=args.base_url, auth=auth, raise_exceptions=False)

    # Build request model
    kwargs: dict[str, Any | None] = {
        key: args.__dict__.get(key) for key in ("mbean", "attribute", "path", "value", "operation", "arguments")
    }
    request = JolokiaRequest(type=Operation(args.request), **kwargs)

    # Output response
    response: Iterable[Any] = await client.fetch_json((request,))
    print(response)


if __name__ == "__main__":
    with suppress(KeyboardInterrupt):
        asyncio.run(_main())
