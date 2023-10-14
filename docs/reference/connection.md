<!-- markdownlint-disable -->

<a href="https://github.com/alexveden/asyncfix/blob/main/asyncfix/connection.py#L0"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

# <kbd>module</kbd> `connection`
Abstract connection module. 



---

<a href="https://github.com/alexveden/asyncfix/blob/main/asyncfix/connection.py#L18"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>class</kbd> `ConnectionState`
Connection status enum. 





---

<a href="https://github.com/alexveden/asyncfix/blob/main/asyncfix/connection.py#L91"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>class</kbd> `ConnectionRole`
Role of the connection INITIATOR / ACCEPTOR. 





---

<a href="https://github.com/alexveden/asyncfix/blob/main/asyncfix/connection.py#L99"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>class</kbd> `AsyncFIXConnection`
AsyncFIX bidirectional connection. 



**Attributes:**
 
 - <b>`connection_state`</b>:  Current connection_state 
 - <b>`connection_role`</b>:  Current connection_role ACCEPTOR | INITIATOR 
 - <b>`log`</b>:  logger 

<a href="https://github.com/alexveden/asyncfix/blob/main/asyncfix/connection.py#L108"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

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

AsyncFIX bidirectional connection. 



**Args:**
 
 - <b>`protocol`</b>:  FIX protocol 
 - <b>`sender_comp_id`</b>:  initiator SenderCompID 
 - <b>`target_comp_id`</b>:  acceptor TargetCompID 
 - <b>`journaler`</b>:  fix messages journaling engine 
 - <b>`host`</b>:  endpoint host 
 - <b>`port`</b>:  endpoint port 
 - <b>`heartbeat_period`</b>:  heartbeat interval in seconds 
 - <b>`logger`</b>:  logger instance (by default logging.getLogger()) 
 - <b>`start_tasks`</b>:  True - starts socket/heartbeat asyncio tasks, False - no tasks  (this is useful in debugging / testing) 


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

<a href="https://github.com/alexveden/asyncfix/blob/main/asyncfix/connection.py#L181"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>method</kbd> `connect`

```python
connect()
```

Transport initialization method. 

---

<a href="https://github.com/alexveden/asyncfix/blob/main/asyncfix/connection.py#L188"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>method</kbd> `disconnect`

```python
disconnect(disconn_state: ConnectionState, logout_message: str = None)
```

Disconnect session and closes the socket. 



**Args:**
 
 - <b>`disconn_state`</b>:  connection state after disconnection 
 - <b>`logout_message`</b>:  if not None, sends Logout() message to peer with  (58=logout_message) 

---

<a href="https://github.com/alexveden/asyncfix/blob/main/asyncfix/connection.py#L345"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>method</kbd> `heartbeat_timer_task`

```python
heartbeat_timer_task()
```

Heartbeat watcher task. 

---

<a href="https://github.com/alexveden/asyncfix/blob/main/asyncfix/connection.py#L407"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>method</kbd> `on_connect`

```python
on_connect()
```

(AppEvent) Underlying socket connected. 

---

<a href="https://github.com/alexveden/asyncfix/blob/main/asyncfix/connection.py#L412"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>method</kbd> `on_disconnect`

```python
on_disconnect()
```

(AppEvent) Underlying socket disconnected. 

---

<a href="https://github.com/alexveden/asyncfix/blob/main/asyncfix/connection.py#L416"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>method</kbd> `on_logon`

```python
on_logon(is_healthy: bool)
```

(AppEvent) Logon(35=A) received from peer. 



**Args:**
 
 - <b>`is_healthy`</b>:  True - if connection_state is ACTIVE 

---

<a href="https://github.com/alexveden/asyncfix/blob/main/asyncfix/connection.py#L424"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>method</kbd> `on_logout`

```python
on_logout(msg: FIXMessage)
```

(AppEvent) Logout(35=5) received from peer. 



**Args:**
 
 - <b>`msg`</b>:  Logout(35=5) FIXMessage 

---

<a href="https://github.com/alexveden/asyncfix/blob/main/asyncfix/connection.py#L397"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>method</kbd> `on_message`

```python
on_message(msg: FIXMessage)
```

(AppEvent) Business message was received. 

Typically excludes session messages 



**Args:**
 
 - <b>`msg`</b>:  generic incoming FIXMessage 

---

<a href="https://github.com/alexveden/asyncfix/blob/main/asyncfix/connection.py#L432"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>method</kbd> `on_state_change`

```python
on_state_change(connection_state: ConnectionState)
```

(AppEvent) On ConnectionState change. 



**Args:**
 
 - <b>`connection_state`</b>:  new connection state 

---

<a href="https://github.com/alexveden/asyncfix/blob/main/asyncfix/connection.py#L384"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>method</kbd> `reset_seq_num`

```python
reset_seq_num()
```

Resets session and journal seq nums to 1. 

---

<a href="https://github.com/alexveden/asyncfix/blob/main/asyncfix/connection.py#L222"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>method</kbd> `send_msg`

```python
send_msg(msg: FIXMessage)
```

Sends message to the peer. 



**Args:**
 
 - <b>`msg`</b>:  fix message 



**Raises:**
 
 - <b>`FIXConnectionError`</b>:  raised if connection state does not allow sending 

---

<a href="https://github.com/alexveden/asyncfix/blob/main/asyncfix/connection.py#L277"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>method</kbd> `send_test_req`

```python
send_test_req()
```

Sends TestRequest(35=1) and sets TestReqID for expected response from peer. 



**Raises:**
 
 - <b>`FIXConnectionError`</b>:  if another TestRequest() is pending 

---

<a href="https://github.com/alexveden/asyncfix/blob/main/asyncfix/connection.py#L440"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>method</kbd> `should_replay`

```python
should_replay(historical_replay_msg: FIXMessage) → bool
```

(AppLevel) Checks if historical_replay_msg from Journaler should be replayed. 



**Args:**
 
 - <b>`historical_replay_msg`</b>:  message from Journaler log 

Returns: True - replay, False - msg skipped (replaced by SequenceReset(35=4)) 

---

<a href="https://github.com/alexveden/asyncfix/blob/main/asyncfix/connection.py#L290"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>method</kbd> `socket_read_task`

```python
socket_read_task()
```

Main socket reader task (decode raw messages and calls _process_message). 




---

_This file was automatically generated via [lazydocs](https://github.com/ml-tooling/lazydocs)._
