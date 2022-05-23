import sys
import argparse
from xml.etree import ElementTree
import re
import operator

class Instruction:
    def __init__(self, opcode, order):
        self.type = opcode
        try:
            self.order = int(order)
        except ValueError:
            exit(32, "Value error")
        self.args = []

    def add_argument(self, arg_type, arg_value, tag):
        tag = tag.split("arg")[1]
        self.args.append(Argument(arg_type, arg_value, tag))
        self.args.sort(key=operator.attrgetter("tag"))

class Argument:
    def __init__(self, arg_type, arg_value, tag):
        self.type = arg_type
        self.value = arg_value
        self.tag = tag

class Framestack:
    def __init__(self):
        self.frames = []

    def pushframe(self, frame):
        if frame.type != "GF" and frame.type != "null":
            frame.type = "LF"
            for var in frame.vars:
                var.frame = "LF"
        self.frames.append(frame)

    def popframe(self):
        frame = self.frames.pop()
        if frame.type == "null":
            return None
        elif frame.type != "GF":
            frame.type = "TF"
            for var in frame.vars:
                var.frame = "TF"
        return frame

    def getvar(self, name, frametype):
        for frame in reversed(self.frames):
            if frame.type != frametype:
                continue
            var = frame.getvar(name)
            if var is not None:
                return var
        return None

    def isglobal(self, varname):
        for frame in self.frames:
            if frame.getvar(varname) is not None:
                if frame.type == "GF":
                    return True
                else:
                    return False

    def updatevar(self, var, frametype):
        for frame in self.frames:
            if frame.getvar(var.name) is not None and frame.type == frametype:
                frame.updatevar(var)
                return True
        return False

class Frame:
    def __init__(self, type):
        self.type = type
        self.vars = []

    def defvar(self, name, frame):
        if frame != self.type:
            exit(55, "Temporary frame doesn't exist")
        self.vars.append(Variable(name, self.type))

    def getvar(self, name):
        for var in self.vars:
            if var.name == name:
                return var
        return None

    def updatevar(self, newvar):
        for var in self.vars:
            if var.name == newvar.name:
                var = newvar
                return True
        return False

class Variable:
    def __init__(self, name, frame):
        self.type = None
        self.name = name
        self.frame = frame
        self.value = None

    def check_type(self):
        if self.type is not None:
            self.type = self.type.lower()

        if self.type == "int":
            try:
                int(self.value)
                self.value = str(self.value)
            except ValueError:
                exit(32, "Value Error")
        elif self.type == "bool":
            try:
                bool(self.value)
                self.value = str(self.value).lower()
            except ValueError:
                exit(32, "Value Error")
        elif self.type == "nil":
            if self.value != "nil":
                exit(32, "Value Error")

class LabelList:
    def __init__(self):
        self.labels = []

    def add_label(self, label):
        self._checkorigin(label.name)
        self.labels.append(label)

    def get_label(self, name):
        for label in self.labels:
            if label.name == name:
                return label
        exit(52, "Undefined Label")

    def load_labels(self, instructions):
        for instr in instructions:
            if instr.type == "LABEL":
                arg_count(instr.args, 1)
                name = instr.args[0].value
                order = instr.order
                self.add_label(Label(name, order))

    def _checkorigin(self, name):
        for label in self.labels:
            if label.name == name:
                exit(52, "LABEL two labels with the same name")

class Label:
    def __init__(self, name, order):
        self.name = name
        self.order = int(order)

class Stack:
    def __init__(self):
        self.vars = []

    def push(self, type, value):
        self.vars.append(Symbol(type, value))

    def pop(self):
        if len(self.vars) == 0:
            exit(56, "POPS stack is empty")
        return self.vars.pop()

class Symbol:
    def __init__(self, type, value):
        self.type = type.lower()
        self.value = value


def exit(code, msg):
    print("ERROR: " + msg, file=sys.stderr)
    sys.exit(code)

def check_regex(exp, type):
    type = type.lower()
    if type == "var":
        if not re.match(r"^(TF|GF|LF)@[a-zA-Z!$%&*_\-?][a-zA-Z0-9!$%&*_\-?]*$", exp):
            exit(32, "Variable regex doesn't match")
    elif type == "string":
        if not re.match(r"^([^#\s\\]|\\\d{3})*$", exp):
            exit(32, "String regex doesn't match")
    elif type == "int":
        if not re.match(r"^(\+|\-)?[0-9]+$", exp):
            exit(32, "Integer regex doesn't match")
    elif type == "bool":
        if not re.match(r"^(true|false)$", exp.lower()):
            exit(32, "Bool regex doesn't match")
    elif type == "type":
        if not re.match(r"^(int|string|bool)$", exp.lower()):
            exit(32, "Type regex doesn't match")
    elif type == "label":
        if not re.match(r"^[a-zA-Z!$%&*_\-?][a-zA-Z0-9!$%&*_\-?]*$", exp):
            exit(32, "Label regex doesn't match")
    elif type == "nil":
        if not re.match(r"^nil$", exp.lower()):
            exit(32, "Nil regex doesn't match")
    else:
        exit(32, "Unexpected Argument Type")

def check_order(instructions):
    i = 0
    for instr in instructions:
        i += 1
        if len(instructions) > i:
            if instr.order == instructions[i].order:
                exit(32, "Duplicit order")
            if int(instr.order) <= 0:
                exit(32, "Negative order")
        instr.order = i

def type_check(arg1, arg2, types):
    if arg1 != arg2:
        exit(53, "Data types don't match")
    if len(types) == 0:
        return
    for type in types:
        if type == arg1:
            return
    exit(53, "Invalid data types")

def getvar(arg, frame, stack):
    try:
        frametype, name = arg.value.split("@", 1)
    except ValueError:
        exit(32, "Value Error")
    if frametype == "TF":
        if frame is None or frame.type == "GF":
            exit(55, "Frame doesn't exist")
        var = frame.getvar(name)
        if var is None:
            exit(54, "Variable doesn't exist")
    else:
        if frame is not None and frame.type == "GF" and frametype == "GF":
            var = frame.getvar(name)
            if var is None:
                exit(54, "Variable doesn't exist")
            return var
        if len(stack.frames) <= 2:
            exit(55, "Frame doesn't exist")
        var = stack.getvar(name, frametype)
        if var is None:
            exit(54, "Variable doesn't exist")
    return var

def updatevar(var, frame, stack):
    var.check_type()
    if var.frame == "TF":
        if not frame.updatevar(var):
            exit(54, "Variable doesn't exist")
    else:
        if frame.type == "GF" and var.frame == "GF":
            if not frame.updatevar(var):
                exit(54, "Variable doesn't exist")
            return
        if not stack.updatevar(var, var.frame):
            exit(54, "Variable doesn't exist")

def getvalue(arg, frame, stack):
    if arg.type == "var":
        value = getvar(arg, frame, stack).value
        if value is None:
            exit(56, "No value")
        return value
    else:
        typ = gettype(arg, frame, stack)
        var = Variable("name", "")
        var.value = arg.value
        var.type = typ
        var.check_type()
        if arg.value is None:
            exit(56, "No value")
        return arg.value

def gettype(arg, frame, stack):
    if arg.type == "var":
        return getvar(arg, frame, stack).type
    else:
        return arg.type

def arg_count(args, expected):
    if len(args) != expected:
        exit(32, "Invalid number of arguments")

def arg_parse():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", nargs=1, help="XML Source File")
    parser.add_argument("--input", nargs=1, help="Input file")

    args = parser.parse_args()

    if args.source is None and args.input is None:
        exit(32, "Both arguments missing")

    if args.source is None:
        return sys.stdin, args.input[0]
    elif args.input is None:
        return args.source[0], sys.stdin

    return args.source[0], args.input[0]

def xml_parse(tree):
    root = tree.getroot()
    instructions = []

    if root.tag != "program":
        exit(32, "Invalid XML root element")

    for elem in root:
        if elem.tag != "instruction":
            exit(32, "Invalid XML instruction")

        attr = elem.attrib.keys()

        if "opcode" not in attr or "order" not in attr:
            exit(32, "Invalid XML instruction")

        order, opcode = elem.attrib["order"], elem.attrib["opcode"]
        instr = Instruction(opcode, order)

        for arg in elem:
            if not re.match(r"arg\d", arg.tag):
                exit(32, "Invalid XML argument")
            type, value = arg.attrib["type"], arg.text
            try:
                type = str(type).lower()
                value = str(value)
            except TypeError:
                exit(32, "Type Error")
            check_regex(value, type)
            if type == "string":
                value = re.sub(r"\\([0-9][0-9][0-9])", lambda tmp: chr(int(tmp.group(1))), str(value))
            instr.add_argument(type, value, arg.tag)

        i = 0
        for arg in instr.args:
            i += 1
            if arg.tag != str(i):
                exit(32, "Argument missing")

        instructions.append(instr)

    return instructions

def interpret(instructions, inputfile):
    stack = Framestack()
    stack.pushframe(Frame("null"))
    frame = Frame("GF")
    labels = LabelList()
    labels.load_labels(instructions)
    datastack = Stack()
    calls = []
    iter = 0
    instr = instructions[0]
    while instr:
        instr.type = instr.type.upper()
        if instr.type == "MOVE":
            arg_count(instr.args, 2)
            var = getvar(instr.args[0], frame, stack)
            value = getvalue(instr.args[1], frame, stack)
            typ = gettype(instr.args[1], frame, stack)
            var.value = value
            var.type = typ
            updatevar(var, frame, stack)
        elif instr.type == "CREATEFRAME":
            arg_count(instr.args, 0)
            if frame is not None and frame.type == "GF":
                stack.pushframe(frame)
            frame = Frame("TF")
        elif instr.type == "PUSHFRAME":
            arg_count(instr.args, 0)
            if frame is None or frame.type == "GF":
                exit(55, "PUSHFRAME undefined frame")
            stack.pushframe(frame)
            frame = None
        elif instr.type == "POPFRAME":
            arg_count(instr.args, 0)
            frame = stack.popframe()
            if frame is None:
                exit(55, "POPFRAME nonexistent frame")
        elif instr.type == "DEFVAR":
            arg_count(instr.args, 1)
            if frame is None:
                exit(55, "DEFVAR undefined frame")
            if frame.getvar(instr.args[0].value.split("@", 1)[1]) is not None:
                exit(52, "DEFVAR redefining a variable")
            frame.defvar(instr.args[0].value.split("@", 1)[1], instr.args[0].value.split("@", 1)[0])
        elif instr.type == "CALL":
            arg_count(instr.args, 1)
            calls.append(instr.order - 1)
            name = instr.args[0].value
            iter = labels.get_label(name).order - 1
        elif instr.type == "RETURN":
            arg_count(instr.args, 0)
            if len(calls) == 0:
                exit(56, "RETURN Return without call")
            iter = calls.pop()
        elif instr.type == "PUSHS":
            arg_count(instr.args, 1)
            typ = gettype(instr.args[0], frame, stack)
            value = getvalue(instr.args[0], frame, stack)
            datastack.push(typ, value)
        elif instr.type == "POPS":
            arg_count(instr.args, 1)
            var = getvar(instr.args[0], frame, stack)
            pop = datastack.pop()
            var.type = pop.type
            var.value = pop.value
            updatevar(var, frame, stack)
        elif \
        instr.type == "ADD" or \
        instr.type == "SUB" or \
        instr.type == "MUL" or \
        instr.type == "IDIV":
            arg_count(instr.args, 3)
            type1 = gettype(instr.args[1], frame, stack)
            type2 = gettype(instr.args[2], frame, stack)
            value1 = getvalue(instr.args[1], frame, stack)
            value2 = getvalue(instr.args[2], frame, stack)
            type_check(type1, type2, ["int"])
            var = getvar(instr.args[0], frame, stack)
            if instr.type == "ADD":
                var.value = int(value1) + int(value2)
            elif instr.type == "SUB":
                var.value = int(value1) - int(value2)
            elif instr.type == "MUL":
                var.value = int(value1) * int(value2)
            elif instr.type == "IDIV":
                if int(value2) == 0:
                    exit(57, "IDIV divison by zero")
                var.value = int(value1) / int(value2)
            var.value = int(var.value)
            var.type = "int"
            updatevar(var, frame, stack)
        elif \
        instr.type == "LT" or \
        instr.type == "GT" or \
        instr.type == "EQ":
            arg_count(instr.args, 3)
            type1 = gettype(instr.args[1], frame, stack)
            type2 = gettype(instr.args[2], frame, stack)
            value1 = getvalue(instr.args[1], frame, stack)
            value2 = getvalue(instr.args[2], frame, stack)
            type_check(type1, type2, ["int", "bool", "string"])
            var = getvar(instr.args[0], frame, stack)
            if instr.type == "LT":
                if type1 == "int":
                    var.value = int(value1) < int(value2)
                elif type1 == "bool":
                    var.value = bool(value1) < bool(value2)
                elif type1 == "string":
                    var.value = value1 < value2
            elif instr.type == "GT":
                if type1 == "int":
                    var.value = int(value1) > int(value2)
                elif type1 == "bool":
                    var.value = bool(value1) > bool(value2)
                elif type1 == "string":
                    var.value = value1 > value2
            elif instr.type == "EQ":
                if type1 == "int":
                    var.value = int(value1) == int(value2)
                elif type1 == "bool":
                    var.value = bool(value1) == bool(value2)
                elif type1 == "string":
                    var.value = value1 == value2
            var.type = "bool"
            updatevar(var, frame, stack)
        elif \
        instr.type == "AND" or \
        instr.type == "OR":
            arg_count(instr.args, 3)
            type_check(gettype(instr.args[1], frame, stack), gettype(instr.args[2], frame, stack), ["bool"])
            var = getvar(instr.args[0], frame, stack)
            value1 = getvalue(instr.args[1], frame, stack)
            value2 = getvalue(instr.args[2], frame, stack)
            if instr.type == "AND":
                var.value = bool(value1) and bool(value2)
            elif instr.type == "OR":
                var.value = bool(value1) or bool(value2)
            var.type = "bool"
            updatevar(var, frame, stack)
        elif instr.type == "NOT":
            arg_count(instr.args, 2)
            var = getvar(instr.args[0], frame, stack)
            if gettype(instr.args[1], frame, stack) != "bool":
                exit(53, "Invalid data type")
            var.value = not bool(getvalue(instr.args[1], frame, stack))
            var.type = "bool"
            updatevar(var, frame, stack)
        elif instr.type == "INT2CHAR":
            arg_count(instr.args, 2)
            var = getvar(instr.args[0], frame, stack)
            value = getvalue(instr.args[1], frame, stack)
            if gettype(instr.args[1], frame, stack) != "int":
                exit(53, "Invalid data type")
            try:
                var.value = chr(int(value))
            except ValueError:
                exit(58, "INT2CHAR unicode out of range")
            var.type = "string"
            updatevar(var, frame, stack)
        elif instr.type == "STRI2INT":
            arg_count(instr.args, 3)
            var = getvar(instr.args[0], frame, stack)
            index = getvalue(instr.args[2], frame, stack)
            value = getvalue(instr.args[1], frame, stack)
            if gettype(instr.args[2], frame, stack) != "int" or gettype(instr.args[1], frame, stack) != "string":
                exit(53, "Invalid data type")
            if len(value) <= index:
                exit(58, "STRI2INT index out of range")
            var.value = ord(value[int(index)])
            var.type = "int"
            updatevar(var, frame, stack)
        elif instr.type == "READ":
            arg_count(instr.args, 2)
            var = getvar(instr.args[0], frame, stack)
            typ = instr.args[1].value
            if typ != "string" and typ != "int" and typ != "bool":
                exit(32, "READ wrong type argument")
            try:
                value = input()
            except Exception:
                value = "nil"
                typ = "nil"
            if typ == "bool":
                if value != "true":
                    value = "false"
            var.type = typ
            var.value = value
            updatevar(var, frame, stack)
        elif instr.type == "WRITE":
            arg_count(instr.args, 1)
            arg = instr.args[0]
            typ = gettype(arg, frame, stack)
            value = getvalue(arg, frame, stack)
            if value is None:
                exit(56, "WRITE Missing value")
            elif typ == "nil":
                print("", end='')
            elif typ == "bool":
                print(str(value).lower(), end='')
            elif typ == "string":
                print(value, end='')
            else:
                value = str(value)
                print(value, end='')
        elif instr.type == "CONCAT":
            arg_count(instr.args, 3)
            type_check(gettype(instr.args[1], frame, stack), gettype(instr.args[2], frame, stack), ["string"])
            value1 = getvalue(instr.args[1], frame, stack)
            value2 = getvalue(instr.args[2], frame, stack)
            var = getvar(instr.args[0], frame, stack)
            var.value = value1 + value2
            var.type = "string"
            updatevar(var, frame, stack)
        elif instr.type == "STRLEN":
            arg_count(instr.args, 2)
            if gettype(instr.args[1], frame, stack) != "string":
                exit(53, "Invalid data type")
            var = getvar(instr.args[0], frame, stack)
            value = getvalue(instr.args[1], frame, stack)
            var.value = len(value)
            var.type = "int"
            updatevar(var)
        elif instr.type == "GETCHAR":
            arg_count(instr.args, 3)
            var = getvar(instr.args[0], frame, stack)
            type1 = gettype(instr.args[1], frame, stack)
            type2 = gettype(instr.args[2], frame, stack)
            index = getvalue(instr.args[2], frame, stack)
            value = getvalue(instr.args[1], frame, stack)
            if type1 != "int" or type2 != "string":
                exit(53, "Invalid data type")
            if len(value) <= index:
                exit(58, "GETCHAR index out of range")
            var.value = value[index]
            var.type = "string"
            updatevar(var, frame, stack)
        elif instr.type == "SETCHAR":
            arg_count(instr.args, 3)
            var = getvar(instr.args[0], frame, stack)
            type1 = gettype(instr.args[1], frame, stack)
            type2 = gettype(instr.args[2], frame, stack)
            index = getvalue(instr.args[1], frame, stack)
            value = getvalue(instr.args[2], frame, stack)
            if type1 != "int" or type2 != "string" or var.type != "string":
                exit(53, "Invalid data type")
            if len(value) <= index:
                exit(58, "SETCHAR index out of range")
            value[index] = var
            var.value = value
            updatevar(var, frame, stack)
        elif instr.type == "TYPE":
            arg_count(instr.args, 2)
            var = getvar(instr.args[0], frame, stack)
            typ = gettype(instr.args[1], frame, stack)
            if typ is None:
                typ = ""
            var.value = typ
            var.type = "string"
        elif instr.type == "LABEL":
            pass
        elif instr.type == "JUMP":
            arg_count(instr.args, 1)
            label = labels.get_label(instr.args[0].value)
            iter = label.order - 1
        elif \
        instr.type == "JUMPIFEQ" or \
        instr.type == "JUMPIFNEQ":
            arg_count(instr.args, 3)
            label = labels.get_label(instr.args[0].value)
            type1 = gettype(instr.args[1], frame, stack)
            type2 = gettype(instr.args[2], frame, stack)
            value1 = getvalue(instr.args[1], frame, stack)
            value2 = getvalue(instr.args[2], frame, stack)
            type_check(type1, type2, [])
            if instr.type == "JUMPIFEQ":
                if str(value1) == str(value2):
                    iter = label.order - 1
            elif instr.type == "JUMPIFNEQ":
                if str(value1) != str(value2):
                    iter = label.order - 1
        elif instr.type == "EXIT":
            arg_count(instr.args, 1)
            if gettype(instr.args[0], frame, stack) != "int":
                exit(53, "Invalid data type")
            value = getvalue(instr.args[0], frame, stack)
            if int(value) >= 0 and int(value) <= 49:
                sys.exit(int(value))
            else:
                exit(57, "EXIT incorrect exit code")
        elif instr.type == "DPRINT":
            arg_count(instr.args, 1)
            print(getvalue(instr.args[0], frame, stack), file=sys.stderr)
        elif instr.type == "BREAK":
            arg_count(instr.args, 0)
            print(f"Current instruction: {instr.order}", file=sys.stderr)
        else:
            exit(32, "Invalid instruction")
        if len(instructions) < (iter + 2):
            break
        iter = iter + 1
        instr = instructions[iter]


if __name__ == "__main__":
    src, inputfile = arg_parse()
    if inputfile != sys.stdin:
        stdin = sys.stdin
        sys.stdin = open(f"{inputfile}", "r")
    try:
        tree = ElementTree.parse(src)
    except Exception:
        exit(31, "Invalid XML structure")
    instructions = xml_parse(tree)
    instructions.sort(key=operator.attrgetter("order"))
    check_order(instructions)
    interpret(instructions, inputfile)
