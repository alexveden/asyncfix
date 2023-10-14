<!-- markdownlint-disable -->

<a href="https://github.com/alexveden/asyncfix/blob/main/asyncfix/session.py#L0"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

# <kbd>module</kbd> `session`
FIXSession module. 



---

<a href="https://github.com/alexveden/asyncfix/blob/main/asyncfix/session.py#L5"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>class</kbd> `FIXSession`
Generic FIX Session container. 



**Attributes:**
 
 - <b>`key`</b>:  session DB id 
 - <b>`sender_comp_id`</b>:  session sender 
 - <b>`target_comp_id`</b>:  session target 
 - <b>`next_num_out`</b>:  next expected seq num out 
 - <b>`next_num_in`</b>:  next expected seq num in 

<a href="https://github.com/alexveden/asyncfix/blob/main/asyncfix/session.py#L15"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>method</kbd> `__init__`

```python
__init__(key, target_comp_id: str, sender_comp_id: str)
```

Initialize session. 



**Args:**
 
 - <b>`key`</b>:  session DB id 
 - <b>`target_comp_id`</b>:  session target 
 - <b>`sender_comp_id`</b>:  session sender 




---

<a href="https://github.com/alexveden/asyncfix/blob/main/asyncfix/session.py#L74"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>method</kbd> `allocate_next_num_out`

```python
allocate_next_num_out()
```

Increments next_num_out counter. 

---

<a href="https://github.com/alexveden/asyncfix/blob/main/asyncfix/session.py#L80"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>method</kbd> `set_next_num_in`

```python
set_next_num_in(msg: FIXMessage) → int
```

Sets next_num_in based on incoming FIXMessage. 



**Args:**
 
 - <b>`msg`</b>:  incoming message 



**Returns:**
 
    - if OK - current message seq_no 
    - if ERROR - 0 or -1 

---

<a href="https://github.com/alexveden/asyncfix/blob/main/asyncfix/session.py#L59"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>method</kbd> `validate_comp_ids`

```python
validate_comp_ids(target_comp_id: str, sender_comp_id: str) → bool
```

Ensure target_comp_id/sender_comp_id match. 



**Args:**
 
 - <b>`target_comp_id`</b>:  incoming target_comp_id 
 - <b>`sender_comp_id`</b>:  incoming sender_comp_id 



**Returns:**
 bool 




---

_This file was automatically generated via [lazydocs](https://github.com/ml-tooling/lazydocs)._
