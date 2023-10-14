<!-- markdownlint-disable -->

<a href="https://github.com/alexveden/asyncfix/blob/main/asyncfix/errors.py#L0"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

# <kbd>module</kbd> `errors`
AsyncFIX errors module. 



---

<a href="https://github.com/alexveden/asyncfix/blob/main/asyncfix/errors.py#L4"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>class</kbd> `FIXError`
Generic AsyncFIX error. 





---

<a href="https://github.com/alexveden/asyncfix/blob/main/asyncfix/errors.py#L8"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>class</kbd> `FIXMessageError`
FIXMessage related error. 





---

<a href="https://github.com/alexveden/asyncfix/blob/main/asyncfix/errors.py#L12"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>class</kbd> `FIXConnectionError`
FIX connection or session error. 





---

<a href="https://github.com/alexveden/asyncfix/blob/main/asyncfix/errors.py#L16"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>class</kbd> `DuplicateSeqNoError`
Journaler duplicated seq no written (critical error). 





---

<a href="https://github.com/alexveden/asyncfix/blob/main/asyncfix/errors.py#L20"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>class</kbd> `EncodingError`
Codec encoding/decoding error. 





---

<a href="https://github.com/alexveden/asyncfix/blob/main/asyncfix/errors.py#L24"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>class</kbd> `TagNotFoundError`
Requested Tag not present in message. 





---

<a href="https://github.com/alexveden/asyncfix/blob/main/asyncfix/errors.py#L28"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>class</kbd> `DuplicatedTagError`
Trying to set tag which is already exist. 





---

<a href="https://github.com/alexveden/asyncfix/blob/main/asyncfix/errors.py#L32"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>class</kbd> `RepeatingTagError`
Tag was repeated after decoding, indicates mishandled fix group. 





---

<a href="https://github.com/alexveden/asyncfix/blob/main/asyncfix/errors.py#L36"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>class</kbd> `UnmappedRepeatedGrpError`
Repeating group improperly set up by protocol. 







---

_This file was automatically generated via [lazydocs](https://github.com/ml-tooling/lazydocs)._
