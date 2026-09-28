# soc-smp

Symmetric multiprocessor reference SoC: two cores sharing one memory.

![maturity](https://img.shields.io/badge/maturity-planned-lightgrey) ![license](https://img.shields.io/badge/license-MIT%20OR%20Apache--2.0%20OR%20MulanPSL--2.0-blue)

Part of the [Tape-Out](https://github.com/Tape-Out) IP library: Bluespec IP over the
bus-neutral contracts in [`hwcore`](https://github.com/Tape-Out/hwcore), assembled by
[`xirang`](https://github.com/Tape-Out/xirang). Maturity runs `planned` -> `simulated` ->
`fpga-proven` -> `asic-ready` -> `silicon-proven`.

## Status

Assembled and tested end to end in CI; the badge stays at `planned` while the assembler is being reworked.

| Part | Repository | Configuration |
|:--:|:--:|:--:|
| cores | [`rvcore`](https://github.com/Tape-Out/rvcore) ×2 | RV32IM, machine mode only |
| memory | [`sram`](https://github.com/Tape-Out/sram) | 1024 words (4 KiB) at `0x8000_0000`, shared |
| interrupts | [`aclint`](https://github.com/Tape-Out/aclint) · [`plic`](https://github.com/Tape-Out/plic) | two harts · 8 sources, one context per core |
| inter-core | [`mbox`](https://github.com/Tape-Out/mbox) | mailboxes and 32 spinlocks |
| console | [`uart`](https://github.com/Tape-Out/uart) | at `0x1000_1000` |

The four ports of the two cores share one switch, round-robin. There are no caches, so the memory is coherent by construction; `rvcore` has no atomic instructions, so mutual exclusion goes through `mbox`'s spinlocks.

## License

任选其一：

- [MIT](LICENSE-MIT)
- [Apache 2.0](LICENSE-APACHE)
- [木兰宽松许可证 第2版](LICENSE-MULAN)

`SPDX-License-Identifier: MIT OR Apache-2.0 OR MulanPSL-2.0`

除非另行说明，你提交的贡献按上述三者同时授权，不附加其他条件。
