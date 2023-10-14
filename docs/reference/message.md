<!-- markdownlint-disable -->

<a href="https://github.com/alexveden/asyncfix/blob/main/asyncfix/message.py#L0"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

# <kbd>module</kbd> `message`
FIX message and containers module. 



---

<a href="https://github.com/alexveden/asyncfix/blob/main/asyncfix/message.py#L25"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>class</kbd> `MessageDirection`
Direction of the message INBOUND/OUTBOUND. 





---

<a href="https://github.com/alexveden/asyncfix/blob/main/asyncfix/message.py#L48"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>class</kbd> `FIXContainer`
Generic FIX container. 



**Attributes:**
 
 - <b>`tags`</b>:  fix tags of the container 

<a href="https://github.com/alexveden/asyncfix/blob/main/asyncfix/message.py#L55"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>method</kbd> `__init__`

```python
__init__(
    tags: 'dict[str | int, [str, float, int, list[dict | FIXContainer]]]' = None
)
```

Initialize. 



**Examples:**
  m = FIXContainer({  1: "account",  FTag.ClOrdID: 'my-clord',  FTag.NoAllocs: [{312: 'grp1'}, {312: 'grp2'}],  }) 



**Args:**
 
 - <b>`tags`</b>:  add tags at initialization time (all keys / values converted to str!) 




---

<a href="https://github.com/alexveden/asyncfix/blob/main/asyncfix/message.py#L160"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>method</kbd> `add_group`

```python
add_group(tag: 'str | int', group: 'FIXContainer | dict', index: 'int' = -1)
```

Add repeating group item to fix message. 



**Args:**
 
 - <b>`tag`</b>:  tag of repeating group, typically contains `No`, e.g. FTag.NoAllocs 
 - <b>`group`</b>:  group item (another FIXContainer) or dict[tag: value] 
 - <b>`index`</b>:  where to insert new value, default: append 



**Raises:**
 
 - <b>`FIXMessageError`</b>:  incorrect group type/value 

---

<a href="https://github.com/alexveden/asyncfix/blob/main/asyncfix/message.py#L111"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>method</kbd> `get`

```python
get(
    tag: 'str | int | FTag',
    default=<class 'asyncfix.errors.TagNotFoundError'>
) → str
```

Get tag value. 



**Args:**
 
 - <b>`tag`</b>:  tag to get 
 - <b>`default`</b>:  default value or raises TagNotFoundError 



**Returns:**
 string value of the tag 



**Raises:**
 
 - <b>`FIXMessageError`</b>:  trying to get FIX message group by tag, use get_group() 
 - <b>`RepeatingTagError`</b>:  tag was repeated in decoded message, probably msg group 
 - <b>`TagNotFoundError`</b>:  tag was not found in message 

---

<a href="https://github.com/alexveden/asyncfix/blob/main/asyncfix/message.py#L264"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>method</kbd> `get_group_by_index`

```python
get_group_by_index(tag: 'str | int', index: 'int') → FIXContainer
```

Get repeating group item by index. 



**Args:**
 
 - <b>`tag`</b>:  repeating group tag 
 - <b>`index`</b>:  repeating group item index 



**Returns:**
 FIXContainer 



**Raises:**
 
 - <b>`TagNotFoundError`</b>:  tag not found 

---

<a href="https://github.com/alexveden/asyncfix/blob/main/asyncfix/message.py#L239"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>method</kbd> `get_group_by_tag`

```python
get_group_by_tag(
    tag: 'str | int',
    gtag: 'str | int',
    gvalue: 'str'
) → FIXContainer
```

Get repeating group item by internal group tag value. 



**Args:**
 
 - <b>`tag`</b>:  repeating group tag 
 - <b>`gtag`</b>:  inside group tag to filter by 
 - <b>`gvalue`</b>:  expected group tag value 



**Returns:**
 FIXContainer of repeating group item 



**Raises:**
 
 - <b>`TagNotFoundError`</b>:  tag not found 

---

<a href="https://github.com/alexveden/asyncfix/blob/main/asyncfix/message.py#L215"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>method</kbd> `get_group_list`

```python
get_group_list(tag: 'str | int') → list[FIXContainer]
```

Get all repeating groups of a tag. 



**Args:**
 
 - <b>`tag`</b>:  target tag 



**Returns:**
 list of repeating FIXContainers 



**Raises:**
 
 - <b>`UnmappedRepeatedGrpError`</b>:  repeating group is not handled by protocol class 
 - <b>`TagNotFoundError`</b>:  tag not found 

---

<a href="https://github.com/alexveden/asyncfix/blob/main/asyncfix/message.py#L140"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>method</kbd> `is_group`

```python
is_group(tag: 'str | int') → bool | None
```

Check if tag is repeating group. 



**Args:**
 
 - <b>`tag`</b>:  tag to check 



**Returns:**
 None - if not found True - if repeating group False - simple tag 

---

<a href="https://github.com/alexveden/asyncfix/blob/main/asyncfix/message.py#L308"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>method</kbd> `items`

```python
items()
```

All tags items iterator. 

---

<a href="https://github.com/alexveden/asyncfix/blob/main/asyncfix/message.py#L286"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>method</kbd> `query`

```python
query(*tags: 'tuple[FTag | str | int]') → dict[FTag | str, str]
```

Request multiple tags from FIXMessage as dictionary. 



**Args:**
 
 - <b>`*tags`</b>:  tags var arguments 



**Returns:**
 
 - <b>`dict {tag`</b>:  value, ...} 

---

<a href="https://github.com/alexveden/asyncfix/blob/main/asyncfix/message.py#L80"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>method</kbd> `set`

```python
set(tag: 'str | int', value, replace: 'bool' = False)
```

Set tag value. 



**Args:**
 
 - <b>`tag`</b>:  tag to set 
 - <b>`value`</b>:  value to set (converted to str!) 
 - <b>`replace`</b>:  set True - to intentionally rewrite existing tag 



**Raises:**
 
 - <b>`DuplicatedTagError`</b>:  when trying to set existing tag 
 - <b>`FIXMessageError`</b>:  tag value is not convertible to int 

---

<a href="https://github.com/alexveden/asyncfix/blob/main/asyncfix/message.py#L186"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>method</kbd> `set_group`

```python
set_group(tag: 'str | int', groups: 'list[dict, FIXContainer]')
```

Set repeating groups of the message. 



**Args:**
 
 - <b>`tag`</b>:  tag of repeating group, typically contains `No`, e.g. FTag.NoAllocs 
 - <b>`groups`</b>:  group items list of  (another FIXContainer) or dict[tag: value] 



**Raises:**
 
 - <b>`DuplicatedTagError`</b>:  group with the same tag already exists 
 - <b>`FIXMessageError`</b>:  incorrect group type/value 


---

<a href="https://github.com/alexveden/asyncfix/blob/main/asyncfix/message.py#L391"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>class</kbd> `FIXMessage`
Generic FIXMessage. 

<a href="https://github.com/alexveden/asyncfix/blob/main/asyncfix/message.py#L393"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>method</kbd> `__init__`

```python
__init__(
    msg_type: 'str | FMsg',
    tags: 'dict[str | int, [str, float, int]]' = None
)
```

Initialize. 



**Args:**
 
 - <b>`msg_type`</b>:  message type, must comply with FIXTag=35 
 - <b>`tags`</b>:  initial tags values 


---

#### <kbd>property</kbd> msg_type

Message type. 



---

<a href="https://github.com/alexveden/asyncfix/blob/main/asyncfix/message.py#L160"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>method</kbd> `add_group`

```python
add_group(tag: 'str | int', group: 'FIXContainer | dict', index: 'int' = -1)
```

Add repeating group item to fix message. 



**Args:**
 
 - <b>`tag`</b>:  tag of repeating group, typically contains `No`, e.g. FTag.NoAllocs 
 - <b>`group`</b>:  group item (another FIXContainer) or dict[tag: value] 
 - <b>`index`</b>:  where to insert new value, default: append 



**Raises:**
 
 - <b>`FIXMessageError`</b>:  incorrect group type/value 

---

<a href="https://github.com/alexveden/asyncfix/blob/main/asyncfix/message.py#L111"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>method</kbd> `get`

```python
get(
    tag: 'str | int | FTag',
    default=<class 'asyncfix.errors.TagNotFoundError'>
) → str
```

Get tag value. 



**Args:**
 
 - <b>`tag`</b>:  tag to get 
 - <b>`default`</b>:  default value or raises TagNotFoundError 



**Returns:**
 string value of the tag 



**Raises:**
 
 - <b>`FIXMessageError`</b>:  trying to get FIX message group by tag, use get_group() 
 - <b>`RepeatingTagError`</b>:  tag was repeated in decoded message, probably msg group 
 - <b>`TagNotFoundError`</b>:  tag was not found in message 

---

<a href="https://github.com/alexveden/asyncfix/blob/main/asyncfix/message.py#L264"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>method</kbd> `get_group_by_index`

```python
get_group_by_index(tag: 'str | int', index: 'int') → FIXContainer
```

Get repeating group item by index. 



**Args:**
 
 - <b>`tag`</b>:  repeating group tag 
 - <b>`index`</b>:  repeating group item index 



**Returns:**
 FIXContainer 



**Raises:**
 
 - <b>`TagNotFoundError`</b>:  tag not found 

---

<a href="https://github.com/alexveden/asyncfix/blob/main/asyncfix/message.py#L239"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>method</kbd> `get_group_by_tag`

```python
get_group_by_tag(
    tag: 'str | int',
    gtag: 'str | int',
    gvalue: 'str'
) → FIXContainer
```

Get repeating group item by internal group tag value. 



**Args:**
 
 - <b>`tag`</b>:  repeating group tag 
 - <b>`gtag`</b>:  inside group tag to filter by 
 - <b>`gvalue`</b>:  expected group tag value 



**Returns:**
 FIXContainer of repeating group item 



**Raises:**
 
 - <b>`TagNotFoundError`</b>:  tag not found 

---

<a href="https://github.com/alexveden/asyncfix/blob/main/asyncfix/message.py#L215"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>method</kbd> `get_group_list`

```python
get_group_list(tag: 'str | int') → list[FIXContainer]
```

Get all repeating groups of a tag. 



**Args:**
 
 - <b>`tag`</b>:  target tag 



**Returns:**
 list of repeating FIXContainers 



**Raises:**
 
 - <b>`UnmappedRepeatedGrpError`</b>:  repeating group is not handled by protocol class 
 - <b>`TagNotFoundError`</b>:  tag not found 

---

<a href="https://github.com/alexveden/asyncfix/blob/main/asyncfix/message.py#L140"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>method</kbd> `is_group`

```python
is_group(tag: 'str | int') → bool | None
```

Check if tag is repeating group. 



**Args:**
 
 - <b>`tag`</b>:  tag to check 



**Returns:**
 None - if not found True - if repeating group False - simple tag 

---

<a href="https://github.com/alexveden/asyncfix/blob/main/asyncfix/message.py#L308"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>method</kbd> `items`

```python
items()
```

All tags items iterator. 

---

<a href="https://github.com/alexveden/asyncfix/blob/main/asyncfix/message.py#L286"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>method</kbd> `query`

```python
query(*tags: 'tuple[FTag | str | int]') → dict[FTag | str, str]
```

Request multiple tags from FIXMessage as dictionary. 



**Args:**
 
 - <b>`*tags`</b>:  tags var arguments 



**Returns:**
 
 - <b>`dict {tag`</b>:  value, ...} 

---

<a href="https://github.com/alexveden/asyncfix/blob/main/asyncfix/message.py#L80"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>method</kbd> `set`

```python
set(tag: 'str | int', value, replace: 'bool' = False)
```

Set tag value. 



**Args:**
 
 - <b>`tag`</b>:  tag to set 
 - <b>`value`</b>:  value to set (converted to str!) 
 - <b>`replace`</b>:  set True - to intentionally rewrite existing tag 



**Raises:**
 
 - <b>`DuplicatedTagError`</b>:  when trying to set existing tag 
 - <b>`FIXMessageError`</b>:  tag value is not convertible to int 

---

<a href="https://github.com/alexveden/asyncfix/blob/main/asyncfix/message.py#L186"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>method</kbd> `set_group`

```python
set_group(tag: 'str | int', groups: 'list[dict, FIXContainer]')
```

Set repeating groups of the message. 



**Args:**
 
 - <b>`tag`</b>:  tag of repeating group, typically contains `No`, e.g. FTag.NoAllocs 
 - <b>`groups`</b>:  group items list of  (another FIXContainer) or dict[tag: value] 



**Raises:**
 
 - <b>`DuplicatedTagError`</b>:  group with the same tag already exists 
 - <b>`FIXMessageError`</b>:  incorrect group type/value 




---

_This file was automatically generated via [lazydocs](https://github.com/ml-tooling/lazydocs)._
