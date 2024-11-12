#https://eater.net/8bit/pc
from cpu import *
from time import perf_counter, sleep
from pathlib import Path
__version__ = "1.1.2"
__last_update__ = "Nov. 3rd 2024"

#Assemble the program
OPS = {
    #ops with address arguments
    "lda"   : 0x00, "add"   : 0x10, "sub"   : 0x20, "sta"   : 0x30,
    "jsr"   : 0x40, "jump"  : 0x50, "jmpc"  : 0x60, "jmpz"  : 0x70,
    "jmpn"  : 0x80, "and"   : 0x90, "or"    : 0xa0, "ldax"  : 0xb0,
    "multl" : 0xc0, "multh" : 0xd0,#(1)     : 0xe+, (2)     : 0xf+
    #ops with numerical arguments (1)
    "ldi"   : 0xe0, "add#"  : 0xe1, "sub#"  : 0xe2, "and#"  : 0xe3,
    "or#"   : 0xe4, "ldib"  : 0xe5, "multl#": 0xe6, "multh#": 0xe7,
    "push#" : 0xe8, "xor#"  : 0xe9, "ret#"  : 0xea, "scp"   : 0xeb,
    "TBA"   : 0xec, "TBA"   : 0xed, "TBA"   : 0xee, "halt#" : 0xef,
    #ops w/o arguments (monos)    (2)
    "noop"  : 0xf0, "out"   : 0xf1, "inc"   : 0xf2, "dec"   : 0xf3,
    "rsh"   : 0xf4, "lsh"   : 0xf5, "take"  : 0xf6, "pusha" : 0xf7,
    "popa"  : 0xf8, "move"  : 0xf9, "ret"   : 0xfa, "hlta"  : 0xfb,
    "not"   : 0xfc,"refresh": 0xfd, "incb"  : 0xfe, "halt"  : 0xff
}

#Token is a named entity (variable or function), not an operation
class Token:
    def __init__(self, name, addr):
        self.name = name
        self.addr = 0 if name == "start" else addr
        self.content = [] #data or ops as numbers
        self.contentstr = [] #data or ops as strings (for printing)
    def __str__(self):
        string = f"<{self.name}> at {self.addr} contains ["
        for i in range(min(len(self.contentstr), 5)):
            string += self.contentstr[i] + ", "
        if len(self.contentstr) == 6:
            return string + self.contentstr[5] + ']'
        elif len(self.contentstr) > 6:
            return string + "...]"
        else:
            return string[:-2] + ']'

def number(arg: str):
    if arg.isdecimal() or (arg[0] == '-' and arg[1:].isdecimal()): #decimal
        return int(arg)
    elif arg[0] == '$': #hexadecimal
        return int(arg[1:], 16)
    elif arg[0] == '%': #binary
        return int(arg[1:], 2)
    elif arg[0] == '"' and arg.endswith('"') and not arg.endswith('\\"'):
        num = 0
        string = arg[1:-1].encode("utf-8").decode("unicode_escape")
        for i, char in enumerate(string):
            num |= ord(char) << (i << 3)
        return num
    else:
        return None
    
def num2byte(num: int) -> list[int]:
    if num < 255:
        return [num & 255]
    bytes = []
    while num > 255:
        bytes.append(num & 255)
        num >>= 8
    bytes.append(num)
    return bytes

def split(string: str) -> list[str]:
    string = string.replace('\\"', '\\\\"').encode("utf-8").decode("unicode_escape")
    output = [""]
    string_form = False
    for char in string:
        if char in [' ', '\t', '\n', '\r'] and not string_form:
            if output[-1] != "":
                output.append("")
        elif char == '"' and not output[-1].endswith('\\'):
            output[-1] += char
            string_form = not string_form
        else:
            output[-1] += char
    return output[:-1] if output[-1] == "" else output
        
def run_program(lines: list[str], *special_mode):
    data_section = True
    program_ends = False
    tokenList: list[Token] = []
    refList: list[Token] = [] #list of references for jumps (*here and &here)
    mem_ptr = RAM_SIZE #memory pointer starts at the end and moves back
    start = perf_counter()

    #Create line pointers
    line_ptr = [0] * len(lines)
    start_section = False
    section = []
    for l, line in enumerate(lines):
        #remove empty lines or comment lines
        if line.strip() == '' or line.strip()[0] == '/': continue

        #remove end-of-line comments
        comment = line.find('/')
        if comment != -1:
            line = line[:comment].strip()
        
        #create references
        ref = len(line) - line[::-1].find('*') - 1
        if ref != len(line) and line.find('"', ref) == -1:
            valid = len(split(line[ref:])) == 1 and line[ref:][1].isalpha()
            assert valid, f"[line {l+1}] Invalid reference <{line[ref+1:-1]}>"
            name = split(line)[-1][1:]
            refList.append(Token(name, l+1))
            refList[-1].content.append(mem_ptr)
            refList[-1].contentstr.append(str(mem_ptr))

        #check if line is a new function
        if split(line)[0].endswith(':'):
            data_section = False
            ptr = mem_ptr
            if len(section) != 0:
                for k, offset in enumerate(section):
                    line_ptr[section[0] + k] = ptr
                    if k == 0: continue
                    for ref in refList:
                        if ref.addr-1 == section[0] + k:
                            ref.content[0] = ptr
                            ref.contentstr[0] = str(ptr)
                    ptr += offset
                for ref in refList:
                    if ref.addr-1 == section[0]:
                        ref.content[0] = line_ptr[section[0]]
                        ref.contentstr[0] = str(line_ptr[section[0]])
            section = [l]
            if line == "start:\n":
                if len(refList) != 0:
                    if refList[-1].addr == l:
                        refList[-1].content[0] = 0
                        refList[-1].contentstr[0] = '0'
                mem_ptr = 0
                start_section = True
            
        #data section
        elif data_section:
            args = split(line)
            arg0 = number(args[0])
            if arg0 == None:
                if len(args) < 3:
                    line_ptr[l] = mem_ptr - 1
                    mem_ptr -= 1
                else:
                    size = 0
                    for i in range(2, len(args)):
                        try:
                            size += len(num2byte(number(args[i])))
                        except:
                            size += 1 #error here
                    line_ptr[l] = mem_ptr - size
                    mem_ptr -= size

            #rest of the cases    
            else:
                line_ptr[l] = arg0
            if len(refList) != 0 and refList[-1].addr == l+1:
                refList[-1].content = [line_ptr[l]]
                refList[-1].contentstr = [str(line_ptr[l])]
            

        #start function section
        elif start_section:
            line_ptr[l] = mem_ptr
            mem_ptr += 2 if OPS[split(line)[0]] < 0xf0 else 1

        #other function sections
        else:
            section.append(2 if OPS[split(line)[0]] < 0xf0 else 1)
            mem_ptr -= 2 if OPS[split(line)[0]] < 0xf0 else 1

    if special_mode[0]:
        print("[Debugger] Line pointers: ")
        for l, line in enumerate(lines):
            if l+1 == len(lines):
                print(f"    line {l+1} -> {line_ptr[l]}:\t{line.strip()}")
            else:
                print(f"    line {l+1} -> {line_ptr[l]}:\t{line[:-1].strip()}")
        if len(refList) == 0:
            print()
        else:
            print("[Debugger] Ref list: ")
            for ref in refList:
                print(f"    {ref}")

    #Create program tokens
    data_section = True
    mem_ptr = RAM_SIZE - 1
    for l, line in enumerate(lines):
        #remove empty lines or comment lines
        if line.strip() == '' or line.strip()[0] == '/': continue

        #remove end-of-line comments
        comment = line.find('/')
        if comment != -1:
            line = line[:comment].strip()
        
        #remove line references
        ref = len(line) - line[::-1].find('*') - 1
        if ref != len(line) and line.find('"', ref) == -1:
            line = line[:ref].strip()

        args = split(line)

        #function section begin, creates a function token
        if args[0].endswith(':'):
            assert args[0][0].isalpha(), f"[line {l+1}] Invalid declaration <{args[0]}>"
            data_section = False
            tokenList.insert(0, Token(args[0].strip(':'), mem_ptr + 1))

        #data section
        elif data_section:
            #if an address is given
            arg0 = number(args[0])
            if type(arg0) == int:
                assert len(args) != 1, f"[line {l+1}] Unexpected <{args[0]}>"
                arg1 = number(args[1])

                #data starts with 2 numbers
                if type(arg1) == int:
                    #set data at a nameless address (ex.: $2ea %10010010)
                    if len(args) == 2:
                        for i, byte in enumerate(num2byte(arg1)):
                            RAM.mem[arg0 + i].equal(byte)

                    #set multiple data to a range of addresses (ex.: $100 $200 x = 1500 3200)
                    else:
                        assert args[2][0].isalpha(), f"[line {l+1}] Invalid declaration <{args[0]}>"
                        tokenList.insert(0, Token(args[2], arg0))
                        if len(args) > 3:
                            assert args[3] == '=', f"[line {l+1}] Syntax error expected '='"
                            assert len(args) > 4, f"[line {l+1}] Expected data after '='"
                            for i in range(4, len(args)):
                                num = number(args[i])
                                assert type(num) == int, f"[line {l+1}] Invalid initialization <{args[i]}>"
                                num = num2byte(num)
                                for byte in num:
                                    tokenList[0].content.append(byte)
                                    tokenList[0].contentstr.append(str(byte))
                        empty_len = 1 + arg1 - arg0 - len(tokenList[0].content)
                        tokenList[0].content += [0] * (empty_len)
                        tokenList[0].contentstr += ["<Empty>"] * (empty_len)
                
                #set data to named address
                else:
                    assert args[1][0].isalpha(), f"[line {l+1}] Invalid declaration <{args[0]}>"
                    tokenList.insert(0, Token(args[1], arg0))
                    if len(args) == 2:
                        tokenList[0].content.append(0)
                        tokenList[0].contentstr.append("<Empty>")
                    else:
                        assert args[2] == '=', f"[line {l+1}] Syntax error expected '='"
                        assert len(args) > 3, f"[line {l+1}] Expected data after '='"
                        for i in range(3, len(args)):
                            num = number(args[i])
                            assert type(num) == int, f"[line {l+1}] Invalid initialization <{args[i]}>"
                            num = num2byte(num)
                            for byte in num:
                                tokenList[0].content.append(byte)
                                tokenList[0].contentstr.append(str(byte))


            #if an addressless-variable is declared
            else:
                assert args[0][0].isalpha(), f"[line {l+1}] Invalid declaration <{args[0]}>"
                tokenList.insert(0, Token(args[0], mem_ptr))
                if len(args) == 1:
                    tokenList[0].content.append(0)
                    tokenList[0].contentstr.append("<Empty>")
                    mem_ptr -= 1
                else:
                    tokenList[0].addr += 1
                    assert args[1] == '=', f"[line {l+1}] Syntax error expected '='"
                    assert len(args) > 2, f"[line {l+1}] Expected data after '='"
                    for i in range(2, len(args)):
                        num = number(args[i])
                        assert type(num) == int, f"[line {l+1}] Invalid initialization <{args[i]}>"
                        num = num2byte(num)
                        for byte in num:
                            tokenList[0].content.append(byte)
                            tokenList[0].contentstr.append(str(byte))
                            tokenList[0].addr -= 1
                            mem_ptr -= 1

        #if data section is complete, add ops to function token
        else:
            tokenList[0].content.append(OPS[args[0]])
            OPS_LEN = 2 if OPS[args[0]] < 0b11110000 else 1
            assert OPS_LEN == len(args), f"[line {l+1}] Incorrect use of <{args[0]}>"
            tokenList[0].contentstr.append(' '.join(split(line)))

            #want to know if the program is intended to loop or not
            program_ends |= args[0] in ["halt", "hlta", "halt#"]

            #ops with number arguments
            if 0xf0 > OPS[args[0]] >= 0xe0:
                assert len(args) == 2, f"[line {l+1}] Incorrect use of <{args[0]}>"
                tokenList[0].content.append(number(args[1]) & 255)
                if tokenList[0].name != "start":
                    tokenList[0].addr -= 1
                    mem_ptr -= 1

            #ops with address arguments
            elif 0xe0 > OPS[args[0]]:
                assert len(args) == 2, f"[line {l+1}] Incorrect use of <{args[0]}>"
                #if second word is a number, store it directly as a number
                arg0 = number(args[1])
                if type(arg0) == int:
                    arg0 &= RAM_SIZE-1
                    tokenList[0].content[-1] += arg0 >> 8
                    tokenList[0].content.append(arg0 & 255)

                #line reference (ex.: l123 -> means to find the address at line 123)
                elif args[1][0].lower() == 'l' and args[1][1:].isdecimal():
                    arg0 = line_ptr[int(args[1][1:]) - 1]
                    tokenList[0].content[-1] += arg0 >> 8
                    tokenList[0].content.append(arg0 & 255)

                #line pointer reference (ex.: &&loop finds the address at 1 more than line marked *loop)
                elif args[1][0] == '&':
                    offset = 1
                    while args[1][offset:][0] == '&': offset += 1
                    invalid_ref = True
                    ref_named = args[1][offset:]

                    #if ref is known set value to corresponding line address
                    for ref in refList:
                        if ref.name == ref_named:
                            arg0 = ref.content[0] + offset - 1
                            tokenList[0].content[-1] += arg0 >> 8
                            tokenList[0].content.append(arg0 & 255)
                            invalid_ref = False

                    assert not invalid_ref, f"[line {l+1}] Invalid reference <{ref_named}>"

                #if second word has a name
                else:
                    invalid_token = True

                    #if word is a know token, add its address to token content
                    for l in range(1, len(tokenList)):
                        if tokenList[l].name == args[1]:
                            arg0 = tokenList[l].addr
                            tokenList[0].content[-1] += arg0 >> 8
                            tokenList[0].content.append(arg0 & 255)
                            invalid_token = False

                    #if word is an invalid token, create this token
                    if invalid_token:
                        assert tokenList[0].name != args[1], f"[line {l+1}] Invalid declaration <{args[1]}>"

                        #determine ram address of created token
                        if tokenList[0].name == "start":
                            invalid_token_addr = tokenList[1].addr - 1
                        else:
                            invalid_token_addr = tokenList[0].addr + len(tokenList[0].content) - 2
                            tokenList[0].addr -= 1

                        #add token at second to last in token list
                        tokenList.insert(1, Token(args[1], invalid_token_addr))
                        tokenList[1].content.append(None)
                        tokenList[1].contentstr.append("<Empty>")
                        arg0 = tokenList[1].addr
                        tokenList[0].content[-1] += arg0 >> 8
                        tokenList[0].content.append(arg0 & 255)

                if tokenList[0].name != "start":
                    tokenList[0].addr -= 1
                    mem_ptr -= 1
            if tokenList[0].name != "start":
                tokenList[0].addr -= 1
                mem_ptr -= 1
        assert mem_ptr > 0, "Program unable to fit in memory"

    #Write program to RAM
    mem_ptr = 0
    program_size = 0
    if len(tokenList) > 1:
        assert tokenList[1].addr >= len(tokenList[0].content), "Too many variable or declared function after start"
    for token in tokenList:
        if len(token.content) == 0: continue
        mem_ptr = token.addr
        for content in token.content:
            if type(content) is int:
                RAM.mem[mem_ptr].equal(content)
            program_size += 1
            mem_ptr += 1
        if special_mode[5] or special_mode[1]:
            print("[Asm]", token)
            if special_mode[1]:
                RAM.chunk(token.addr, token.addr + len(token.content) - 1)
    program_size = max(len(RAM), program_size)
    print(f"Compiled successfully ({round((perf_counter() - start)*1000,2)}ms)")
    print(f"Program size: {program_size} bytes ({round(program_size/RAM_SIZE*100,2)}%)\n")

    if special_mode[6]:
        print("Initializing Screen")
        SCREEN.on()

    #manual clock cycle mode
    if special_mode[4]:
        if input(" > ").lower() != "stop":
            while run(True, True, special_mode[0], special_mode[6]):
                if input("\n > ").lower() == "stop": break
        print("\n_________________________________                               \n"
              "OUT :", OUT,)

    #if program contains a halt (careful bc some programs might no end)
    elif program_ends:
        start = perf_counter()
        tick = 0
        while run(False, True, special_mode[0], special_mode[6]): tick += 1
        time = perf_counter() - start
        units = 1000 if time < 10 else 1
        print(f"_________________________________\n"
              f"Program execution: {time*units:.2f}{'ms' if time < 10 else 's'}, "
              f"{tick/time/1000:.2f}kHz\n"
              "OUT :", OUT)

    #program contains no loops
    else:
        l = 0
        while run(True, False, special_mode[0], special_mode[6]) and \
            (l<2**20 if special_mode[3] else l<2**14):
            if not special_mode[3]:
                sleep(0.03)
            l += 1
        print("_________________________________                               \n"
              "OUT :", OUT)

    if special_mode[2]:
        RAM.chunk(0x500,0x503)
        result = RAM.mem[0x500].uint()\
        | RAM.mem[0x501].uint() << 8  \
        | RAM.mem[0x502].uint() << 16 \
        | RAM.mem[0x503].uint() << 24
        print("Result:", result)
    #print(Gate.count, "logic gates used\n")

#if program is run as a main file ask for a file
if __name__ == "__main__":
    print(f'SBB Computer & SBBasm {__version__} by Charles Benoit ({__last_update__})')
    special_mode = [False] * 7
    program = input("Run >>> ").strip()

    #debug tools
    while True:
        match program[-2:]:
            case "-d":
                print("[Special mode] Debug enabled")
                special_mode[0] = True
            case "-r":
                print("[Special mode] RAM printing enabled")
                special_mode[1] = True
            case "-m":
                print("[Special mode] Show mult output enabled")
                special_mode[2] = True
            case "-f":
                print("[Special mode] Fast mode enabled")
                special_mode[3] = True
            case "-s":
                print("[Special mode] Manual clock enabled")
                special_mode[4] = True
            case "-t":
                print("[Special mode] Token printing enabled")
                special_mode[5] = True
            case "-v":
                print("[Special mode] Screen visuals enabled")
                special_mode[6] = True
            case _:
                print()
                break
        program = program[:-2].strip()

    cwd = str(Path.cwd())
    if program == "":
        program = cwd + "\\sbbasm_program_files\\program.sbbasm"
    elif program.endswith(".sbbasm"):
        if not program.__contains__(cwd):
            program = cwd + "\\sbbasm_program_files\\" + program
    else:
        program = cwd + "\\sbbasm_program_files\\" + program + ".sbbasm"
    program = open(program, "r")
    lines = program.readlines()
    program.close()
    run_program(lines, *special_mode)