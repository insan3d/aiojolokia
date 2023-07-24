# Asynchronous [Jookia](https://jolokia.org) API client for Python

`aiojolokia` is a simple [Pydantic](https://docs.pydantic.dev/latest/) model definition with [aiohttp](https://docs.aiohttp.org/en/stable/) client for [Jookia protocol](https://jolokia.org/reference/html/protocol.html). All operations (`read`, `write`, `exec`, `search`, `list`, `version`) are supported and processed as bulk POST-requests. Jolokia service discovery is not supported.

## Requirements

Python 3.11+ is required. Dependencies are `pydantic` and `aiohttp`.

## Command-line usage

Root arguments:

  - `--username`: optional username for HTTP Basic authentication
  - `--password`: optional password for HTTP Basic authentication
  - `base_url`: base Jolokia URL (e.g. `http://localhost:8080/jolokia`)
  - `request`: type of operation (`read`, `write`, `exec`, `search`, `list`, `version`)

Each operation has its own set of arguments:

  - `read`: `--mbean` name, `--attribute` name and `--path`
  - `write`: `--mbean` name, `--attribute` name, `--path` of operation and `--value` to write
  - `exec`:  `--mbean` name, `--operation-name`,  and list of `--arguments`
  - `search`:  `--mbean` name
  - `list`: `--path` to list
  - `version`: no additional arguments

Some arguments are required and some may be omited, please, refer to [Jookia protocol](https://jolokia.org/reference/html/protocol.html) documentation. Any operation will simply output JSON received from Jolokia:

```bash session
python -m aiojolokia http://localhost:8081/jolokia read --mbean 'java.lang:type=Memory' --attribute 'HeapMemoryUsage' --path 'used'

[{'request': {'path': 'used', 'mbean': 'java.lang:type=Memory', 'attribute': 'HeapMemoryUsage', 'type': 'read'}, 'value': 194103808, 'timestamp': 1688841055, 'status': 200}]
```

But when using as module, responses are converted and validated as Pydantic models. Python API example:

```python
from aiohttp import BasicAuth

from aiojolokia import JolokiaClient, JolokiaRequest, Operation

auth = BasicAuth(login="jolokia", password="jolokia")
jolokia = JolokiaClient("http://localhost:8080/jolokia", auth=auth)

request1 = JolokiaRequest(type=Operation.READ, mbean="java.lang:type=Memory", attribute="HeapMemoryUsage", path="used")
request2 = JolokiaRequest(type=Operation.READ, mbean="java.lang:type=Memory", attribute="HeapMemoryUsage", path="free")
request3 = JolokiaRequest(type=Operation.WRITE, mbean="java.lang:type=ClassLoading", attribute="Verbose", value="true")
request4 = JolokiaRequest(type=Operation.VERSION)

async for result in jolokia.request((request1, request2, request3, request4)):
    print(result.value)
```

Will output

- used heap memory of JVM as `int`
- `None` since there is no path `free` for `HeapMemoryUsage`
- `True` because Jolokia repeats `value` on successfull write
- Jolokia version as object in [defined format](https://jolokia.org/reference/html/protocol.html#version)

Each result has it's request as `.request` property. [Historical values](https://jolokia.org/reference/html/protocol.html#history) and [proxy requests](https://jolokia.org/reference/html/protocol.html#protocol-proxy) are supported, but never tested.

## Exceptions

If `JolokiaClient` instantiated with `raise_exceptions=True`, when response from Jolokia having `status` field with code greater than 400, new `Exception` class is generated based on `error`, `error_type` and `stacktrace` fields of response and exception raised. All exceptions from one response will be raised as [PEP 654](https://peps.python.org/pep-0654/) `ExceptionGroup`.

For example, this code:

```python
from aiohttp import BasicAuth

from aiojolokia import JolokiaClient, JolokiaRequest, Operation

auth = BasicAuth(login="jolokia", password="jolokia")
jolokia = JolokiaClient("http://localhost:8081/jolokia", auth=auth, raise_exceptions=True)

request = JolokiaRequest(type=Operation.READ, mbean="invalid_")
```

Will produce `aiojolokia.client.IllegalArgumentException` from received `java.lang.IllegalArgumentException` exception information like this:

```
  + Exception Group Traceback (most recent call last):
  |   File "/home/apozlevich/aiojolokia/test.py", line 22, in <module>
  |     asyncio.run(main())
  |   File "/usr/lib/python3.11/asyncio/runners.py", line 190, in run
  |     return runner.run(main)
  |            ^^^^^^^^^^^^^^^^
  |   File "/usr/lib/python3.11/asyncio/runners.py", line 118, in run
  |     return self._loop.run_until_complete(task)
  |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  |   File "/usr/lib/python3.11/asyncio/base_events.py", line 653, in run_until_complete
  |     return future.result()
  |            ^^^^^^^^^^^^^^^
  |   File "/home/apozlevich/aiojolokia/test.py", line 17, in main
  |     async for _ in jolokia.request((request,)):
  |   File "/home/apozlevich/aiojolokia/aiojolokia/client.py", line 99, in request
  |     raise ExceptionGroup("JolokiaException", exceptions)
  | ExceptionGroup: JolokiaException (1 sub-exception)
  +-+---------------- 1 ----------------
    | aiojolokia.client.IllegalArgumentException: Invalid object name. Key properties cannot be empty
    | java.lang.IllegalArgumentException: Invalid object name. Key properties cannot be empty
    |   at org.jolokia.request.JmxRequestFactory.createPostRequest(JmxRequestFactory.java:119)
    |   at org.jolokia.request.JmxRequestFactory.createPostRequests(JmxRequestFactory.java:137)
    |   at org.jolokia.http.HttpRequestHandler.handlePostRequest(HttpRequestHandler.java:123)
    |   at org.jolokia.http.AgentServlet$3.handleRequest(AgentServlet.java:493)
    |   at org.jolokia.http.AgentServlet.handleSecurely(AgentServlet.java:383)
    |   at org.jolokia.http.AgentServlet.handle(AgentServlet.java:354)
    |   at org.jolokia.http.AgentServlet.doPost(AgentServlet.java:317)
    |   at javax.servlet.http.HttpServlet.service(HttpServlet.java:555)
    |   at javax.servlet.http.HttpServlet.service(HttpServlet.java:623)
    |   at org.apache.catalina.core.ApplicationFilterChain.internalDoFilter(ApplicationFilterChain.java:209)
    |   at org.apache.catalina.core.ApplicationFilterChain.doFilter(ApplicationFilterChain.java:153)
    |   at org.apache.tomcat.websocket.server.WsFilter.doFilter(WsFilter.java:51)
    |   at org.apache.catalina.core.ApplicationFilterChain.internalDoFilter(ApplicationFilterChain.java:178)
    |   at org.apache.catalina.core.ApplicationFilterChain.doFilter(ApplicationFilterChain.java:153)
    |   at org.apache.catalina.core.StandardWrapperValve.invoke(StandardWrapperValve.java:167)
    |   at org.apache.catalina.core.StandardContextValve.invoke(StandardContextValve.java:90)
    |   at org.apache.catalina.authenticator.AuthenticatorBase.invoke(AuthenticatorBase.java:481)
    |   at org.apache.catalina.core.StandardHostValve.invoke(StandardHostValve.java:130)
    |   at org.apache.catalina.valves.ErrorReportValve.invoke(ErrorReportValve.java:93)
    |   at org.apache.catalina.valves.AbstractAccessLogValve.invoke(AbstractAccessLogValve.java:673)
    |   at org.apache.catalina.core.StandardEngineValve.invoke(StandardEngineValve.java:74)
    |   at org.apache.catalina.connector.CoyoteAdapter.service(CoyoteAdapter.java:343)
    |   at org.apache.coyote.http11.Http11Processor.service(Http11Processor.java:390)
    |   at org.apache.coyote.AbstractProcessorLight.process(AbstractProcessorLight.java:63)
    |   at org.apache.coyote.AbstractProtocol$ConnectionHandler.process(AbstractProtocol.java:926)
    |   at org.apache.tomcat.util.net.NioEndpoint$SocketProcessor.doRun(NioEndpoint.java:1791)
    |   at org.apache.tomcat.util.net.SocketProcessorBase.run(SocketProcessorBase.java:52)
    |   at org.apache.tomcat.util.threads.ThreadPoolExecutor.runWorker(ThreadPoolExecutor.java:1191)
    |   at org.apache.tomcat.util.threads.ThreadPoolExecutor$Worker.run(ThreadPoolExecutor.java:659)
    |   at org.apache.tomcat.util.threads.TaskThread$WrappingRunnable.run(TaskThread.java:61)
    |   at java.base/java.lang.Thread.run(Thread.java:829)
    | Caused by: javax.management.MalformedObjectNameException: Key properties cannot be empty
    |   at java.management/javax.management.ObjectName.construct(ObjectName.java:485)
    |   at java.management/javax.management.ObjectName.<init>(ObjectName.java:1406)
    |   at org.jolokia.request.JmxObjectNameRequest.initObjectName(JmxObjectNameRequest.java:130)
    |   at org.jolokia.request.JmxObjectNameRequest.<init>(JmxObjectNameRequest.java:65)
    |   at org.jolokia.request.JmxReadRequest.<init>(JmxReadRequest.java:68)
    |   at org.jolokia.request.JmxReadRequest$1.create(JmxReadRequest.java:164)
    |   at org.jolokia.request.JmxReadRequest$1.create(JmxReadRequest.java:151)
    |   at org.jolokia.request.JmxRequestFactory.createPostRequest(JmxRequestFactory.java:117)
    |   ... 30 more

    +------------------------------------
```