# AsyncFIX - AsyncIO FIX Protocol Python Framework
![tests](https://github.com/alexveden/asyncfix/actions/workflows/build.yml/badge.svg)
![coverage](https://github.com/alexveden/asyncfix/blob/main/.github/coverage.svg)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

AsyncIO FIX protocol library for Python


## Highlights
- Pythonic way of dealing with FIX messages
- Schema validation
- Tools for unit testing client apps
- NewOrderSingle container / state management support
- Session management included (FIX journaling, session restoring, heartbeats, resets)
- FIX Tester - tool for FIX unit testing (schema validation, order management, protocol
message exchange)
- FIX 4.4 protocol implemented
- 100% unit test code coverage

## Installation
```
pip install asyncfix
```

## Getting started
* [Simple snippets](https://alexveden.github.io/asyncfix/examples/)
* [Client example](https://github.com/alexveden/asyncfix/tree/main/examples/client_example.py)
* [Full Documentation](https://alexveden.github.io/asyncfix/)

## Credits
This project initially intended to be a fork of [AIOPyFIX](https://github.com/maxtwen/AIOPyFix),
but things went too deep and too far. Hopefully, this project could help. Please, star this repo
if you are going to use this project.

## License
MIT 2023 Aleksandr Vedeneev
