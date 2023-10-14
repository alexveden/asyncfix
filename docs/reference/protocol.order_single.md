<!-- markdownlint-disable -->

<a href="https://github.com/alexveden/asyncfix/blob/main/asyncfix/protocol/order_single.py#L0"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

# <kbd>module</kbd> `protocol.order_single`
Generic FIX Order single module. 

**Global Variables**
---------------
- **nan**


---

<a href="https://github.com/alexveden/asyncfix/blob/main/asyncfix/protocol/order_single.py#L14"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>class</kbd> `FIXNewOrderSingle`
Generic FIXNewOrderSingle wrapper. 



**Attributes:**
 
 - <b>`clord_id`</b>:  current order ClOrdID 
 - <b>`orig_clord_id`</b>:  order OrigClOrdID (when canceling / replacing) 
 - <b>`order_id`</b>:  executed order id 
 - <b>`ticker`</b>:  user order ticker 
 - <b>`side`</b>:  order side 
 - <b>`price`</b>:  order price 
 - <b>`qty`</b>:  order quantity 
 - <b>`leaves_qty`</b>:  order remaining qty 
 - <b>`cum_qty`</b>:  order filled qty 
 - <b>`avg_px`</b>:  average fill price 
 - <b>`ord_type`</b>:  order type 
 - <b>`account`</b>:  order account 
 - <b>`status`</b>:  current order status 
 - <b>`target_price`</b>:  order target execution price 

<a href="https://github.com/alexveden/asyncfix/blob/main/asyncfix/protocol/order_single.py#L33"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>method</kbd> `__init__`

```python
__init__(
    clord_id: str,
    cl_ticker: str,
    side: FOrdSide | str,
    price: float,
    qty: float,
    ord_type: FOrdType | str = <FOrdType.LIMIT: '2'>,
    account: str | dict = '000000',
    target_price: float | None = None
)
```

Initialize order. 



**Args:**
 
 - <b>`clord_id`</b>:  root ClOrdID 
 - <b>`cl_ticker`</b>:  client ticker (can by any accepted by user's OMS) 
 - <b>`side`</b>:  order side 
 - <b>`price`</b>:  order initial price (current price, changes if replaced) 
 - <b>`qty`</b>:  order quantity 
 - <b>`ord_type`</b>:  order type 
 - <b>`account`</b>:  order account (optional) 
 - <b>`target_price`</b>:  order initial target execution price (useful for slippage) 


---

#### <kbd>property</kbd> clord_id_root

Current order ClOrdID root. 



---

<a href="https://github.com/alexveden/asyncfix/blob/main/asyncfix/protocol/order_single.py#L473"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>method</kbd> `can_cancel`

```python
can_cancel() → bool
```

Check if order can be canceled from its current state. 

---

<a href="https://github.com/alexveden/asyncfix/blob/main/asyncfix/protocol/order_single.py#L486"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>method</kbd> `can_replace`

```python
can_replace() → bool
```

Check if order can be replaced from its current state. 

---

<a href="https://github.com/alexveden/asyncfix/blob/main/asyncfix/protocol/order_single.py#L139"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>method</kbd> `cancel_req`

```python
cancel_req() → FIXMessage
```

Creates order cancel request. 



**Raises:**
 
 - <b>`FIXError`</b>:  if order can't be canceled 

---

<a href="https://github.com/alexveden/asyncfix/blob/main/asyncfix/protocol/order_single.py#L239"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>method</kbd> `change_status`

```python
change_status(
    status: FOrdStatus,
    fix_msg_type: FMsg,
    msg_exec_type: FExecType,
    msg_status: FOrdStatus,
    raise_on_err: bool = True
) → FOrdStatus | None
```

FIX Order State transition algo. 

:param status: current order status :param fix_msg_type: incoming/or requesting order type,  these are supported:  '8' - execution report,  '9' - Order Cancel reject,  'F' - Order cancel request (if possible to cancel current order)  'G' -  Order replace request (if possible to replace current order) :param msg_exec_type: (only for execution report), for other should be 0 :param msg_status: new fix msg order status, or required status :return: FOrdStatus if state transition is possible,  None - if transition is valid, but need to wait for a good state  raises FIXError - when transition is invalid 

---

<a href="https://github.com/alexveden/asyncfix/blob/main/asyncfix/protocol/order_single.py#L82"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>method</kbd> `clord_next`

```python
clord_next() → str
```

New ClOrdID for current order management. 

---

<a href="https://github.com/alexveden/asyncfix/blob/main/asyncfix/protocol/order_single.py#L87"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>method</kbd> `clord_root`

```python
clord_root(clord_id: str) → str
```

Order ClOrdID root, as given at initialization. 



**Args:**
 
 - <b>`clord_id`</b>:  current order one of the clord_next() 



**Returns:**
 string 

---

<a href="https://github.com/alexveden/asyncfix/blob/main/asyncfix/protocol/order_single.py#L108"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>method</kbd> `current_datetime`

```python
current_datetime()
```

Date for TransactTime field. 

---

<a href="https://github.com/alexveden/asyncfix/blob/main/asyncfix/protocol/order_single.py#L464"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>method</kbd> `is_finished`

```python
is_finished() → bool
```

Check if order is in terminal state (no subsequent changes expected). 

---

<a href="https://github.com/alexveden/asyncfix/blob/main/asyncfix/protocol/order_single.py#L113"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>method</kbd> `new_req`

```python
new_req() → FIXMessage
```

Creates NewOrderSingle message. 

---

<a href="https://github.com/alexveden/asyncfix/blob/main/asyncfix/protocol/order_single.py#L393"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>method</kbd> `process_cancel_rej_report`

```python
process_cancel_rej_report(m: FIXMessage) → bool
```

Processes incoming cancel reject report message. 

---

<a href="https://github.com/alexveden/asyncfix/blob/main/asyncfix/protocol/order_single.py#L415"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>method</kbd> `process_execution_report`

```python
process_execution_report(m: FIXMessage) → bool
```

Processes incoming execution report for an order. 



**Raises:**
 
 - <b>`FIXError`</b>:  if ClOrdID mismatch 

---

<a href="https://github.com/alexveden/asyncfix/blob/main/asyncfix/protocol/order_single.py#L164"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>method</kbd> `replace_req`

```python
replace_req(price: float = nan, qty: float = nan) → FIXMessage
```

Creates order replace request. 



**Args:**
 
 - <b>`price`</b>:  alternative price 
 - <b>`qty`</b>:  alternative qty 



**Returns:**
 message 



**Raises:**
 
 - <b>`FIXError`</b>:  if order can't be replaced or price/qty unchanged 

---

<a href="https://github.com/alexveden/asyncfix/blob/main/asyncfix/protocol/order_single.py#L215"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>method</kbd> `set_account`

```python
set_account(ord_msg: FIXMessage)
```

Set account definition (override this in child). 



**Args:**
 
 - <b>`ord_msg`</b>:  new or replaced order 

---

<a href="https://github.com/alexveden/asyncfix/blob/main/asyncfix/protocol/order_single.py#L205"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>method</kbd> `set_instrument`

```python
set_instrument(ord_msg: FIXMessage)
```

Set order instrument definition (override this in child). 



**Args:**
 
 - <b>`ord_msg`</b>:  new or replaced order 

---

<a href="https://github.com/alexveden/asyncfix/blob/main/asyncfix/protocol/order_single.py#L225"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>method</kbd> `set_price_qty`

```python
set_price_qty(ord_msg: FIXMessage, price: float, qty: float)
```

Set order price and qty definition (override this in child). 

This method handles custom price/qty rounding/decimal formatting, or maybe conditional presence of two fields based on order type 



**Args:**
 
 - <b>`ord_msg`</b>:  new or replaced order 
 - <b>`price`</b>:  new order price (unformatted / unrounded) 
 - <b>`qty`</b>:  new order qty (unformatted / unrounded) 




---

_This file was automatically generated via [lazydocs](https://github.com/ml-tooling/lazydocs)._
