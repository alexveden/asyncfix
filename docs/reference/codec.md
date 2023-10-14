<!-- markdownlint-disable -->

<a href="https://github.com/alexveden/asyncfix/blob/main/asyncfix/codec.py#L0"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

# <kbd>module</kbd> `codec`
FIX Message encoding / decoding module. 



---

<a href="https://github.com/alexveden/asyncfix/blob/main/asyncfix/codec.py#L20"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>class</kbd> `Codec`
Encoding / decoding engine. 



**Attributes:**
 
 - <b>`protocol`</b>:  FIX protocol 
 - <b>`SOH`</b>:  encoded message separator 

<a href="https://github.com/alexveden/asyncfix/blob/main/asyncfix/codec.py#L28"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>method</kbd> `__init__`

```python
__init__(protocol: FIXProtocolBase)
```

Codec init. 



**Args:**
 
 - <b>`protocol`</b>:  FIX protocol used in encoding/decoding 




---

<a href="https://github.com/alexveden/asyncfix/blob/main/asyncfix/codec.py#L37"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>method</kbd> `current_datetime`

```python
current_datetime() → str
```

FIX complaint date-time string (UTC now). 

---

<a href="https://github.com/alexveden/asyncfix/blob/main/asyncfix/codec.py#L136"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>method</kbd> `decode`

```python
decode(
    rawmsg: bytes,
    silent: bool = True
) → tuple[FIXMessage | None, int, bytes | None]
```

Decodes message from socket. 



**Args:**
 
 - <b>`rawmsg`</b>:  message bytes 
 - <b>`silent`</b>:  no errors raised, returns non 



**Returns:**
 if OK - (FIXMessage, bytes_processed, valid_raw_msg_bytes) if ERR - (None, n_bytes_skip, None) 

---

<a href="https://github.com/alexveden/asyncfix/blob/main/asyncfix/codec.py#L52"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>method</kbd> `encode`

```python
encode(msg: FIXMessage, session: FIXSession, raw_seq_num: bool = False) → str
```

Encodes FIXMessage into serialized message. 



**Args:**
 
 - <b>`msg`</b>:  generic FIXMessage 
 - <b>`session`</b>:  current session (for seq num) 
 - <b>`raw_seq_num`</b>:  if True - uses MsgSeqNum from `msg` 



**Returns:**
 encoded message (string) 



**Raises:**
 
 - <b>`EncodingError`</b>:  when failed MsgSeqNum conditions for some types of messages 




---

_This file was automatically generated via [lazydocs](https://github.com/ml-tooling/lazydocs)._
