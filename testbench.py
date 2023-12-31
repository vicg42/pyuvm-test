import random
import cocotb
import pyuvm
import sys
# from pathlib import Path
# sys.path.append(str(Path("..").resolve()))
import testbench_utils

# Sequence classes
class AluSeqItem(pyuvm.uvm_sequence_item):

    def __init__(self, name, aa, bb, op):
        super().__init__(name)
        self.A = aa
        self.B = bb
        self.op = testbench_utils.Ops(op)

    def randomize_operands(self):
        self.A = random.randint(0, 255)
        self.B = random.randint(0, 255)

    def randomize(self):
        self.randomize_operands()
        self.op = random.choice(list(testbench_utils.Ops))

    def __eq__(self, other):
        same = self.A == other.A and self.B == other.B and self.op == other.op
        return same

    def __str__(self):
        return f"{self.get_name()} : A: 0x{self.A:02x} \
        OP: {self.op.name} ({self.op.value}) B: 0x{self.B:02x}"


class RandomSeq(pyuvm.uvm_sequence):
    async def body(self):
        for op in list(testbench_utils.Ops):
            cmd_tr = AluSeqItem("cmd_tr", None, None, op)
            await self.start_item(cmd_tr)
            cmd_tr.randomize_operands()
            await self.finish_item(cmd_tr)


class MaxSeq(pyuvm.uvm_sequence):
    async def body(self):
        for op in list(testbench_utils.Ops):
            cmd_tr = AluSeqItem("cmd_tr", 0xff, 0xff, op)
            await self.start_item(cmd_tr)
            await self.finish_item(cmd_tr)


class TestAllSeq(pyuvm.uvm_sequence):

    async def body(self):
        seqr = pyuvm.ConfigDB().get(None, "", "SEQR")
        random = RandomSeq("random")
        max = MaxSeq("max")
        await random.start(seqr)
        await max.start(seqr)


class TestAllForkSeq(pyuvm.uvm_sequence):

    async def body(self):
        seqr = pyuvm.ConfigDB().get(None, "", "SEQR")
        random = RandomSeq("random")
        max = MaxSeq("max")
        random_task = cocotb.fork(random.start(seqr))
        max_task = cocotb.fork(max.start(seqr))
        await cocotb.triggers.Combine(cocotb.triggers.Join(random_task), cocotb.triggers.Join(max_task))

# Sequence library example


class OpSeq(pyuvm.uvm_sequence):
    def __init__(self, name, aa, bb, op):
        super().__init__(name)
        self.aa = aa
        self.bb = bb
        self.op = testbench_utils.Ops(op)

    async def body(self):
        seq_item = AluSeqItem("seq_item", self.aa, self.bb,
                              self.op)
        await self.start_item(seq_item)
        await self.finish_item(seq_item)
        self.result = seq_item.result


async def do_add(seqr, aa, bb):
    seq = OpSeq("seq", aa, bb, testbench_utils.Ops.ADD)
    await seq.start(seqr)
    return seq.result


async def do_and(seqr, aa, bb):
    seq = OpSeq("seq", aa, bb, testbench_utils.Ops.AND)
    await seq.start(seqr)
    return seq.result


async def do_xor(seqr, aa, bb):
    seq = OpSeq("seq", aa, bb, testbench_utils.Ops.XOR)
    await seq.start(seqr)
    return seq.result


async def do_mul(seqr, aa, bb):
    seq = OpSeq("seq", aa, bb, testbench_utils.Ops.MUL)
    await seq.start(seqr)
    return seq.result


class FibonacciSeq(pyuvm.uvm_sequence):
    def __init__(self, name):
        super().__init__(name)
        self.seqr = pyuvm.ConfigDB().get(None, "", "SEQR")

    async def body(self):
        prev_num = 0
        cur_num = 1
        fib_list = [prev_num, cur_num]
        for _ in range(7):
            sum = await do_add(self.seqr, prev_num, cur_num)
            fib_list.append(sum)
            prev_num = cur_num
            cur_num = sum
        pyuvm.uvm_root().logger.info("Fibonacci Sequence: " + str(fib_list))
        pyuvm.uvm_root().set_logging_level_hier(pyuvm.CRITICAL)


class Driver(pyuvm.uvm_driver):
    def build_phase(self):
        self.ap = pyuvm.uvm_analysis_port("ap", self)

    def start_of_simulation_phase(self):
        self.bfm = testbench_utils.TinyAluBfm()

    async def launch_tb(self):
        await self.bfm.reset()
        self.bfm.start_bfm()

    async def run_phase(self):
        await self.launch_tb()
        while True:
            cmd = await self.seq_item_port.get_next_item()
            await self.bfm.send_op(cmd.A, cmd.B, cmd.op)
            result = await self.bfm.get_result()
            self.ap.write(result)
            cmd.result = result
            self.seq_item_port.item_done()


class Coverage(pyuvm.uvm_subscriber):

    def end_of_elaboration_phase(self):
        self.cvg = set()

    def write(self, cmd):
        (_, _, op) = cmd
        self.cvg.add(op)

    def report_phase(self):
        try:
            disable_errors = pyuvm.ConfigDB().get(
                self, "", "DISABLE_COVERAGE_ERRORS")
        except pyuvm.UVMConfigItemNotFound:
            disable_errors = False
        if not disable_errors:
            if len(set(testbench_utils.Ops) - self.cvg) > 0:
                self.logger.error(
                    f"Functional coverage error. Missed: {set(testbench_utils.Ops)-self.cvg}")
                assert False
            else:
                self.logger.info("Covered all operations")
                assert True


class Scoreboard(pyuvm.uvm_component):

    def build_phase(self):
        self.cmd_fifo = pyuvm.uvm_tlm_analysis_fifo("cmd_fifo", self)
        self.result_fifo = pyuvm.uvm_tlm_analysis_fifo("result_fifo", self)
        self.cmd_get_port = pyuvm.uvm_get_port("cmd_get_port", self)
        self.result_get_port = pyuvm.uvm_get_port("result_get_port", self)
        self.cmd_export = self.cmd_fifo.analysis_export
        self.result_export = self.result_fifo.analysis_export

    def connect_phase(self):
        self.cmd_get_port.connect(self.cmd_fifo.get_export)
        self.result_get_port.connect(self.result_fifo.get_export)

    def check_phase(self):
        passed = True
        try:
            self.errors = pyuvm.ConfigDB().get(self, "", "CREATE_ERRORS")
        except pyuvm.UVMConfigItemNotFound:
            self.errors = False
        while self.result_get_port.can_get():
            _, actual_result = self.result_get_port.try_get()
            cmd_success, cmd = self.cmd_get_port.try_get()
            if not cmd_success:
                self.logger.critical(f"result {actual_result} had no command")
            else:
                (A, B, op_numb) = cmd
                op = testbench_utils.Ops(op_numb)
                predicted_result = testbench_utils.alu_prediction(A, B, op, self.errors)
                if predicted_result == actual_result:
                    self.logger.info(f"PASSED: 0x{A:02x} {op.name} 0x{B:02x} ="
                                     f" 0x{actual_result:04x}")
                else:
                    self.logger.error(f"FAILED: 0x{A:02x} {op.name} 0x{B:02x} "
                                      f"= 0x{actual_result:04x} "
                                      f"expected 0x{predicted_result:04x}")
                    passed = False
        assert passed


class Monitor(pyuvm.uvm_component):
    def __init__(self, name, parent, method_name):
        super().__init__(name, parent)
        self.method_name = method_name

    def build_phase(self):
        self.ap = pyuvm.uvm_analysis_port("ap", self)
        self.bfm = testbench_utils.TinyAluBfm()
        self.get_method = getattr(self.bfm, self.method_name)

    async def run_phase(self):
        while True:
            datum = await self.get_method()
            self.logger.debug(f"MONITORED {datum}")
            self.ap.write(datum)


class AluEnv(pyuvm.uvm_env):

    def build_phase(self):
        self.seqr = pyuvm.uvm_sequencer("seqr", self)
        pyuvm.ConfigDB().set(None, "*", "SEQR", self.seqr)
        self.driver = Driver.create("driver", self)
        self.cmd_mon = Monitor("cmd_mon", self, "get_cmd")
        self.coverage = Coverage("coverage", self)
        self.scoreboard = Scoreboard("scoreboard", self)

    def connect_phase(self):
        self.driver.seq_item_port.connect(self.seqr.seq_item_export)
        self.cmd_mon.ap.connect(self.scoreboard.cmd_export)
        self.cmd_mon.ap.connect(self.coverage.analysis_export)
        self.driver.ap.connect(self.scoreboard.result_export)


#-------------------------------------
#Run tests
#-------------------------------------
@pyuvm.test()
class AluTest(pyuvm.uvm_test):
    """Test ALU with random and max values"""

    def build_phase(self):
        self.env = AluEnv("env", self)

    def end_of_elaboration_phase(self):
        self.test_all = TestAllSeq.create("test_all")

    async def run_phase(self):
        self.raise_objection()
        await self.test_all.start()
        self.drop_objection()


@pyuvm.test()
class ParallelTest(AluTest):
    """Test ALU random and max forked"""

    def build_phase(self):
        pyuvm.uvm_factory().set_type_override_by_type(TestAllSeq, TestAllForkSeq)
        super().build_phase()


@pyuvm.test()
class FibonacciTest(AluTest):
    """Run Fibonacci program"""

    def build_phase(self):
        pyuvm.ConfigDB().set(None, "*", "DISABLE_COVERAGE_ERRORS", True)
        pyuvm.uvm_factory().set_type_override_by_type(TestAllSeq, FibonacciSeq)
        return super().build_phase()


# @pyuvm.test(expect_fail=True)
# class AluTestErrors(AluTest):
#     """Test ALU with errors on all operations"""

#     def start_of_simulation_phase(self):
#         pyuvm.ConfigDB().set(None, "*", "CREATE_ERRORS", True)
