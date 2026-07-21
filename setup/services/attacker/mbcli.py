#!/usr/bin/env python3
"""Small Modbus/TCP utility provided on the challenge workstation."""

from __future__ import annotations

import argparse
import sys

from pyModbusTCP.client import ModbusClient


def offset(reference: int, kind: str) -> int:
    if kind == "holding" and reference >= 40001:
        return reference - 40001
    if kind == "input" and reference >= 30001:
        return reference - 30001
    return reference


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="Read and write authorized lab Modbus/TCP registers")
    sub = result.add_subparsers(dest="command", required=True)
    for name, help_text in (("read-holding", "read 4xxxx holding registers"), ("read-input", "read 3xxxx input registers")):
        cmd = sub.add_parser(name, help=help_text)
        cmd.add_argument("host")
        cmd.add_argument("reference", type=lambda value: int(value, 0))
        cmd.add_argument("count", type=int, nargs="?", default=1)
    identify = sub.add_parser("identify", help="read Modbus device-identification objects")
    identify.add_argument("host")
    write = sub.add_parser("write", help="write one 4xxxx holding register")
    write.add_argument("host")
    write.add_argument("reference", type=lambda value: int(value, 0))
    write.add_argument("value", type=lambda value: int(value, 0))
    result.add_argument("--port", type=int, default=502)
    return result


def main() -> int:
    args = parser().parse_args()
    modbus = ModbusClient(host=args.host, port=args.port, auto_open=True, auto_close=True, timeout=2.0)
    if args.command == "identify":
        basic = modbus.read_device_identification(read_code=1)
        regular = modbus.read_device_identification(read_code=2)
        if not basic and not regular:
            print("device identification failed or is unsupported", file=sys.stderr)
            return 1
        objects: dict[int, bytes] = {}
        if basic:
            objects.update(basic.objects_by_id)
        if regular:
            objects.update(regular.objects_by_id)
        names = {
            0: "vendor",
            1: "product_code",
            2: "revision",
            3: "vendor_url",
            4: "product_name",
            5: "model",
            6: "application",
        }
        for object_id, value in sorted(objects.items()):
            label = names.get(object_id, f"object_{object_id}")
            decoded = value.decode("utf-8", errors="replace") if isinstance(value, bytes) else str(value)
            if decoded:
                print(f"{label}: {decoded}")
        return 0
    if args.command == "read-holding":
        start = offset(args.reference, "holding")
        values = modbus.read_holding_registers(start, args.count)
        base = 40001
    elif args.command == "read-input":
        start = offset(args.reference, "input")
        values = modbus.read_input_registers(start, args.count)
        base = 30001
    else:
        start = offset(args.reference, "holding")
        if not 0 <= args.value <= 0xFFFF:
            print("value must fit in one unsigned 16-bit register", file=sys.stderr)
            return 2
        if not modbus.write_single_register(start, args.value):
            print("write failed or timed out", file=sys.stderr)
            return 1
        print(f"wrote {args.host}:{args.port} 4{start + 1:04d} (offset {start}) = {args.value} / 0x{args.value:04x}")
        return 0

    if values is None:
        print("read failed or timed out", file=sys.stderr)
        return 1
    for index, value in enumerate(values):
        register_offset = start + index
        print(f"{base + register_offset} (offset {register_offset:>2}) = {value:>5} / 0x{value:04x}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
