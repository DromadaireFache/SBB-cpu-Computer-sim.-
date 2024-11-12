import pygame as app

RAM_SIZE = 2**12

class Bit:
    def __init__(self, state: bool | int = False):
        self.state = bool(state)
    def __call__(self):
        return self.state
    def flip(self):
        self.state = not(self.state)
        return self
    def on(self):
        self.state = True
    def off(self):
        self.state = False
    def __str__(self):
        return bin(int(self()))
    def copy(self, new_value):
        self.state = new_value()
    def equal(self, new_value):
        self.state = bool(new_value)

class Byte:
    def __init__(self, value = 0, signed = False):
        if signed and value < 0:
            value = (value % 128) + 128
        else:
            value %= 256
        self.byte = [Bit((value >> i) % 2) for i in range(8)]
    def __str__(self):
        string = ""
        for i in range(8):
            string += str(int(self.byte[i].state))
        return "0b" + string[::-1] + f" (i8: {str(self.int())}, u8: {str(self.uint())}, {repr(chr(self.uint())).replace('\\x', '')})"
    def uint(self):
        sum = 0
        for i in range(8):
            sum |= int(self.byte[i].state) << i
        return sum
    def int(self):
        if self.byte[7]():
            complement = 0
            for i in range(8):
                complement |= (not self.byte[i]()) << i
            return -(complement + 1)
        else:
            return self.uint()
    def __iter__(self):
        return iter(self.byte)
    def equal(self, new_value, signed = False):
        if signed and new_value < 0:
            new_value = (new_value % 128) + 128
        else:
            new_value %= 256
        for i in range(8):
            self.byte[i].equal((new_value >> i) % 2)
    def copy(self, new_value):
        for i in range(8):
            self.byte[i].state = new_value.byte[i].state

class Gate:
    count = 0
    def __init__(self, *inputs):
        self.inputs = inputs
    def __call__(self):
        return False
    def __str__(self):
        return bin(int(self()))
    def verify_inputs(self, N):
        if len(self.inputs) < N:
            self.inputs += (Bit(False),) * (N - len(self.inputs))
    @classmethod
    def logic_gate_count(cls, inc = 1):
        cls.count += inc
    def reset(cls):
        cls.count = 0

class And(Gate):
    def __call__(self):
        # Gate.logic_gate_count()
        L = len(self.inputs)
        if L == 0: return False
        for i in range(L):
            if not self.inputs[i](): return False
        return True

class Or(Gate):
    def __call__(self):
        # Gate.logic_gate_count()
        for i in range(len(self.inputs)):
            if self.inputs[i](): return True
        return False

class Not(Gate):
    def __init__(self, input):
        self.input = input
    def __call__(self):
        # Gate.logic_gate_count()
        return not self.input()

class Xor(Gate):
    def __call__(self):
        # Gate.logic_gate_count()
        L = len(self.inputs)
        if L == 0: return False
        result = self.inputs[0]()
        for i in range(1,L):
            result ^= self.inputs[i]()
        return result
    
class Nand(Gate):
    def __call__(self):
        return not And(*self.inputs)()

class Nor(Gate):
    def __call__(self):
        return not Or(*self.inputs)()

class FullAdder(Gate):
    #self.inputs[2] is the carry
    def sum(self):
        self.verify_inputs(3)
        return Xor(self.inputs[0],self.inputs[1],self.inputs[2])()
    def carry(self):
        self.verify_inputs(3)
        AND1 = And(Xor(self.inputs[0],self.inputs[1]),self.inputs[2])
        AND2 = And(self.inputs[0],self.inputs[1])
        return Or(AND1,AND2)()
    def __str__(self):
        return f"0b{int(self.carry())}{int(self.sum())}"

class Adder:
    def __init__(self, A: Byte, B: Byte, CI: Bit):
        self.A = A
        self.B = B
        self.carry = CI
    def __call__(self):
        """Outputs: 'sum', 'carry'"""
        sum = Byte()
        for i in range(8):
            sum.byte[i] = Bit(FullAdder(self.A.byte[i],self.B.byte[i],self.carry).sum())
            self.carry = Bit(FullAdder(self.A.byte[i],self.B.byte[i],self.carry).carry())
        return {'sum': sum, 'carry': self.carry}

class Alu:
    def __init__(self, A: Byte, B: Byte, bus: Byte):
        self.A = A #regA connection
        self.B = B #regB connection
        self.bus = bus
        self.adder = Adder(self.A, self.B, Bit())

        self.L1 = Bit()  #alu 1 signal
        self.L2 = Bit()  #alu 2 signal
        self.L3 = Bit()  #alu 3 signal
        self.L4 = Bit()  #alu 4 signal

        self.CF = Bit() #carry flag
        self.ZF = Bit() #zero flag
        self.SF = Bit() #sign flag

    def optype(self) -> int:
        return (self.L4() << 3) | (self.L3() << 2) | (self.L2() << 1) | self.L1()
    
    def multiply(self, high = False):
        output = Byte(And(self.A.byte[0], self.B.byte[0])())
        in1 = Byte()
        in2 = Byte()
        self.adder.A, self.adder.B = in1, in2
        self.adder.carry.off()
        in1.byte = [And(self.A.byte[0], self.B.byte[j]) for j in range(1,8)] + [Bit()]
        for i in range(1,8):
            in2.byte = [And(self.A.byte[i], self.B.byte[j]) for j in range(8)]
            sum = self.adder()
            output.byte[i].copy(sum['sum'].byte[0])
            in1.byte = [sum['sum'].byte[j] for j in range(1,8)] + [sum['carry']]
        if high:
            self.bus.copy(in1)
        else:
            self.bus.copy(output)
            self.CF.copy(in1.byte[0])

    def __call__(self):
        optype = self.optype()
        match optype:
            case 1: #addition L1
                self.adder.A, self.adder.B = self.A, self.B
                self.adder.carry.off()
                result = self.adder()
                self.bus.copy(result['sum'])
                self.CF.copy(result['carry'])
            
            case 2: #substraction L2
                Bxor = Byte()
                Bxor.byte = [Bit(not Bbit()) for Bbit in self.B]
                self.adder.A, self.adder.B = self.A, Bxor
                self.adder.carry.on()
                result = self.adder()
                self.bus.copy(result['sum'])
                self.CF.copy(result['carry'])
            
            case 3: #increment L1|L2
                carry = Bit(1)
                for i in range(8):
                    self.bus.byte[i].copy(Xor(self.A.byte[i], carry))
                    carry = And(self.A.byte[i], carry)
                self.CF.copy(carry)
            
            case 4: #decrement L3
                borrow = Bit(1)
                for i in range(8):
                    self.bus.byte[i].copy(Xor(self.A.byte[i], borrow))
                    borrow = And(Not(self.A.byte[i]), borrow)
                self.CF.copy(borrow)
            
            case 5: #and L1|L3
                for i in range(8):
                    self.bus.byte[i].copy(And(self.A.byte[i], self.B.byte[i]))

            case 6: #or L2|L3
                for i in range(8):
                    self.bus.byte[i].copy(Or(self.A.byte[i], self.B.byte[i]))
            
            case 7: #not A L1|L2|L3
                for i in range(8):
                    self.bus.byte[i].copy(Not(self.A.byte[i]))
            
            case 8: #right shift A L4
                self.bus.byte = [Bit(self.A.byte[i].state) for i in range(1,8)] + [Bit()]
            
            case 9: #left shift A L1|L4
                self.bus.byte = [Bit()] + [Bit(self.A.byte[i].state) for i in range(7)]
                self.CF.copy(self.A.byte[7])
            
            case 10: #multiply low L2|L4
                self.multiply(False)

            case 11: #multiply high L1|L2|L4
                self.multiply(True)
            
            case 12: #xor L3|L4
                for i in range(8):
                    self.bus.byte[i].copy(Xor(self.A.byte[i], self.B.byte[i]))
        
        if optype != 0:
            self.ZF.copy(Nor(*self.bus))
            self.SF.copy(self.bus.byte[7])

class Ram:
    def __init__(self, mbus: list[Bit], bus: Byte):
        self.mbus = mbus
        self.A = [Bit() for i in range(len(mbus))]
        self.bus = bus
        self.RI = Bit() #RAM write
        self.RO = Bit() #RAM read
        self.MI = Bit() #MAR in
        self.mem = [Byte() for i in range(RAM_SIZE)]
    def chunk(self, start = 0, end = 16):
        msg = f"RAM -> {start}\n" if start == end else f"RAM -> ({start} to {end})\n"
        msg += "[ Addr ][   Data   ]\n"
        start = max(start, 0)
        end = min(end, RAM_SIZE - 1)
        for i in range(start, end+1):
            msg += f"| {str(i).rjust(4, '0')} || {str(self.mem[i])[2:10]} |\n"
        print(msg)
    def __str__(self):
        string = ""
        for i in range(12):
            string += str(int(self.A[i].state))
        return string[::-1]
    def __len__(self):
        count = 0
        for byte in self.mem:
            if byte.uint() != 0:
                count += 1
        return count
    def decoder(self):
        inv = [Bit(self.A[i]()).flip() for i in range(len(self.A))]
        outputs = []
        for i in range(RAM_SIZE):
            input = []
            for j in range(len(self.A)):
                input.append(self.A[j] if (i & (1 << j) != 0) else inv[j])
            outputs.append(Bit(And(*input)()))
        return outputs
    def value(self):
        sum = 0
        for i in range(12):
            sum |= int(self.A[i].state) << i
        return sum
    def write(self):
        for i in range(12):
            self.A[i].state = self.mbus[i].state
    def __call__(self):
        # addr = self.decoder()
        # for i in range(16):
        #     if And(addr[i], self.RI)():
        #         self.mem[i].copy(self.bus)
        #     if And(addr[i], self.RO)():
        #         self.bus.copy(self.mem[i])
        if self.RI():
            # Gate.logic_gate_count(16)
            self.mem[self.value()].copy(self.bus)
        if self.RO():
            # Gate.logic_gate_count(16)
            # print(f"Wrote {self.mem[self.value()].uint()} from {self.value()}")
            self.bus.copy(self.mem[self.value()])
        if self.MI():
            self.write()

def bin_counter(counter: list[Bit], word_len: int, dec = False):
        carry = Bit(1)
        if dec:
            for i in range(word_len):
                counter[i].copy(Xor(counter[i], carry))
                carry = And(counter[i], carry)
        else:
            for i in range(word_len):
                counter[i].copy(Xor(counter[i], carry))
                carry = And(Not(counter[i]), carry)

class ProgCounter:
    def __init__(self, bus: list[Bit]):
        self.mbus = bus
        self.CO = Bit() #Program counter out
        self.JP = Bit() #Jump (program counter in)
        self.CE = Bit() #Count enable
        self.counter = [Bit() for i in range(12)]
    def __str__(self):
        string = ""
        for i in range(len(self.counter)):
            string += str(int(self.counter[i].state))
        return "0b" + string[::-1] + f" (u12: {str(self.uint())})"
    def uint(self):
        sum = 0
        for i in range(len(self.counter)):
            sum |= int(self.counter[i].state) << i
        return sum
    def write(self):
        if self.CE():
            # Gate.logic_gate_count(12)
            bin_counter(self.counter, 12)
        if self.JP():
            # Gate.logic_gate_count(12)
            for i in range(len(self.counter)):
                self.counter[i].state = self.mbus[i].state
    def read(self):
        if self.CO():
            # Gate.logic_gate_count(12)
            for i in range(len(self.counter)):
                self.mbus[i].state = self.counter[i].state
    def reset(self):
        for i in range(len(self.counter)):
            self.counter[i].off()
        
class Register:
    def __init__(self, bus: Byte):
        self.bus = bus
        self.IN = Bit()
        self.OUT = Bit()
        self.data = Byte()
    def __str__(self):
        return str(self.data)
    def write(self):
        if self.IN():
            # Gate.logic_gate_count(8)
            self.data.copy(self.bus)
    def read(self):
        if self.OUT():
            # Gate.logic_gate_count(8)
            self.bus.copy(self.data)

class ControlUnit:
    ROM_SIZE = 2**14
    def __init__(self, ir: Byte, ir2: Byte, controls: list[Bit], cond: list[Bit], mbus: list[Bit]):
        self.counter = Byte()
        self.ins = ir.byte[4:]
        self.addr = ir2.byte + ir.byte[:4]
        self.controls = controls
        self.cond = cond
        self.mbus = mbus
        self.IO = self.controls[4]
        self.rom = [0] * ControlUnit.ROM_SIZE
        control_signals = open("control_signals.rom", "r")
        for i in range(ControlUnit.ROM_SIZE):
            line = control_signals.readline()
            self.rom[i] = int(line, 2)
        control_signals.close()
    def __str__(self):
        return f"Op: {(self.value.uint() & 0b11110000) >> 4}"
    def decoder(self):
        inv = []
        for i in range(3):
            inv.append(Bit(self.counter.byte[i]()).flip())
        outputs = []
        for i in range(8):
            input = []
            for j in range(3):
                input.append(self.counter.byte[j] if (i & (1 << j) != 0) else inv[j])
            outputs.append(Bit(And(*input)()))
        return outputs
    def reset(self):
        self.counter.equal(0)
        for control in self.controls:
            control.off()
    def value(self):
        sum = 0
        for i in range(4):
            sum |= int(self.ins[i].state) << i
            sum |= int(self.addr[i+8].state) << (i+4)
        return sum
    def __call__(self):
        rom_addr = (self.counter.uint() & 7) | (self.value() << 3)
        rom_addr |= int(self.cond[0]()) << 11
        rom_addr |= int(self.cond[1]()) << 12
        rom_addr |= int(self.cond[2]()) << 13
        control_signals = self.rom[rom_addr]
        if control_signals == 0:
            self.reset()
        else:
            for i in range(len(self.controls)):
                self.controls[i].equal(bool(control_signals & (1 << i)))
            bin_counter(self.counter.byte, 3)
    def read(self):
        if self.IO():
            for i in range(12):
                self.mbus[i].state = self.addr[i].state

class StackMemory:
    def __init__(self, bus: Byte, mbus: list[Bit]):
        self.bus = bus
        self.mbus = mbus
        self.SI = Bit() #Stack in (increment)
        self.SO = Bit() #Stack out (decrement)
        self.SA = Bit() #Stack address output (false: takes from bus, true: takes from mbus)
        self.sp = Byte() #Stack pointer
        self.mem = [[Bit() for j in range(12)] for i in range(256)]
    def __str__(self):
        msg = f"[   sp = {str(self.sp.uint()).rjust(3, '0')}   ]\n"
        for i in range(1, self.sp.uint()+1):
            msg += f"| {bin(self.uint(self.sp.uint() - i))[2:].rjust(12, '0')} |\n"
        return msg
    def uint(self, n):
        sum = 0
        for i in range(len(self.mem[n])):
            sum |= int(self.mem[n][i].state) << i
        return sum
    def inc(self):
        bin_counter(self.sp.byte, 8)
    def dec(self):
        borrow = Bit(1)
        for bit in self.sp.byte:
            bit.copy(Xor(bit, borrow))
            borrow = And(bit, borrow)
    def __call__(self):
        if self.SO():
            self.dec()
            if self.SA():
                for i in range(12):
                    self.mbus[i].copy(self.mem[self.sp.uint()][i])
            else:
                for i in range(8):
                    self.bus.byte[i].copy(self.mem[self.sp.uint()][i])
        elif self.SI():
            if self.SA():
                for i in range(12):
                    self.mem[self.sp.uint()][i].copy(self.mbus[i])
            else:
                for i in range(8):
                    self.mem[self.sp.uint()][i].copy(self.bus.byte[i])
            self.inc()

class Screen:
    BACK_COLOR = (10, 20, 10)
    LETTER_COLOR = (0, 200, 17)
    CHAR_SIZE = (4, 6)
    SCREEN_DIM = (32, 8)

    def __init__(self, bus: Byte, mem_access = None, scale=10) -> None:
        self.dim = (scale * Screen.CHAR_SIZE[0] * Screen.SCREEN_DIM[0],
                    scale * Screen.CHAR_SIZE[1] * Screen.SCREEN_DIM[1])
        self.scale = scale
        self.power = True
        self.ram: Ram | None = mem_access
        self.scp = Byte()
        self.PI  = Bit()
        self.bus = bus
    
    def on(self):
        app.init()
        self.font = app.font.SysFont("Monospace", 70)
        app.display.set_caption("SBB Computer by Charles Benoit")
        app.display.set_icon(app.image.load("sbb_logo.ico"))
        self.display = app.display.set_mode((self.dim[0], self.dim[1]))
        if self.ram == None:
            app.quit()
            print("[Error] Screen disconnected from RAM")
            exit()
        self.refresh()

        # while self.power:
        #     self.refresh()

        # app.quit()

    def refresh(self, render=False):
        if self.PI():
            self.scp.copy(self.bus)

        for event in app.event.get():
            if event.type == app.QUIT:
                self.power = False
                app.quit()

        if self.power:
            if render:
                self.grid()
            app.display.update()

    def grid(self):
        self.display.fill(Screen.BACK_COLOR)
        for x in range(0, Screen.SCREEN_DIM[0]):
            for y in range(0, Screen.SCREEN_DIM[1]):
                rect = app.Rect(x*Screen.CHAR_SIZE[0]*self.scale, y*Screen.CHAR_SIZE[1]*self.scale,
                                Screen.CHAR_SIZE[0]*self.scale, Screen.CHAR_SIZE[1]*self.scale)
                app.draw.rect(self.display, (0,0,0), rect, 1)
                addr = (x + Screen.SCREEN_DIM[0]*y - self.scp.uint())%256 + 1024 
                char = self.ram.mem[addr].uint() % 128
                if char != 0:
                    char = self.font.render(chr(char), False, Screen.LETTER_COLOR)
                    self.display.blit(char, ((x*Screen.CHAR_SIZE[0]-0.3)*self.scale,
                                             (y*Screen.CHAR_SIZE[1]-1.3)*self.scale))

#    MAIN PROGRAM    #
if __name__ == '__main__':
    BUS  = Byte()
    MBUS = [Bit() for i in range(12)]
    RAM  = Ram(MBUS, BUS)
    text = "Hello, World!"
    for i, char in enumerate(text):
        RAM.mem[i+1024].equal(ord(char))
    SCREEN = Screen(RAM)
    SCREEN.scp.equal(10)
    SCREEN.on()
    while SCREEN.power:
        SCREEN.refresh()

else:
    BUS  = Byte()
    HLT  = Bit() #Halt signal
    RFH  = Bit() #Refresh signal

    #    Registers    #
    REGA = Register(BUS)
    REGB = Register(BUS)
    IR   = Register(BUS) #write only
    IR2  = Register(BUS)
    OUT  = Register(BUS) #write only
    MBUS = [Bit() for i in range(12)]

    def print_mbus():
        string = ""
        sum = 0
        for i in range(len(MBUS)):
            string += str(int(MBUS[i].state))
            sum |= int(MBUS[i].state) << i
        print("0b" + string[::-1] + f" (u12: {str(sum)})")

    #    Components    #
    ALU  = Alu(REGA.data, REGB.data, BUS)
    RAM  = Ram(MBUS, BUS)
    PC   = ProgCounter(MBUS)
    ST   = StackMemory(BUS, MBUS)
    SCREEN = Screen(BUS, RAM)
    control_wires = [
        RAM.MI,     #0
        RAM.RI,     #1
        RAM.RO,     #2
        IR.IN,      #3
        IR2.OUT,    #4
        PC.CO,      #5
        PC.JP,      #6
        PC.CE,      #7
        REGA.IN,    #8
        REGA.OUT,   #9

        ALU.L1,     #10
        ALU.L2,     #11
        ALU.L3,     #12
        ALU.L4,     #13
        
        HLT,        #14
        REGB.IN,    #15
        REGB.OUT,   #16
        OUT.IN,     #17
        IR2.IN,     #18
        ST.SI,      #19
        ST.SO,      #20
        ST.SA,      #21
        RFH,        #22
        SCREEN.PI   #23
    ]
    flags = [
        ALU.CF,     #0, carry flag
        ALU.ZF,     #1, zero flag
        ALU.SF      #2, sign flag
    ]
    CU = ControlUnit(IR.data, IR2.data, control_wires, flags, MBUS)
    count = 0
    def run(display = True, ends = True, debug = False, screen = False):
        global count
        CU()
        if HLT() or not SCREEN.power:
            return False
        ALU()
        PC  .read()
        REGA.read()
        REGB.read()
        IR2 .read()
        CU  .read()
        RAM()
        ST()
        REGA.write()
        REGB.write()
        IR  .write()
        IR2 .write()
        OUT .write()
        PC  .write()
        if screen:
            SCREEN.refresh(RFH())
        
        if debug and ends:
            print(f"\n > [Debugger] Tick {count}")
            print(" > BUS:", BUS)
            print(" > REGA:", REGA)
            print(" > REGB:", REGB)
            print(" > I1:", IR)
            print(" > I2:", IR2)
            print(ST)
        count += 1
        if display:
            print(" > OUT :", OUT, "              ", end='\r')
        return True