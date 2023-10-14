<!-- markdownlint-disable -->

# API Overview

## Modules

- [`codec`](./codec.md#module-codec): FIX Message encoding / decoding module.
- [`connection`](./connection.md#module-connection): Abstract connection module.
- [`connection_client`](./connection_client.md#module-connection_client): FIX Initiator (client) connection.
- [`connection_server`](./connection_server.md#module-connection_server): Dummy FIX server module.
- [`errors`](./errors.md#module-errors): AsyncFIX errors module.
- [`fix_tester`](./fix_tester.md#module-fix_tester): FIX Protocol Unit Tester.
- [`fixtags`](./fixtags.md#module-fixtags): FIX Tags collection module.
- [`journaler`](./journaler.md#module-journaler): Generic SQLite Journaler.
- [`message`](./message.md#module-message): FIX message and containers module.
- [`msgtype`](./msgtype.md#module-msgtype): Message type module.
- [`protocol`](./protocol.md#module-protocol): AsyncFIX protocol package.
- [`protocol.common`](./protocol.common.md#module-protocolcommon): Common FIX protocol enums.
- [`protocol.order_single`](./protocol.order_single.md#module-protocolorder_single): Generic FIX Order single module.
- [`protocol.protocol_base`](./protocol.protocol_base.md#module-protocolprotocol_base): Base FIX protocol.
- [`protocol.protocol_fix44`](./protocol.protocol_fix44.md#module-protocolprotocol_fix44): FIX Protocol 4.4 module.
- [`protocol.schema`](./protocol.schema.md#module-protocolschema): FIX Schema validation module.
- [`session`](./session.md#module-session): FIXSession module.

## Classes

- [`codec.Codec`](./codec.md#class-codec): Encoding / decoding engine.
- [`connection.AsyncFIXConnection`](./connection.md#class-asyncfixconnection): AsyncFIX bidirectional connection.
- [`connection.ConnectionRole`](./connection.md#class-connectionrole): Role of the connection INITIATOR / ACCEPTOR.
- [`connection.ConnectionState`](./connection.md#class-connectionstate): Connection status enum.
- [`connection_client.AsyncFIXClient`](./connection_client.md#class-asyncfixclient): Generic FIX client.
- [`connection_server.AsyncFIXDummyServer`](./connection_server.md#class-asyncfixdummyserver): Simple server which supports only single connection (just for testing).
- [`errors.DuplicateSeqNoError`](./errors.md#class-duplicateseqnoerror): Journaler duplicated seq no written (critical error).
- [`errors.DuplicatedTagError`](./errors.md#class-duplicatedtagerror): Trying to set tag which is already exist.
- [`errors.EncodingError`](./errors.md#class-encodingerror): Codec encoding/decoding error.
- [`errors.FIXConnectionError`](./errors.md#class-fixconnectionerror): FIX connection or session error.
- [`errors.FIXError`](./errors.md#class-fixerror): Generic AsyncFIX error.
- [`errors.FIXMessageError`](./errors.md#class-fixmessageerror): FIXMessage related error.
- [`errors.RepeatingTagError`](./errors.md#class-repeatingtagerror): Tag was repeated after decoding, indicates mishandled fix group.
- [`errors.TagNotFoundError`](./errors.md#class-tagnotfounderror): Requested Tag not present in message.
- [`errors.UnmappedRepeatedGrpError`](./errors.md#class-unmappedrepeatedgrperror): Repeating group improperly set up by protocol.
- [`fix_tester.FIXTester`](./fix_tester.md#class-fixtester): FIX protocol tester.
- [`fixtags.FTag`](./fixtags.md#class-ftag): All tags enum.
- [`journaler.Journaler`](./journaler.md#class-journaler): Tracks FIX message history.
- [`message.FIXContainer`](./message.md#class-fixcontainer): Generic FIX container.
- [`message.FIXMessage`](./message.md#class-fixmessage): Generic FIXMessage.
- [`message.MessageDirection`](./message.md#class-messagedirection): Direction of the message INBOUND/OUTBOUND.
- [`msgtype.FMsg`](./msgtype.md#class-fmsg): FIXMessage type enum.
- [`common.FExecType`](./protocol.common.md#class-fexectype): FIX execution report ExecType.
- [`common.FOrdSide`](./protocol.common.md#class-fordside): FIX Order Side.
- [`common.FOrdStatus`](./protocol.common.md#class-fordstatus): FIX Order Status.
- [`common.FOrdType`](./protocol.common.md#class-fordtype): FIX Order Type.
- [`order_single.FIXNewOrderSingle`](./protocol.order_single.md#class-fixnewordersingle): Generic FIXNewOrderSingle wrapper.
- [`protocol_base.FIXProtocolBase`](./protocol.protocol_base.md#class-fixprotocolbase): Generic FIX protocol.
- [`protocol_fix44.FIXProtocol44`](./protocol.protocol_fix44.md#class-fixprotocol44): FIXProtocol 4.4 protocol definition class.
- [`schema.FIXSchema`](./protocol.schema.md#class-fixschema): FIX schema validator.
- [`schema.SchemaComponent`](./protocol.schema.md#class-schemacomponent): SchemaComponent container.
- [`schema.SchemaField`](./protocol.schema.md#class-schemafield): FIX Field schema.
- [`schema.SchemaGroup`](./protocol.schema.md#class-schemagroup): SchemaGroup container.
- [`schema.SchemaHeader`](./protocol.schema.md#class-schemaheader): SchemaHeader container.
- [`schema.SchemaMessage`](./protocol.schema.md#class-schemamessage): SchemaMessage container.
- [`schema.SchemaSet`](./protocol.schema.md#class-schemaset): Generic schema set (base for component/group).
- [`session.FIXSession`](./session.md#class-fixsession): Generic FIX Session container.

## Functions

- No functions


---

_This file was automatically generated via [lazydocs](https://github.com/ml-tooling/lazydocs)._
