<!-- markdownlint-disable -->

<a href="https://github.com/alexveden/asyncfix/blob/main/asyncfix/protocol/schema.py#L0"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

# <kbd>module</kbd> `protocol.schema`
FIX Schema validation module. 



---

<a href="https://github.com/alexveden/asyncfix/blob/main/asyncfix/protocol/schema.py#L16"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>class</kbd> `SchemaField`
FIX Field schema. 

<a href="https://github.com/alexveden/asyncfix/blob/main/<string>"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>method</kbd> `__init__`

```python
__init__(
    tag: 'str',
    name: 'str',
    ftype: 'str',
    values: 'dict[str, str]' = <factory>
) → None
```








---

<a href="https://github.com/alexveden/asyncfix/blob/main/asyncfix/protocol/schema.py#L41"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>method</kbd> `validate_value`

```python
validate_value(value: 'str') → bool
```

Validate tag value based on schema settings. 



**Args:**
 
 - <b>`value`</b>:  tag value 

Returns: True - if passed 



**Raises:**
 
 - <b>`FIXMessageError`</b>:  raised if validation failed 


---

<a href="https://github.com/alexveden/asyncfix/blob/main/asyncfix/protocol/schema.py#L216"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>class</kbd> `SchemaSet`
Generic schema set (base for component/group). 



**Attributes:**
 
 - <b>`name`</b>:  schema name 
 - <b>`field`</b>:  schema field 
 - <b>`members`</b>:  members 
 - <b>`required`</b>:  required flag 

<a href="https://github.com/alexveden/asyncfix/blob/main/asyncfix/protocol/schema.py#L226"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>method</kbd> `__init__`

```python
__init__(name: 'str', field: 'SchemaField | None' = None)
```

Initialize. 



**Args:**
 
 - <b>`name`</b>:  name of abstract set 
 - <b>`field`</b>:  field of abstract set 



**Raises:**
 
 - <b>`ValueError`</b>:  if not NUMINGROUP type or similar tag name 


---

#### <kbd>property</kbd> tag

Tag number of SchemaField. 



**Returns:**
  tag 



**Raises:**
 
 - <b>`ValueError`</b>:  raised then tag is not single field 



---

<a href="https://github.com/alexveden/asyncfix/blob/main/asyncfix/protocol/schema.py#L270"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>method</kbd> `add`

```python
add(field_or_set: 'SchemaField | SchemaSet', required: 'bool')
```

Add SchemaSet member. 



**Args:**
 
 - <b>`field_or_set`</b>:  field or SchemaSet 
 - <b>`required`</b>:  required tag flag 



**Raises:**
 
 - <b>`ValueError`</b>:  unsupported field_or_set value 

---

<a href="https://github.com/alexveden/asyncfix/blob/main/asyncfix/protocol/schema.py#L266"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>method</kbd> `keys`

```python
keys() → list[str]
```

List of field names. 

---

<a href="https://github.com/alexveden/asyncfix/blob/main/asyncfix/protocol/schema.py#L290"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>method</kbd> `merge`

```python
merge(comp: 'SchemaSet')
```

Merge SchemaSet with another. 



**Args:**
 
 - <b>`comp`</b>:  SchemaSet 


---

<a href="https://github.com/alexveden/asyncfix/blob/main/asyncfix/protocol/schema.py#L352"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>class</kbd> `SchemaGroup`
SchemaGroup container. 



**Attributes:**
  field_required: 

<a href="https://github.com/alexveden/asyncfix/blob/main/asyncfix/protocol/schema.py#L359"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>method</kbd> `__init__`

```python
__init__(field: 'SchemaField', required: 'bool')
```

Initialize. 



**Args:**
 
 - <b>`field`</b>:  SchemaField of group 
 - <b>`required`</b>:  required flag 


---

#### <kbd>property</kbd> tag

Tag number of SchemaField. 



**Returns:**
  tag 



**Raises:**
 
 - <b>`ValueError`</b>:  raised then tag is not single field 



---

<a href="https://github.com/alexveden/asyncfix/blob/main/asyncfix/protocol/schema.py#L270"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>method</kbd> `add`

```python
add(field_or_set: 'SchemaField | SchemaSet', required: 'bool')
```

Add SchemaSet member. 



**Args:**
 
 - <b>`field_or_set`</b>:  field or SchemaSet 
 - <b>`required`</b>:  required tag flag 



**Raises:**
 
 - <b>`ValueError`</b>:  unsupported field_or_set value 

---

<a href="https://github.com/alexveden/asyncfix/blob/main/asyncfix/protocol/schema.py#L266"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>method</kbd> `keys`

```python
keys() → list[str]
```

List of field names. 

---

<a href="https://github.com/alexveden/asyncfix/blob/main/asyncfix/protocol/schema.py#L290"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>method</kbd> `merge`

```python
merge(comp: 'SchemaSet')
```

Merge SchemaSet with another. 



**Args:**
 
 - <b>`comp`</b>:  SchemaSet 

---

<a href="https://github.com/alexveden/asyncfix/blob/main/asyncfix/protocol/schema.py#L369"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>method</kbd> `validate_group`

```python
validate_group(groups: 'list[FIXContainer]')
```

Validate values of all tags in group. 



**Args:**
 
 - <b>`groups`</b>:  list of repeating group items 



**Raises:**
 
 - <b>`FIXMessageError`</b>:  validation failed 


---

<a href="https://github.com/alexveden/asyncfix/blob/main/asyncfix/protocol/schema.py#L434"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>class</kbd> `SchemaComponent`
SchemaComponent container. 

<a href="https://github.com/alexveden/asyncfix/blob/main/asyncfix/protocol/schema.py#L437"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>method</kbd> `__init__`

```python
__init__(name: 'str')
```

Initialize. 



**Args:**
 
 - <b>`name`</b>:  component name 


---

#### <kbd>property</kbd> tag

Tag number of SchemaField. 



**Returns:**
  tag 



**Raises:**
 
 - <b>`ValueError`</b>:  raised then tag is not single field 



---

<a href="https://github.com/alexveden/asyncfix/blob/main/asyncfix/protocol/schema.py#L270"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>method</kbd> `add`

```python
add(field_or_set: 'SchemaField | SchemaSet', required: 'bool')
```

Add SchemaSet member. 



**Args:**
 
 - <b>`field_or_set`</b>:  field or SchemaSet 
 - <b>`required`</b>:  required tag flag 



**Raises:**
 
 - <b>`ValueError`</b>:  unsupported field_or_set value 

---

<a href="https://github.com/alexveden/asyncfix/blob/main/asyncfix/protocol/schema.py#L266"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>method</kbd> `keys`

```python
keys() → list[str]
```

List of field names. 

---

<a href="https://github.com/alexveden/asyncfix/blob/main/asyncfix/protocol/schema.py#L290"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>method</kbd> `merge`

```python
merge(comp: 'SchemaSet')
```

Merge SchemaSet with another. 



**Args:**
 
 - <b>`comp`</b>:  SchemaSet 


---

<a href="https://github.com/alexveden/asyncfix/blob/main/asyncfix/protocol/schema.py#L446"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>class</kbd> `SchemaHeader`
SchemaHeader container. 

<a href="https://github.com/alexveden/asyncfix/blob/main/asyncfix/protocol/schema.py#L449"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>method</kbd> `__init__`

```python
__init__()
```

Initialize header. 


---

#### <kbd>property</kbd> tag

Tag number of SchemaField. 



**Returns:**
  tag 



**Raises:**
 
 - <b>`ValueError`</b>:  raised then tag is not single field 



---

<a href="https://github.com/alexveden/asyncfix/blob/main/asyncfix/protocol/schema.py#L270"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>method</kbd> `add`

```python
add(field_or_set: 'SchemaField | SchemaSet', required: 'bool')
```

Add SchemaSet member. 



**Args:**
 
 - <b>`field_or_set`</b>:  field or SchemaSet 
 - <b>`required`</b>:  required tag flag 



**Raises:**
 
 - <b>`ValueError`</b>:  unsupported field_or_set value 

---

<a href="https://github.com/alexveden/asyncfix/blob/main/asyncfix/protocol/schema.py#L266"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>method</kbd> `keys`

```python
keys() → list[str]
```

List of field names. 

---

<a href="https://github.com/alexveden/asyncfix/blob/main/asyncfix/protocol/schema.py#L290"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>method</kbd> `merge`

```python
merge(comp: 'SchemaSet')
```

Merge SchemaSet with another. 



**Args:**
 
 - <b>`comp`</b>:  SchemaSet 


---

<a href="https://github.com/alexveden/asyncfix/blob/main/asyncfix/protocol/schema.py#L454"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>class</kbd> `SchemaMessage`
SchemaMessage container. 



**Attributes:**
 
 - <b>`msg_type`</b>:  msg_type value 
 - <b>`msg_cat`</b>:  message category 

<a href="https://github.com/alexveden/asyncfix/blob/main/asyncfix/protocol/schema.py#L462"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>method</kbd> `__init__`

```python
__init__(name: 'str', msg_type: 'str', msg_cat: 'str')
```

Initialize. 



**Args:**
 
 - <b>`name`</b>:  message name 
 - <b>`msg_type`</b>:  message type 
 - <b>`msg_cat`</b>:  message category 


---

#### <kbd>property</kbd> tag

Tag number of SchemaField. 



**Returns:**
  tag 



**Raises:**
 
 - <b>`ValueError`</b>:  raised then tag is not single field 



---

<a href="https://github.com/alexveden/asyncfix/blob/main/asyncfix/protocol/schema.py#L270"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>method</kbd> `add`

```python
add(field_or_set: 'SchemaField | SchemaSet', required: 'bool')
```

Add SchemaSet member. 



**Args:**
 
 - <b>`field_or_set`</b>:  field or SchemaSet 
 - <b>`required`</b>:  required tag flag 



**Raises:**
 
 - <b>`ValueError`</b>:  unsupported field_or_set value 

---

<a href="https://github.com/alexveden/asyncfix/blob/main/asyncfix/protocol/schema.py#L266"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>method</kbd> `keys`

```python
keys() → list[str]
```

List of field names. 

---

<a href="https://github.com/alexveden/asyncfix/blob/main/asyncfix/protocol/schema.py#L290"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>method</kbd> `merge`

```python
merge(comp: 'SchemaSet')
```

Merge SchemaSet with another. 



**Args:**
 
 - <b>`comp`</b>:  SchemaSet 


---

<a href="https://github.com/alexveden/asyncfix/blob/main/asyncfix/protocol/schema.py#L481"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>class</kbd> `FIXSchema`
FIX schema validator. 

<a href="https://github.com/alexveden/asyncfix/blob/main/asyncfix/protocol/schema.py#L484"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>method</kbd> `__init__`

```python
__init__(xml_or_path: 'ElementTree | str')
```

Initialize. 



**Args:**
 
 - <b>`xml_or_path`</b>:  path to xml or xml.etree.ElementTree 



**Raises:**
 ValueError: 




---

<a href="https://github.com/alexveden/asyncfix/blob/main/asyncfix/protocol/schema.py#L664"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>method</kbd> `validate`

```python
validate(msg: 'FIXMessage') → bool
```

Validates generic FIXMessage based on schema. 



**Args:**
 
 - <b>`msg`</b>:  generic FIXMessage 



**Returns:**
 True - if ok 



**Raises:**
 
 - <b>`FIXMessageError`</b>:  raises on invalid message 




---

_This file was automatically generated via [lazydocs](https://github.com/ml-tooling/lazydocs)._
