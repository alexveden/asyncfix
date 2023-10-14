<!-- markdownlint-disable -->

<a href="https://github.com/alexveden/asyncfix/blob/main/asyncfix/connection_server.py#L0"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

# <kbd>module</kbd> `connection_server`
Dummy FIX server module. 



---

<a href="https://github.com/alexveden/asyncfix/blob/main/asyncfix/connection_server.py#L11"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>class</kbd> `AsyncFIXDummyServer`
Simple server which supports only single connection (just for testing). 

<a href="https://github.com/alexveden/asyncfix/blob/main/asyncfix/connection_server.py#L14"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>method</kbd> `__init__`

```python
__init__(
    protocol: FIXProtocolBase,
    sender_comp_id: str,
    target_comp_id: str,
    journaler: Journaler,
    host: str,
    port: int,
    heartbeat_period: int = 30,
    logger: Logger | None = None
)
```

Initialization. 



**Args:**
 
 - <b>`protocol`</b>:  FIX protocol used in codec 
 - <b>`sender_comp_id`</b>:  server sender_comp_id tag 
 - <b>`target_comp_id`</b>:  server target_comp_id tag 
 - <b>`journaler`</b>:  message journaler 
 - <b>`host`</b>:  fix host to listen 
 - <b>`port`</b>:  fix port to bind 
 - <b>`heartbeat_period`</b>:  heartbeat_period in seconds 
 - <b>`logger`</b>:  custom logger instance 


---

#### <kbd>property</kbd> connection_role

Current connection role. 

---

#### <kbd>property</kbd> connection_state

Current connection state. 

---

#### <kbd>property</kbd> heartbeat_period

Current connection heartbeat period in seconds. 

---

#### <kbd>property</kbd> protocol

Underlying FIXProtocolBase of a connection. 



---

<a href="https://github.com/alexveden/asyncfix/blob/main/asyncfix/connection_server.py#L49"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>method</kbd> `connect`

```python
connect()
```

Starts the server and infinitely runs it. 



**Raises:**
 
 - <b>`FIXConnectionError`</b>:  when already connected 




---

_This file was automatically generated via [lazydocs](https://github.com/ml-tooling/lazydocs)._
