from pathlib import Path

CS_NUM = 24
FLAGS_NUM = 3

bit = (1 << x for x in range(CS_NUM+1))
MI = next(bit)  #mem address register in
RI = next(bit)  #ram data in
RO = next(bit)  #ram data out
II = next(bit)  #instruction register in
IO = next(bit)  #instruction register out
CO = next(bit)  #program counter register out
JP = next(bit)  #program counter register in
CE = next(bit)  #program counter increment enable
AI = next(bit)  #A register in
AO = next(bit)  #A register out
L1 = next(bit)  #ALU signal 1
L2 = next(bit)  #ALU signal 2
L3 = next(bit)  #ALU signal 3
L4 = next(bit)  #ALU signal 4
HT = next(bit)  #halt signal enable
BI = next(bit)  #B register in
BO = next(bit)  #B register out
OI = next(bit)  #output register in
XI = next(bit)  #extended instruction content in
SI = next(bit)  #Stack in (increments)
SO = next(bit)  #Stack out (decrements)
SA = next(bit)  #Stack address (linked w bus if false and mbus if true)
RF = next(bit)  #refresh signal
PI = next(bit)  #screen pointer in

assert next(bit) >> CS_NUM == 1, "Incorrect control signal count"

controls_list = [
    #lda, load A from address
    [CO|MI, RO|XI|CE, IO|MI, RO|AI],

    #add, add A with address, store in A
    [CO|MI, RO|XI|CE, IO|MI, RO|BI, L1|AI],

    #sub, sub A with address, store in A
    [CO|MI, RO|XI|CE, IO|MI, RO|BI, L2|AI],

    #sta, load data from A to address
    [CO|MI, RO|XI|CE, IO|MI, AO|RI],

    #jsr, jump to subroutine, jumps to an address while storing program counter to stack
    [CO|MI, RO|XI|CE, SI|CO|SA, IO|JP],

    #jmp, load prog counter with ins register data
    [CO|MI, RO|XI, IO|JP],

    #jpc, jump if carry flag
    [CE],

    #jpz, jump if zero flag
    [CE],

    #jpn, jump if negative flag
    [CE],

    #and, and A with address, store in A
    [CO|MI, RO|XI|CE, IO|MI, RO|BI, L1|L3|AI],

    #or, or A with address, store in A
    [CO|MI, RO|XI|CE, IO|MI, RO|BI, L2|L3|AI],

    #ldax, loads A from (address + B data)
    [CO|MI, RO|AI|CE, L1|XI, IO|MI, RO|AI],

    #multl, multiply A with address, store lower 8 bits in A
    [CO|MI, RO|XI|CE, IO|MI, RO|BI, L2|L4|AI],

    #multh, multiply A with address, store higher 8 bits in A
    [CO|MI, RO|XI|CE, IO|MI, RO|BI, L1|L2|L4|AI],

    #ops with 1byte arguments
    [],

    #ops w/o arguments (monos)
    [],
]

doc = open(str(Path.cwd()) + "\\control_signals.rom", "w")

def writeROM(flags: int, al: int):
    #Common fetching instructions
    fetch1 = bin(CO|MI)[2:].rjust(CS_NUM, '0') + '\n'
    fetch2 = bin(RO|II|CE)[2:].rjust(CS_NUM, '0') + '\n'

    #Carry flag conditional controls
    CF = bool(flags & 1)
    controls_list[6] = [CO|MI, RO|XI, IO|JP] if CF else [CE]

    #Zero flag conditional controls
    ZF = bool(flags & 2)
    controls_list[7] = [CO|MI, RO|XI, IO|JP] if ZF else [CE]

    #Signal flag conditional controls
    SF = bool(flags & 4)
    controls_list[8] = [CO|MI, RO|XI, IO|JP] if SF else [CE]

    #addressless ops
    if al == 0:
        #ldi, load A with next byte data
        controls_list[14] = [CO|MI, RO|AI|CE]
        #noop, does nothing
        controls_list[15] = []
    elif al == 1:
        #add#, add A with next byte data
        controls_list[14] = [CO|MI, RO|BI|CE, L1|AI]
        #out, load data from A to OUT
        controls_list[15] = [AO|OI]
    elif al == 2:
        #sub#, sub A with next byte data
        controls_list[14] = [CO|MI, RO|BI|CE, L2|AI]
        #inc, add 1 to the A register
        controls_list[15] = [L1|L2|AI]
    elif al == 3:
        #and#, and A with next byte data
        controls_list[14] = [CO|MI, RO|BI|CE, L1|L3|AI]
        #dec, sub 1 to the A register
        controls_list[15] = [L3|AI]
    elif al == 4:
        #or#, or A with next byte data
        controls_list[14] = [CO|MI, RO|BI|CE, L2|L3|AI]
        #rshift, shift A register right
        controls_list[15] = [L4|AI]
    elif al == 5:
        #ldib, load B with next byte data
        controls_list[14] = [CO|MI, RO|BI|CE]
        #lshift, shift A register left
        controls_list[15] = [L1|L4|AI]
    elif al == 6:
        #multl#, mult A with next byte data, store lower 8 bits in A
        controls_list[14] = [CO|MI, RO|BI|CE, L2|L4|AI]
        #take, move B register content to A register
        controls_list[15] = [BO|AI]
    elif al == 7:
        #multh#, mult A with next byte data, store higher 8 bits in A
        controls_list[14] = [CO|MI, RO|BI|CE, L1|L2|L4|AI]
        #pusha, load data from A to top of stack
        controls_list[15] = [AO|SI]
    elif al == 8:
        #push#, push next byte data onto stack
        controls_list[14] = [CO|MI, RO|SI|CE]
        #popa, load data from top of stack to A
        controls_list[15] = [SO|AI]
    elif al == 9:
        #xor#, xor A with next byte data
        controls_list[14] = [CO|MI, RO|BI|CE, L3|L4|AI]
        #move, move A register content to B register
        controls_list[15] = [AO|BI]
    elif al == 10:
        #ret#
        controls_list[14] = [CO|MI, RO|AI|SO|JP|SA]
        #ret
        controls_list[15] = [SO|JP|SA]
    elif al == 11:
        #scp, set screen pointer to next byte data
        controls_list[14] = [CO|MI, RO|PI|RF|CE]
        #hlta, halt and output A register content
        controls_list[15] = [AO|OI, HT]
    elif al == 12:
        #
        controls_list[14] = []
        #not, inverts A register bits
        controls_list[15] = [L1|L2|L3|AI]
    elif al == 13:
        #
        controls_list[14] = []
        #refresh, refresh the screen
        controls_list[15] = [RF]
    elif al == 14:
        #
        controls_list[14] = []
        #incb, add 1 to B register
        controls_list[15] = [L1|L2|BI]
    elif al == 15:
        #halt#, halt and outputs next byte data
        controls_list[14] = [CO|MI, RO|OI|CE, HT]
        #halt
        controls_list[15] = [HT]
        
    for controls in controls_list:
        doc.write(fetch1)
        doc.write(fetch2)
        for control in controls:
            doc.write(bin(control)[2:].rjust(CS_NUM, '0') + '\n')
        for i in range(6 - len(controls)):
            doc.write('0'.rjust(CS_NUM, '0') + '\n')

if __name__ == '__main__':
    print('[                ]', end='\r')

    for flags in range(1 << FLAGS_NUM):
        for al in range(16):
            writeROM(flags, al)
        # sleep(0.1)
        print('['+ ('=='*(flags+1)).ljust(1<<(FLAGS_NUM+1), ' ') + ']', end='\r')

    print("\nDone.")

doc.close()