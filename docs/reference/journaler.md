<!-- markdownlint-disable -->

<a href="https://github.com/alexveden/asyncfix/blob/main/asyncfix/journaler.py#L0"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

# <kbd>module</kbd> `journaler`
Generic SQLite Journaler. 



---

<a href="https://github.com/alexveden/asyncfix/blob/main/asyncfix/journaler.py#L9"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>class</kbd> `Journaler`
Tracks FIX message history. 

<a href="https://github.com/alexveden/asyncfix/blob/main/asyncfix/journaler.py#L12"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>method</kbd> `__init__`

```python
__init__(filename=None)
```

Initialize SQLite Journaler. 



**Args:**
 
 - <b>`filename`</b>:  path to file, or None - to make in-memory journal 




---

<a href="https://github.com/alexveden/asyncfix/blob/main/asyncfix/journaler.py#L58"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>method</kbd> `create_or_load`

```python
create_or_load(target_comp_id, sender_comp_id) → FIXSession
```

Creates or loads new session with unique target_comp_id/sender_comp_id. 



**Args:**
 
 - <b>`target_comp_id`</b>:  session targetCompId 
 - <b>`sender_comp_id`</b>:  session senderCompId 



**Returns:**
 FIXSession 

---

<a href="https://github.com/alexveden/asyncfix/blob/main/asyncfix/journaler.py#L91"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>method</kbd> `find_seq_no`

```python
find_seq_no(msg: bytes) → int
```

Finds 34=<seqno> in serialized message. 



**Args:**
 
 - <b>`msg`</b>:  encoded fix message 



**Returns:**
 seq no value 



**Raises:**
 
 - <b>`FIXMessageError`</b>:  if not found or malformed message 

---

<a href="https://github.com/alexveden/asyncfix/blob/main/asyncfix/journaler.py#L239"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>method</kbd> `get_all_msgs`

```python
get_all_msgs(
    sessions: list[FIXSession] | None = None,
    direction: MessageDirection | None = None
)
```

Get all messages from the Journaler DB. 



**Args:**
 
 - <b>`sessions`</b>:  session filter (optional) 
 - <b>`direction`</b>:  direction filter (optional) 



**Returns:**
 list of tuples [(seq_no, enc_msg, direction, session_key), ...] 

---

<a href="https://github.com/alexveden/asyncfix/blob/main/asyncfix/journaler.py#L150"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>method</kbd> `persist_msg`

```python
persist_msg(msg: bytes, session: FIXSession, direction: MessageDirection)
```

Commits encoded fix message into DB. 



**Args:**
 
 - <b>`msg`</b>:  encoded fix message 
 - <b>`session`</b>:  target session 
 - <b>`direction`</b>:  message direction 



**Raises:**
 
 - <b>`DuplicateSeqNoError`</b>:  (critical) when DB already have such message seq_no 

---

<a href="https://github.com/alexveden/asyncfix/blob/main/asyncfix/journaler.py#L210"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>method</kbd> `recover_messages`

```python
recover_messages(
    session: FIXSession,
    direction: MessageDirection,
    start_seq_no: int | str,
    end_seq_no: int | str
) → list[bytes]
```

Loads messages with seq no range from DB. 



**Args:**
 
 - <b>`session`</b>:  target session 
 - <b>`direction`</b>:  message direction 
 - <b>`start_seq_no`</b>:  seq no from 
 - <b>`end_seq_no`</b>:  seq no to 



**Returns:**
 list of encoded FIX messages 

---

<a href="https://github.com/alexveden/asyncfix/blob/main/asyncfix/journaler.py#L188"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>method</kbd> `recover_msg`

```python
recover_msg(
    session: FIXSession,
    direction: MessageDirection,
    seq_no: int
) → bytes
```

Loads specific message from DB by seq no. 



**Args:**
 
 - <b>`session`</b>:  target session 
 - <b>`direction`</b>:  message direction 
 - <b>`seq_no`</b>:  target seq_no 



**Returns:**
 encoded message (bytes) 

---

<a href="https://github.com/alexveden/asyncfix/blob/main/asyncfix/journaler.py#L43"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>method</kbd> `sessions`

```python
sessions() → dict[tuple[str, str], FIXSession]
```

Loads all available sessions from journal. 

---

<a href="https://github.com/alexveden/asyncfix/blob/main/asyncfix/journaler.py#L111"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>method</kbd> `set_seq_num`

```python
set_seq_num(
    session: FIXSession,
    next_num_out: int | None = None,
    next_num_in: int | None = None
)
```

Sets journal and session seq num. 



**Args:**
 
 - <b>`session`</b>:  target session 
 - <b>`next_num_out`</b>:  new expected num out (optional) 
 - <b>`next_num_in`</b>:  new expected num in (optional) 




---

_This file was automatically generated via [lazydocs](https://github.com/ml-tooling/lazydocs)._
