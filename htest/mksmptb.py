"""soc-smp 的端到端测试台：两个核跑同一份程序，靠 mhartid 各走各的。

判据不是「跑起来了」而是「两个核都跑了、而且各自知道自己是谁」：同一份镜像
装进内存，每个核按自己的 hartid 算出一个槽位与一个值写进去，测试台再从外部
总线把两个槽位读回来对。核只有一个的话第二个槽位会是零，对不上。

hartid 是引脚，装配把它透传到顶层，所以「两个核」这件事在这里是可见的：
cpu0_pins.hartid(0)、cpu1_pins.hartid(1)。
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from rasm import assemble  # noqa: E402

out = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".")
out.mkdir(parents=True, exist_ok=True)

SLOT = 0x7F8          # 内存里避开程序的两个字：0x800007F8 与 0x800007FC

SRC = [
    "  csrrs t0, 0xF14, zero",     # t0 = hartid
    "  addi  t1, t0, 1",           # 写进去的值：1 或 2
    "  lui   a1, 0x80000",
    "  slli  t2, t0, 2",
    "  add   a1, a1, t2",
    f"  sw    t1, {SLOT}(a1)",
    "done:",
    "  jal  zero, done",
]
CHECKS = [(0x8000_0000 + SLOT, 1), (0x8000_0000 + SLOT + 4, 2)]

prog = assemble(SRC)
rom = "\n".join(f"      {i}: return 32'h{w:08X};" for i, w in enumerate(prog))
chk = "\n".join(f"      {i}: return tuple2(32'h{a:08X}, 32'h{v:08X});"
                for i, (a, v) in enumerate(CHECKS))

(out / "SmpProg.bsv").write_text(f'''package SmpProg;

// 由 tb/mksmptb.py 生成，勿手改。

Integer progLen = {len(prog)};
Integer chkLen  = {len(CHECKS)};

function Bit#(32) progWord(Bit#(32) i);
  case (i)
{rom}
    default: return 32'h00000013;
  endcase
endfunction

function Tuple2#(Bit#(32), Bit#(32)) checkAt(Bit#(32) i);
  case (i)
{chk}
    default: return tuple2(0, 0);
  endcase
endfunction

endpackage
''', encoding="utf-8")

(out / "SmpTb.bsv").write_text('''package SmpTb;

import Apb4::*;
import Hart::*;
import Uart::*;
import Aclint::*;
import Plic::*;
import SocSmpPkg::*;
import SmpProg::*;

// 端到端：装程序 -> 放两个核 -> 读两个槽位。少跑一个核就对不上。

typedef enum { Load, Run, Read, Done } Phase deriving (Bits, Eq);

(* synthesize *)
module mkSmpTb(Empty);
  SocSmpIfc soc <- mkSocSmp;

  Reg#(Phase)    ph   <- mkReg(Load);
  Reg#(Bit#(32)) idx  <- mkReg(0);
  Reg#(Bit#(2))  st   <- mkReg(0);   // APB4 的两拍：0 建立，1 访问
  Reg#(Bit#(32)) wait_ <- mkReg(0);
  Reg#(Bool)     bad  <- mkReg(False);

  Bool loading = ph == Load;
  Bool reading = ph == Read;
  Bool active  = loading || reading;

  Bit#(32) addr = loading ? (32'h8000_0000 + (idx << 2))
                          : tpl_1(checkAt(idx));
  Bit#(32) wdat = progWord(idx);

  rule drive;
    soc.bus.req(addr, 3'b000, active, active && st == 1,
                loading, wdat, 4'hF);
    // 两个核编号不同，程序靠这个分岔
    soc.cpu0_pins.halt(ph == Load);
    soc.cpu0_pins.hartid(0);
    soc.cpu1_pins.halt(ph == Load);
    soc.cpu1_pins.hartid(1);
    soc.clint_pins.tick(0);
    soc.plic0_pins.src(0);
    soc.uart0_pins.rxd(1);
    soc.uart0_pins.cts(1);
  endrule

  rule step;
    case (ph)
      Load: begin
        if (st == 0) st <= 1;
        else if (soc.bus.pready) begin
          st <= 0;
          if (idx + 1 == fromInteger(progLen)) begin
            ph <= Run; idx <= 0; wait_ <= 0;
          end else idx <= idx + 1;
        end
      end
      Run: begin
        if (wait_ > 4000) begin ph <= Read; idx <= 0; st <= 0; end
        else wait_ <= wait_ + 1;
      end
      Read: begin
        if (st == 0) st <= 1;
        else if (soc.bus.pready) begin
          st <= 0;
          Bit#(32) want = tpl_2(checkAt(idx));
          if (soc.bus.prdata != want) begin
            $display("FAIL slot %0d at %08h: got %08h want %08h",
                     idx, addr, soc.bus.prdata, want);
            bad <= True;
          end
          if (idx + 1 == fromInteger(chkLen)) ph <= Done;
          else idx <= idx + 1;
        end
      end
      Done: begin
        if (bad) $display("FAILED");
        else $display("PASS both harts ran and each knew its own id");
        $finish(bad ? 1 : 0);
      end
    endcase
  endrule
endmodule

endpackage
''', encoding="utf-8")
print(f"  程序 {len(prog)} 条，两个槽位")
