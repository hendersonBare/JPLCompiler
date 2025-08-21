from environment import *
from tensorContraction import *

class Function:
    def __init__(self, name: str, code: list[str], stack_map, jump_parent, jump_children): # not sure of other necessary parameters
        #do we need to keep track of parents?
        self.name = name
        self.code = code
        self.stack_map = stack_map
        self.jump_parent = jump_parent
        self.jump_children = jump_children
        self.processed = False

class Assembly:
    def __init__(self, constants, linkage_cmds: list[str], fns: list[Function], stack, stack_map, opt_level: int):
        self.constants = constants
        self.linkage_cmds = linkage_cmds
        self.fns = fns
        self.name_ctr = 0
        self.jump_ctr = 1
        self.stack = stack
        self.stack_map = stack_map
        self.opt_level = opt_level
    def gensym_const(self):
        ret_val = f"const{self.name_ctr}"
        self.name_ctr += 1
        return ret_val
    def add_const(self, name, type, value, int_or_float):
        self.constants[(value, int_or_float)] = (name, type)
    def gen_jump(self):
        name = f".jump{self.jump_ctr}"
        self.jump_ctr += 1
        return name

class Stack:
    def __init__(self, padding: list[int]):
        self.size = 8
        self.padding = padding
    def push(self, fn, name):
        fn.code.append(f"push {name}")
        self.size += 8
    def pop(self, fn, name):
        fn.code.append(f"pop {name}")
        self.size -= 8
    def align(self, fn, padding):
        fn.code.append(f"sub rsp, {padding} ; Add alignment")
        self.padding.append(padding)
        self.size += padding
    def unalign(self, fn):
        padding = self.padding.pop()
        if padding != 0:
            fn.code.append(f"add rsp, {padding} ; Remove alignment")
            self.size -= padding
    def free(self, fn, size):
        fn.code.append(f"add rsp, {size} ; Free local variables")
        self.size -= size

def add_lvalue(lval, fn, program, base):
    if type(lval) is VariableLvalue:
        fn.stack_map[lval.variable] = base
        if fn.name == "_jpl_main" or fn.name.startswith(".jump"):
            program.stack_map[lval.variable] = base
    elif type(lval) is ArrayLvalue:
        if fn.name == "_jpl_main" or fn.name.startswith(".jump"):
            fn.stack_map[lval.variable] = base
            program.stack_map[lval.variable] = base
            for length_var in lval.variable_list:
                fn.stack_map[length_var] = base
                program.stack_map[length_var] = base
                base -= 8
        else:
            fn.stack_map[lval.variable] = base
            for length_var in lval.variable_list:
                fn.stack_map[length_var] = base
                base -= 8

def gen_jump_fn(program, fn, jumplabel):
    if fn not in program.fns:
        program.fns.append(fn)
    parent = fn
    while parent.jump_parent != None:
        parent = parent.jump_parent
    fn = Function(jumplabel, [], {}, parent, [])
    parent.jump_children.append(fn)
    return fn

def get_expr_size(expr_type, env): #Changed to take in expression instead of expression's resolved type
    if type(expr_type) is ArrayResolvedType:
        return 8 + (8*expr_type.rank)
    elif type(expr_type) is StructResolvedType:
        name_info = env.get_struct(expr_type.name)
        size = 0
        for field in name_info:
            size += get_expr_size(field[1], env)
        return size
    else:
        return 8

def get_total_arr_size(expr_type):
    if type(expr_type) is ArrayResolvedType:
        return 8 + (8 * expr_type.rank)
    
def alloc(size, program, fn):
    program.stack.size += size
    fn.code.append(f"sub rsp, {size}")

def copy_data(size, start, end, fn, name):
    fn.code.append(f"; Moving {size} bytes from rbp - {start} to rsp")
    for i in range(size-8, -1, -8):
        fn.code.append(f"\tmov r10, [rbp - {start} + {i}] ; Variable {name}")
        fn.code.append(f"\tmov [rsp + {end + i}], r10")

def copy_global_data(size, start, end, fn):
    fn.code.append(f"; Moving {size} bytes from r12 - {start} to rsp")
    for i in range(size-8, -1, -8): 
        fn.code.append(f"\tmov r10, [r12 - {start} + {i}]")
        fn.code.append(f"\tmov [rsp + {end + i}], r10")

def copy_data_to_ret_address(size, fn):
    fn.code.append(f"; Moving {size} bytes from rsp to rax")
    for i in range(size, -1, -8):
        fn.code.append(f"\tmov r10, [rsp + {i}]")
        fn.code.append(f"\tmov [rax + {i}], r10")

def copy_data_rax(size, fn):
    fn.code.append(f"; Moving {size} bytes from rax to rsp")
    for i in range(size-8, -1, -8): 
        fn.code.append(f"\tmov r10, [rax + {i}]")
        fn.code.append(f"\tmov [rsp + {i}], r10")

def copy_data_array_loop(size, fn):
    fn.code.append(f"; Moving {size+8} bytes from rsp to rax")
    for i in range(size, -1, -8):
        fn.code.append(f"\tmov r10, [rsp + {i}]")
        fn.code.append(f"\tmov [rax + {i}], r10")

def copy_data_struct(size, start, end, fn, name):
    fn.code.append(f"; Moving {size} bytes from rsp + {start} to rsp + {end}")
    for i in range(size-8, -1, -8):
        fn.code.append(f"\tmov r10, [rsp + {start} + {i}] ; Variable {name}")
        fn.code.append(f"\tmov [rsp + {end} + {i}], r10")

def power_of_2(x:int):
    if x == 1:
        return 0
    if not(x > 0 and (x & (x - 1)) == 0):
        return -1
    else:
        n = 0
        while (1 << n) < x:
            n += 1
        return n
    
def replace_imul(expr, fn, program, env):
    if type(expr) is IntExpr:
        if power_of_2(expr.i) != -1:
            fn = gen_expr(expr, program, fn, env)
            program.stack.pop(fn, "rax")
            fn.code.append(f"shl rax, {power_of_2(expr.i)}")
            program.stack.push(fn, "rax")
            return fn
    return False

def has_message(message: str, fn: Function, program: Assembly):
    key = f'`{message}`, 0'.replace("\"", "")
    if (key, "") in program.constants:
        m_const = program.constants[(key, "")][0]
    else:
        m_const = program.gensym_const()
        program.add_const(m_const, 'db', key, "")
    return m_const

def assert_asm(message: str, condition: str, jump_l: str, fn: Function, program: Assembly, env):
    align = False
    #jump_l = program.gen_jump()
    jump_fn = gen_jump_fn(program, fn, jump_l)
    fn.code.append(f"{condition} {jump_l}")
    size = get_stack_base(fn, program, env)
    if size % 16 != 0:
        program.stack.align(fn, 8)
        align = True
    m = has_message(message, fn, program)
    fn.code.append(f"lea rdi, [rel {m}]")
    fn.code.append(f"call _fail_assertion")
    if align:
        program.stack.unalign(fn)
    return jump_fn

def get_stack_base(fn, program, env):
    parent = fn
    if fn.name.startswith(".jump"):
        parent = fn.jump_parent
    if parent.name == "_jpl_main":
        base = program.stack.size
    else:
        base = program.stack.size - env.get_function(parent.name[1:]).cc.stack_base
    return base

def gen_expr(node, program: Assembly, fn: Function, env):
    match (type(node).__name__):
        case "IntExpr":
            load_constant = False
            if program.opt_level == 0:
                load_constant = True
            elif program.opt_level == 1:
                if node.i & ((1 << 31) - 1) == node.i:
                    program.stack.push(fn, f"qword {node.i}")
                else:
                    load_constant = True
            if load_constant:
                if (node.i, "int") in program.constants:
                    name = program.constants[(node.i, "int")][0]
                else:
                    name = program.gensym_const()
                    program.add_const(name, "dq", node.i, "int")
                fn.code.append(f"mov rax, [rel {name}] ; {node.i}")
                program.stack.push(fn, "rax")
            return fn
        case "FloatExpr":
            if (node.f, "float") in program.constants:
                name = program.constants[(node.f, "float")][0]
            else:
                name = program.gensym_const()
                program.add_const(name, "dq", node.f, "float")
            fn.code.append(f"mov rax, [rel {name}] ; {node.f}")
            program.stack.push(fn, "rax")
            return fn
        case "TrueExpr":
            if program.opt_level == 0:
                if (1, "int") in program.constants:
                    name = program.constants[(1, "int")][0]
                else:
                    name = program.gensym_const()
                    program.add_const(name, "dq", 1, "int")
                fn.code.append(f"mov rax, [rel {name}] ; 1")
                program.stack.push(fn, "rax") 
            elif program.opt_level == 1:
                program.stack.push(fn, "qword 1")
            return fn
        case "FalseExpr":
            if program.opt_level == 0:
                if (0, "int") in program.constants:
                    name = program.constants[(0, "int")][0]
                else:
                    name = program.gensym_const()
                    program.add_const(name, "dq", 0, "int")
                fn.code.append(f"mov rax, [rel {name}] ; 0")
                program.stack.push(fn, "rax") 
            elif program.opt_level == 1:
                program.stack.push(fn, "qword 0")
            return fn
        case "VariableExpr":
            found = False
            isLocal = False
            name = node.variable
            fn_ptr = fn
            if name in fn.stack_map:
                pos = fn.stack_map[name]
                found = True
                isLocal = True
            elif fn.name.startswith(".jump"):
                if name in fn.jump_parent.stack_map:
                    pos = fn.jump_parent.stack_map[name]
                    fn_ptr = fn.jump_parent
                    found = True
                    isLocal = True
                for child in fn.jump_parent.jump_children:
                    if name in child.stack_map:
                        pos = child.stack_map[name]
                        fn_ptr = child
                        found = True
                        isLocal = True
            if not found and name in program.stack_map:
                pos = program.stack_map[name]
                found = True
            if not found:
                print(fn.name)
                print(fn.jump_parent.name)
                raise Exception(f"variable {name} not defined in code")
            alloc(get_expr_size(node.type, env), program, fn)
            size = get_expr_size(node.type, env)
            is_main = False
            if fn_ptr.name == "_jpl_main":
                is_main = True
            if fn_ptr.name.startswith(".jump"):
                if fn_ptr.jump_parent.name == "_jpl_main":
                    is_main = True
            if (not is_main) and (not isLocal) and (not name in fn_ptr.stack_map):
                copy_global_data(size, pos, 0, fn)
            else:
                copy_data(size, pos, 0, fn, name)
            return fn
        case "ArrayExpr":
            for expr in node.expr_list[::-1]:
                fn = gen_expr(expr, program, fn, env)
            mem_size = len(node.expr_list) * get_expr_size(node.expr_list[0].type, env)
            fn.code.append(f"mov rdi, {mem_size}")
            aligned = False
            size = get_stack_base(fn, program, env)
            if size % 16 != 0:
                aligned = True
                program.stack.align(fn, 8)
            fn.code.append("call _jpl_alloc")
            if aligned: 
                program.stack.unalign(fn)
            for i in range(mem_size-8, -1, -8):
                fn.code.append(f"\tmov r10, [rsp + {i}]")
                fn.code.append(f"\tmov [rax + {i}], r10")
            program.stack.free(fn, mem_size) 
            program.stack.push(fn, "rax")
            fn.code.append(f"mov rax, {len(node.expr_list)}")
            program.stack.push(fn, "rax")
            return fn
        case "VoidExpr":
            if (1, "int") in program.constants:
                name = program.constants[(1, "int")][0]
            else:
                name = program.gensym_const()
                program.add_const(name, "dq", 1, "int")
            fn.code.append(f"mov rax, [rel {name}] ; {1}")
            program.stack.push(fn, "rax")
            return fn
        case "StructLiteralExpr":
            for i in range(len(node.expr_list)-1,-1,-1):
                fn = gen_expr(node.expr_list[i], program, fn, env)
            return fn
        case "DotExpr":
            fn = gen_expr(node.expr, program, fn, env)
            struct = env.get_struct(node.expr.type.name)
            offset = 0
            size = 0
            for field in struct:
                if field[0] == node.variable:
                    size = get_expr_size(field[1], env)
                    break
                offset += get_expr_size(field[1], env)
            end = get_expr_size(node.expr.type, env) - size
            copy_data_struct(size, offset, end, fn, f".{node.variable}")
            fn.code.append(f"add rsp, {end}")
            program.stack.size -= end
            return fn
        case "CallExpr":
            cc = env.get_function(node.variable).cc
            # Prepare stack
            ret_size = 0
            aligned = False
            if isinstance(cc.ret_val, int):
                ret_type = env.get_function(node.variable).fn_type
                if type(ret_type) is ArrayResolvedType:
                    ret_size = get_total_arr_size(env.get_function(node.variable).fn_type)
                else:
                    ret_size = get_expr_size(ret_type, env)
                alloc(ret_size, program, fn)
            size = program.stack.size
            parent = fn.name
            if parent.startswith(".jump"):
                parent = fn.jump_parent.name
            if parent != "_jpl_main":
                size = program.stack.size - env.get_function(parent[1:]).cc.stack_base
            if isinstance(cc.ret_val, int): # We added this because we ran into alignment issues with functions with array return types
                size -= 8
            if (size + cc.stack_size) % 16 != 0:
                aligned = True
                program.stack.align(fn, 8)
            # Generate expression code
            for i in range(len(node.expr_list)-1,-1,-1):
                if cc.regs[i][0] == 1:
                    fn = gen_expr(node.expr_list[i], program, fn, env)

            for i in range(len(node.expr_list)-1,-1,-1):
                if cc.regs[i][0] == 0:
                    fn = gen_expr(node.expr_list[i], program, fn, env)
            for reg in cc.regs:
                if reg[0] == 0:
                    if reg[1].startswith("xmm"):
                        fn.code.append(f"movsd {reg[1]}, [rsp]")
                        fn.code.append("add rsp, 8")
                        program.stack.size -= 8
                    else:
                        program.stack.pop(fn, reg[1])
            # Make call
            if isinstance(cc.ret_val, int):
                called = fn
                for f in program.fns:
                    if f.name[1:] == node.variable:
                        called = f
                pad = 0
                minus = False
                if aligned:
                    offset = cc.stack_size + program.stack.padding[-1] - called.stack_map["$return"]
                else:
                    offset = cc.stack_size - called.stack_map["$return"]
                fn.code.append(f"lea rdi, [rsp + {offset}]") 
            fn.code.append(f"call _{node.variable}")
            # Free variables
            for reg in cc.regs:
                if reg[0] == 1:
                    program.stack.free(fn, reg[1][1])
            # Unalign
            if aligned:
                program.stack.unalign(fn)
            # Push to stack if not already there
            if not isinstance(cc.ret_val, int):
                if cc.ret_val.startswith("xmm"):
                    fn.code.append("sub rsp, 8")
                    fn.code.append(f"movsd [rsp], {cc.ret_val}")
                    program.stack.size += 8
                else:
                    program.stack.push(fn, cc.ret_val)
            return fn
        case "UnopExpr":
            fn = gen_expr(node.expr, program, fn, env)
            if type(node.type).__name__ == "FloatResolvedType":
                fn.code.append("movsd xmm1, [rsp]")
                fn.code.append("add rsp, 8") 
                program.stack.size -= 8
                fn.code.append("pxor xmm0, xmm0")
                fn.code.append("subsd xmm0, xmm1")
                fn.code.append("sub rsp, 8")
                program.stack.size += 8 
                fn.code.append("movsd [rsp], xmm0")
            else:
                program.stack.pop(fn, "rax")
                if node.op.text == "-":
                    fn.code.append("neg rax")
                else:
                    fn.code.append("xor rax, 1")
                program.stack.push(fn, "rax")
            return fn
        case "BinopExpr":
            if node.op.text == "&&" or node.op.text == "||":
                fn = gen_expr(node.l_expr, program, fn, env)
                program.stack.pop(fn, "rax")
                fn.code.append("cmp rax, 0")
                label = program.gen_jump()
                if node.op.text == "&&":
                    fn.code.append(f"je {label}")
                else:
                    fn.code.append(f"jne {label}")
                fn = gen_expr(node.r_expr, program, fn, env)
                program.stack.pop(fn, "rax")
                fn = gen_jump_fn(program, fn, label)
                program.stack.push(fn, "rax")
            else:
                aligned = False
                size = get_stack_base(fn, program, env)
                if type(node.l_expr.type).__name__ == "FloatResolvedType" and node.op.text == "%":
                    padding = (size) % 16
                    if padding != 0:
                        aligned = True
                        program.stack.align(fn, 8)
                if node.op.text == "*" and program.opt_level == 1:
                    if type(node.l_expr) is IntExpr:
                        log2 = power_of_2(node.l_expr.i)
                        if log2 == 0:
                            fn = gen_expr(node.r_expr, program, fn, env)
                            return fn
                        if log2 > 0:
                            fn = gen_expr(node.r_expr, program, fn, env)
                            program.stack.pop(fn, "rax")
                            fn.code.append(f"shl rax, {log2}")
                            program.stack.push(fn, "rax")
                            return fn
                    if type(node.r_expr) is IntExpr:
                        log2 = power_of_2(node.r_expr.i)
                        if log2 == 0:
                            fn = gen_expr(node.l_expr, program, fn, env)
                            return fn
                        if log2 > 0:
                            fn = gen_expr(node.l_expr, program, fn, env)
                            program.stack.pop(fn, "rax")
                            fn.code.append(f"shl rax, {log2}")
                            program.stack.push(fn, "rax")
                            return fn
                fn = gen_expr(node.r_expr, program, fn, env)
                fn = gen_expr(node.l_expr, program, fn, env)
                if type(node.l_expr.type).__name__ == "FloatResolvedType":
                    fn.code.append("movsd xmm0, [rsp]")
                    fn.code.append("add rsp, 8")
                    program.stack.size -= 8 
                    fn.code.append("movsd xmm1, [rsp]")
                    fn.code.append("add rsp, 8") 
                    program.stack.size -= 8
                    match node.op.text:
                        case "+":
                            fn.code.append("addsd xmm0, xmm1")
                        case "-":
                            fn.code.append("subsd xmm0, xmm1")
                        case "*":
                            fn.code.append("mulsd xmm0, xmm1")
                        case "/":
                            fn.code.append("divsd xmm0, xmm1")
                        case "%":
                            fn.code.append("call _fmod")
                            if aligned:
                                program.stack.unalign(fn)
                        case "==":
                            fn.code.append("cmpeqsd xmm0, xmm1")
                            fn.code.append("movq rax, xmm0")
                            fn.code.append("and rax, 1")
                            program.stack.push(fn, "rax")
                            return fn
                        case "!=":
                            fn.code.append("cmpneqsd xmm0, xmm1")
                            fn.code.append("movq rax, xmm0")
                            fn.code.append("and rax, 1")
                            program.stack.push(fn, "rax")
                            return fn
                        case "<":
                            fn.code.append("cmpltsd xmm0, xmm1")
                            fn.code.append("movq rax, xmm0")
                            fn.code.append("and rax, 1")
                            program.stack.push(fn, "rax")
                            return fn
                        case ">":
                            fn.code.append("cmpltsd xmm1, xmm0")
                            fn.code.append("movq rax, xmm1")
                            fn.code.append("and rax, 1")
                            program.stack.push(fn, "rax")
                            return fn
                        case "<=":
                            fn.code.append("cmplesd xmm0, xmm1")
                            fn.code.append("movq rax, xmm0")
                            fn.code.append("and rax, 1")
                            program.stack.push(fn, "rax")
                            return fn
                        case ">=":
                            fn.code.append("cmplesd xmm1, xmm0")
                            fn.code.append("movq rax, xmm1")
                            fn.code.append("and rax, 1")
                            program.stack.push(fn, "rax")
                            return fn
                    fn.code.append("sub rsp, 8")
                    program.stack.size += 8 
                    fn.code.append("movsd [rsp], xmm0")
                else:
                    program.stack.pop(fn, "rax")
                    program.stack.pop(fn, "r10")
                    match node.op.text:
                        case "+":
                            fn.code.append("add rax, r10")
                        case "-":
                            fn.code.append("sub rax, r10")
                        case "*":
                            fn.code.append("imul rax, r10")
                        case "/" | "%":
                            fn.code.append("cmp r10, 0")
                            jumplabel = program.gen_jump()
                            if node.op.text == "/":
                                if ('`divide by zero`, 0', "") in program.constants:
                                    const = program.constants[('`divide by zero`, 0', "")][0]
                                else:
                                    const = program.gensym_const()
                                    program.add_const(const, 'db', '`divide by zero`, 0', "")
                            else:
                                if ('`mod by zero`, 0', "") in program.constants:
                                    const = program.constants[('`mod by zero`, 0', "")][0]
                                else:
                                    const = program.gensym_const()
                                    program.add_const(const, 'db', '`mod by zero`, 0', "")
                            fn.code.append(f"jne {jumplabel}")
                            aligned = False 
                            size = program.stack.size
                            parent = fn.name
                            if parent.startswith(".jump"):
                                parent = fn.jump_parent.name
                            if parent != "_jpl_main":
                                size = program.stack.size - env.get_function(parent[1:]).cc.stack_base
                            if size % 16 != 0:
                                aligned = True
                                program.stack.align(fn, 8)
                            fn.code.append(f"lea rdi, [rel {const}]")
                            fn.code.append("call _fail_assertion")
                            if aligned:
                                program.stack.unalign(fn)
                            if fn not in program.fns:
                                program.fns.append(fn)
                            parent = fn
                            while parent.jump_parent != None:
                                parent = parent.jump_parent
                            fn = Function(jumplabel, [], {}, parent, [])
                            parent.jump_children.append(fn)
                            fn.code.append("cqo")
                            fn.code.append("idiv r10")
                            if node.op.text == "%":
                                fn.code.append("mov rax, rdx")
                        case "==":
                            fn.code.append("cmp rax, r10")
                            fn.code.append("sete al")
                            fn.code.append("and rax, 1")
                        case "!=":
                            fn.code.append("cmp rax, r10")
                            fn.code.append("setne al")
                            fn.code.append("and rax, 1")
                        case "<":
                            fn.code.append("cmp rax, r10")
                            fn.code.append("setl al")
                            fn.code.append("and rax, 1")
                        case ">":
                            fn.code.append("cmp rax, r10")
                            fn.code.append("setg al")
                            fn.code.append("and rax, 1")
                        case "<=":
                            fn.code.append("cmp rax, r10")
                            fn.code.append("setle al")
                            fn.code.append("and rax, 1")
                        case ">=":
                            fn.code.append("cmp rax, r10")
                            fn.code.append("setge al")
                            fn.code.append("and rax, 1")
                    program.stack.push(fn, "rax")
            return fn
        case "IfExpr":
            #node
            l1_can_opt = (type(node.then_expr) is IntExpr) and (type(node.else_expr) is IntExpr) and (
                node.then_expr.i == 1 and node.else_expr.i == 0)
            if program.opt_level == 0 or not l1_can_opt:
                fn = gen_expr(node.cndn_expr, program, fn, env) #generate code for e1
                program.stack.pop(fn, "rax")
                fn.code.append("cmp rax, 0")
                else_branch = program.gen_jump()
                end_branch = program.gen_jump()
                fn.code.append(f"je {else_branch}") #don't make new function because havent jumped yet?
                fn = gen_expr(node.then_expr, program, fn, env)
                #decrement stack by size of return type to prevent the 2n error. just use expr size?
                size = get_expr_size(node.type, env)
                program.stack.size -= size
                fn.code.append(f"jmp {end_branch}")
                #begin code to handle new jump function (else branch)
                fn = gen_jump_fn(program, fn, else_branch)
                fn = gen_expr(node.else_expr, program, fn, env)
                #begin code to handle new jump function (end branch)
                fn = gen_jump_fn(program, fn, end_branch)
            elif program.opt_level == 1 and l1_can_opt:
                fn = gen_expr(node.cndn_expr, program, fn, env)
            return fn
        case "ArrayIndexExpr":
            gap = node.expr.type.rank
            if type(node.expr.type.type) is StructResolvedType and node.expr.type.type.name == "rgba":
                gap -= 2 #this value needs to be changed somehow?
            found = False
            copy = True
            if type(node.expr) is VariableExpr and program.opt_level == 1:
                name = node.expr.variable
                if name in fn.stack_map:
                    pos = fn.stack_map[name]
                    found = True
                elif fn.name.startswith(".jump"):
                    if name in fn.jump_parent.stack_map:
                        pos = fn.jump_parent.stack_map[name]
                        found = True
                    for child in fn.jump_parent.jump_children:
                        if name in child.stack_map:
                            pos = child.stack_map[name]
                            found = True
                if not found and name in program.stack_map:
                    pos = program.stack_map[name]
                    found = True
                if not found:
                    print(fn.name)
                    print(fn.jump_parent.name)
                    raise Exception(f"variable {name} not defined in code")
                offset = program.stack.size - pos
                gap *= 8
                gap += (program.stack.size - pos)
                gap = (int)(gap / 8)
                copy = False
            else:
                fn = gen_expr(node.expr, program, fn, env)
            for i in range(len(node.expr_list)-1,-1,-1): #gen in reverse order
                fn = gen_expr(node.expr_list[i], program, fn, env)
            for i in range(len(node.expr_list)):
                #pretty sure we make new jumps for each index expr
                sec_check = program.gen_jump()
                safe = program.gen_jump()
                if i == 0:
                    fn.code.append(f"mov rax, [rsp]")
                else:
                    fn.code.append(f"mov rax, [rsp + {(i)*8}]") 
                fn.code.append("cmp rax, 0")
                fn = assert_asm("negative array index", "jge", sec_check, fn, program, env)
                fn.code.append(f"cmp rax, [rsp + {((i + gap) * 8)}] ;error is here?")
                fn = assert_asm("index too large", "jl", safe, fn, program, env)
            #after we exit, we will be in the latest function and generate the indexing code (3rd slide for indexing)
            #gen indexing code:
            if program.opt_level == 0:
                offset = 0 #says nonzero later for slides? idk
                fn.code.append("mov rax, 0")
                for i in range(len(node.expr_list)): #not in reverse here
                    """imul rax, [rsp + (OFFSET + IDX * 8 + GAP * 8)]
                        add rax, [rsp + (OFFSET + IDX * 8)]"""
                    fn.code.append(f"imul rax, [rsp + {offset + i * 8 + (gap * 8)}] ; no overflow if indices in bounds")
                    fn.code.append(f"add rax, [rsp + {offset + i * 8}]")
                elem_size = get_expr_size(node.type, env)
                fn.code.append(f"imul rax, {elem_size}")
                fn.code.append(f"add rax, [rsp + {(offset + len(node.expr_list) * 8 + gap * 8)}]")
            elif program.opt_level == 1:
                offset = 0
                fn.code.append(f"mov rax, [rsp + {offset}]")
                for i in range(1, len(node.expr_list)):
                    fn.code.append(f"imul rax, [rsp + {offset + i * 8 + (gap * 8)}] ; no overflow if indices in bounds")
                    fn.code.append(f"add rax, [rsp + {offset + i * 8}]")
                elem_size = get_expr_size(node.type, env)
                if power_of_2(elem_size) != -1:
                    fn.code.append(f"shl rax, {power_of_2(elem_size)}")
                else:
                    fn.code.append(f"imul rax, {elem_size}")
                fn.code.append(f"add rax, [rsp + {(offset + len(node.expr_list) * 8 + gap * 8)}]")
            #now we write the code to free all the allocated space (back to 1st indexing slide)
            if program.opt_level == 0:
                for i in range(len(node.expr_list)): #have no idea if this is reversed or not but shouldnt matter
                    size = get_expr_size(node.expr_list[i], env)
                    program.stack.free(fn, size)
            else:
                program.stack.free(fn, len(node.expr_list) * get_expr_size(node.expr_list[0], env))
            if copy:
                program.stack.free(fn, get_expr_size(node.expr.type, env))
            #alloc size for elements
            fn.code.append(f"sub rsp, {elem_size}")
            program.stack.size += elem_size
            copy_data_rax(elem_size, fn)
            return fn
        case "SumLoopExpr":
            NUM_E = len(node.list)
            fn.code.append("; allocating 8 bytes for the sum")
            alloc(8, program, fn)
            #generate code for each expression, checking bounds
            for i in range(len(node.list)-1, -1, -1):
                fn.code.append(f"; Computing bound for \'{node.list[i][0]}\'")
                fn = gen_expr(node.list[i][1], program, fn, env)
                fn.code.append("mov rax, [rsp]")
                fn.code.append("cmp rax, 0")
                fn = assert_asm("non-positive loop bound", "jg", program.gen_jump(), fn, program, env)
            fn.code.append("mov rax, 0 ;init sum")
            fn.code.append(f"mov [rsp + {NUM_E*8}], rax ; move to pre-alloc")
            #Create lvalues for bound variables
            for i in range(len(node.list)-1, -1, -1):
                fn.code.append("mov rax, 0")
                lval = VariableLvalue(0, node.list[i][0])
                program.stack.push(fn, "rax")
                base = get_stack_base(fn, program, env)
                add_lvalue(lval, fn, program, base)
            label = program.gen_jump()
            label_fn = gen_jump_fn(program, fn, label)
            fn = label_fn
            fn.code.append(f"; Compute loop body (SumLoop) {node.expr.toString()}")
            #generate the loop body
            fn = gen_expr(node.expr, program, fn, env)
            if type(node.expr.type) is IntResolvedType:
                program.stack.pop(fn, "rax")
                fn.code.append(f"add [rsp + {2 * NUM_E * 8}], rax")
            elif type(node.expr.type) is FloatResolvedType:
                #this is pop for float regs
                fn.code.append("movsd xmm0, [rsp]")
                fn.code.append("add rsp, 8") 
                program.stack.size -= 8
                fn.code.append(f"addsd xmm0, [rsp + {(2 * NUM_E * 8)}]")
                fn.code.append(f"movsd [rsp + {(2 * NUM_E * 8)}], xmm0")
            fn.code.append(f"add qword [rsp + {((NUM_E-1) * 8)}], 1") #increment last variable
            for i in range(NUM_E-1, -1, -1):
                #check that each variable is within its bounds
                fn.code.append(f"mov rax, [rsp + {(i * 8)}]")
                fn.code.append(f"cmp rax, [rsp + {((i + NUM_E) * 8)}]")
                fn.code.append(f"jl {label}")
                #if not first, then we increment the previous var
                if i > 0:
                    fn.code.append(f"mov qword [rsp + {(i * 8)}], 0")
                    fn.code.append(f"add qword [rsp + {((i-1) * 8)}], 1")
            #since we allocated bounds and variables, we have to free twice (only once for arrays)
            fn.code.append("; free all loop variables")
            program.stack.free(fn, (NUM_E * 8))
            fn.code.append("; free all loop bounds")
            program.stack.free(fn, (NUM_E * 8))
            return fn
        case "ArrayLoopExpr":
            align = False
            NUM_E = len(node.list)
            fn.code.append("; allocating 8 bytes for pointer")
            alloc(8, program, fn)
            try:
                tc_gen = node.is_tc
            except AttributeError:
                tc_gen = False
            if program.opt_level == 1:
                if tc_gen:
                    # Compute array bounds
                    for i in range(len(node.list)-1, -1, -1):
                        fn.code.append(f"; Computing bound for \'{node.list[i][0]}\'")
                        fn = gen_expr(node.list[i][1], program, fn, env)
                        fn.code.append("mov rax, [rsp]")
                        fn.code.append("cmp rax, 0")
                        fn = assert_asm("non-positive loop bound", "jg", program.gen_jump(), fn, program, env)
                    # Compute sum bounds
                    for i in range(len(node.expr.list)-1, -1, -1):
                        fn.code.append(f"; Computing bound for \'{node.expr.list[i][0]}\'")
                        fn = gen_expr(node.expr.list[i][1], program, fn, env)
                        fn.code.append("mov rax, [rsp]")
                        fn.code.append("cmp rax, 0")
                        fn = assert_asm("non-positive loop bound", "jg", program.gen_jump(), fn, program, env)
                    # Multiply array bounds (not sum bounds) together
                    body_size = get_expr_size(node.expr.expr.type, env)
                    fn.code.append(f"mov rdi, {body_size} ;init pointer")
                    sum_offset = len(node.expr.list) * body_size
                    for i in range(len(node.list)):
                        fn.code.append(f"imul rdi, [rsp + {sum_offset} + {i*8}]")
                        fn = assert_asm("overflow computing array size", "jno", program.gen_jump(), fn, program, env)
                    # jpl alloc
                    size = get_stack_base(fn, program, env)
                    if size % 16 != 0:
                        program.stack.align(fn, 8)
                        align = True
                    fn.code.append("call _jpl_alloc")
                    if align:
                        program.stack.unalign(fn)
                    # Save the allocated pointer to the stack
                    fn.code.append(f"mov [rsp + {NUM_E * 8 + sum_offset}], rax ; move to pre-allocated space")
                    # Initialize all bounds to 0
                    for i in range(NUM_E-1, -1, -1):
                        fn.code.append("mov rax, 0 ; Initialize var to 0")
                        program.stack.push(fn, "rax")
                        lval = VariableLvalue(0, node.list[i][0])
                        base = get_stack_base(fn, program, env)
                        add_lvalue(lval, fn, program, base)
                    for i in range(len(node.expr.list)-1, -1, -1):
                        fn.code.append("mov rax, 0 ; Initialize var to 0")
                        program.stack.push(fn, "rax")
                        lval = VariableLvalue(0, node.expr.list[i][0])
                        base = get_stack_base(fn, program, env)
                        add_lvalue(lval, fn, program, base)
                    # Begin loop
                    label = program.gen_jump()
                    fn = gen_jump_fn(program, fn, label)
                    for i in range(1):
                        # Compute sum loop body
                        fn = gen_expr(node.expr.expr, program, fn, env)
                        # Indexing code
                        gap = len(node.list)
                        offset = get_expr_size(node.expr.type, env)
                        fn.code.append(f"mov rax, [rsp + {offset} + {sum_offset}]")
                        for i in range(1, len(node.list)):
                            if type(node.list[i][1]) is IntExpr:
                                log2 = power_of_2(node.list[i][1].i)
                                if log2 != -1:
                                    fn.code.append(f"shl rax, {log2}")
                                else:
                                    fn.code.append(f"imul rax, {node.list[i][1].i} ; no overflow if indices in bounds")
                            else:
                                fn.code.append(f"imul rax, [rsp + {offset + i * 8 + (gap * 8) + 2 * sum_offset}] ; no overflow if indices in bounds")
                            fn.code.append(f"add rax, [rsp + {offset + i * 8 + sum_offset}]")
                        elem_size = get_expr_size(node.expr.type, env)
                        if power_of_2(elem_size) -1:
                            fn.code.append(f"shl rax, {power_of_2(elem_size)}")
                        else:
                            fn.code.append(f"imul rax, {elem_size}")
                        fn.code.append(f"add rax, [rsp + {(offset + (len(node.list) + len(node.expr.list)) * 8 + gap * 8 + sum_offset)}]") 
                        # Add the body to the computed pointer
                        if type(node.expr.type) is IntResolvedType:
                            program.stack.pop(fn, "r10")
                            fn.code.append(f"add [rax], r10")
                            fn.code.append(f"add qword [rsp], 1") #increment last variable
                        elif type(node.expr.type) is FloatResolvedType:
                            #this is pop for float regs
                            fn.code.append("movsd xmm0, [rsp]")
                            fn.code.append("add rsp, 8") 
                            program.stack.size -= 8
                            fn.code.append(f"addsd xmm0, [rax]")
                            fn.code.append(f"movsd [rax], xmm0")
                            fn.code.append(f"add qword [rsp + {((NUM_E + len(node.expr.list)-1) * 8)}], 1") #increment last variable
                        # Increment the loop indices using the topological order
                        top_order = node.top_list
                        for i in range(len(top_order)-1,-1,-1):
                            #check that each variable is within its bounds
                            index_offset = -1
                            for j in range(len(node.list)-1,-1,-1):
                                if node.list[j][0] == top_order[i]:
                                    index_offset = j * 8 + len(node.expr.list) * 8
                                    bound_offset = j * 8 + len(node.expr.list) * 8 + (len(node.expr.list) + NUM_E) * 8
                            if index_offset == -1:
                                for j in range(len(node.expr.list)-1,-1,-1):
                                    if node.expr.list[j][0] == top_order[i]:
                                        index_offset = j * 8
                                        bound_offset = j * 8 + (len(node.expr.list) + NUM_E) * 8
                            fn.code.append(f"mov rax, [rsp + {index_offset}]")
                            fn.code.append(f"cmp rax, [rsp + {bound_offset}]")
                            fn.code.append(f"jl {label}")
                            #if not first, then we increment the previous var
                            if i > 0:
                                next_offset = -1
                                for j in range(len(node.list)-1,-1,-1):
                                    if node.list[j][0] == top_order[i-1]:
                                        next_offset = j * 8 + len(node.expr.list) * 8
                                if next_offset == -1:
                                    for j in range(len(node.expr.list)-1,-1,-1):
                                        if node.expr.list[j][0] == top_order[i-1]:
                                            next_offset = j * 8
                                fn.code.append(f"mov qword [rsp + {index_offset}], 0")
                                fn.code.append(f"add qword [rsp + {next_offset}], 1")
                    program.stack.free(fn, 8 * (NUM_E + len(node.expr.list)))
                    program.stack.free(fn, 8 * len(node.expr.list))
            if not tc_gen:
                #generate code for each expression, checking bounds
                for i in range(len(node.list)-1, -1, -1):
                    fn.code.append(f"; Computing bound for \'{node.list[i][0]}\'")
                    fn = gen_expr(node.list[i][1], program, fn, env)
                    fn.code.append("mov rax, [rsp]")
                    fn.code.append("cmp rax, 0")
                    fn = assert_asm("non-positive loop bound", "jg", program.gen_jump(), fn, program, env)
                fn.code.append(f"mov rdi, {get_expr_size(node.expr.type, env)} ;init pointer")
                #Create lvalues for bound variables
                for i in range(len(node.list)):
                    fn.code.append(f"imul rdi, [rsp + {i*8}]")
                    fn = assert_asm("overflow computing array size", "jno", program.gen_jump(), fn, program, env)
                size = get_stack_base(fn, program, env)
                if size % 16 != 0:
                    program.stack.align(fn, 8)
                    align = True
                fn.code.append("call _jpl_alloc")
                if align:
                    program.stack.unalign(fn)
                fn.code.append(f"mov [rsp + {NUM_E * 8}], rax ; move to pre-allocated space")
                for i in range(NUM_E-1, -1, -1):
                    fn.code.append("mov rax, 0 ; Initialize ver to 0")
                    program.stack.push(fn, "rax")
                    lval = VariableLvalue(0, node.list[i][0])
                    base = get_stack_base(fn, program, env)
                    add_lvalue(lval, fn, program, base)
                label = program.gen_jump()
                label_fn = gen_jump_fn(program, fn, label)
                fn = label_fn
                fn.code.append(f"; Compute loop body (Array loop) {node.expr.toString()}")
                #generate the loop body
                fn = gen_expr(node.expr, program, fn, env)
                gap = len(node.list)
                # INDEXING CODE:
                if program.opt_level == 0:
                    offset = get_expr_size(node.expr.type, env)
                    fn.code.append("mov rax, 0")
                    for i in range(len(node.list)): #not in reverse here
                        fn.code.append(f"imul rax, [rsp + {offset + i * 8 + (gap * 8)}] ; no overflow if indices in bounds")
                        fn.code.append(f"add rax, [rsp + {offset + i * 8}]")
                    elem_size = get_expr_size(node.expr.type, env)
                    fn.code.append(f"imul rax, {elem_size}")
                elif program.opt_level == 1:
                    offset = get_expr_size(node.expr.type, env)
                    fn.code.append(f"mov rax, [rsp + {offset}]") 
                    for i in range(1, len(node.list)):
                        if type(node.list[i][1]) is IntExpr:
                            log2 = power_of_2(node.list[i][1].i)
                            if log2 != -1:
                                fn.code.append(f"shl rax, {log2}")
                            else:
                                fn.code.append(f"imul rax, {node.list[i][1].i} ; no overflow if indices in bounds")
                        else:
                            fn.code.append(f"imul rax, [rsp + {offset + i * 8 + (gap * 8)}] ; no overflow if indices in bounds")
                        fn.code.append(f"add rax, [rsp + {offset + i * 8}]")
                    elem_size = get_expr_size(node.expr.type, env)
                    if power_of_2(elem_size) -1:
                        fn.code.append(f"shl rax, {power_of_2(elem_size)}")
                    else:
                        fn.code.append(f"imul rax, {elem_size}")
                fn.code.append(f"add rax, [rsp + {(offset + len(node.list) * 8 + gap * 8)}]")
                copy_data_array_loop(offset-8, fn)
                program.stack.free(fn, offset)
                fn.code.append(f"add qword [rsp + {((NUM_E-1) * 8)}], 1") #increment last variable
                for i in range(NUM_E-1, -1, -1):
                    #check that each variable is within its bounds
                    fn.code.append(f"mov rax, [rsp + {(i * 8)}]")
                    fn.code.append(f"cmp rax, [rsp + {((i + NUM_E) * 8)}]")
                    fn.code.append(f"jl {label}")
                    #if not first, then we increment the previous var
                    if i > 0:
                        fn.code.append(f"mov qword [rsp + {(i * 8)}], 0")
                        fn.code.append(f"add qword [rsp + {((i-1) * 8)}], 1")
                #since we allocated bounds and variables, we have to free twice (only once for arrays)
                fn.code.append("; free all loop variables")
                program.stack.free(fn, (NUM_E*8))
            return fn
        case _:
            raise Exception(f"ASTNode of type {type(node).__name__}; invalid for HW10")
    raise Exception(f"not implemented, {type(node).__name__} type not recognized")

def gen_cmd(node, program, fn, env, cc):
    match (type(node).__name__):
        case "ShowCmd":
            aligned = False
            if (program.stack.size + get_expr_size(node.expr.type, env)) % 16 != 0:
                aligned = True
                program.stack.align(fn, 8)
            fn = gen_expr(node.expr, program, fn, env)
            if type(node.expr.type) is StructResolvedType:
                str = print_struct(node.expr.type, env)
            elif type(node.expr.type) is ArrayResolvedType and type(node.expr.type.type) is StructResolvedType:
                str = f"(ArrayType "
                str += print_struct(node.expr.type.type, env)
                str += f" {node.expr.type.rank})"
            else:
                str = node.expr.type.toString()[1:]
            if (f"`{str}`, 0", "") in program.constants:
                type_const = program.constants[(f"`{str}`, 0", "")][0]
            else:
                type_const = program.gensym_const()
                program.add_const(type_const, "db", f"`{str}`, 0", "")
            fn.code.append(f"lea rdi, [rel {type_const}]")
            fn.code.append("lea rsi, [rsp]")
            fn.code.append("call _show")
            program.stack.free(fn, get_expr_size(node.expr.type, env))
            if aligned: 
                program.stack.unalign(fn)
            return fn
        case "LetCmd":
            fn = gen_expr(node.expr, program, fn, env)
            add_lvalue(node.lvalue, fn, program, program.stack.size)
            return fn
        case "LetStmt":
            fn = gen_expr(node.expr, program, fn, env)
            base = get_stack_base(fn, program, env)
            add_lvalue(node.lvalue, fn, program, base)
            return fn
        case "FnCmd":
            # Initialize stuff used for setting up calling convention
            regs = []
            int_regs = ["rdi", "rsi", "rdx", "rcx", "r8", "r9"]
            float_regs = ["xmm0", "xmm1", "xmm2", "xmm3", "xmm4", "xmm5", "xmm6", "xmm7", "xmm8"]
            cc_stack_size = 0
            int_index = 0
            float_index = 0

            # Create the new function
            old_fn = fn
            fn = Function("_" + node.variable, [], {}, None, [])
            program.stack.push(fn, "rbp")
            stack_base = program.stack.size 
            #stack_base = 8
            fn.code.append("mov rbp, rsp")
            fn_info = env.get_function(node.variable)
            ret_val = 0
            #print(f"{fn.name} : {fn_info.fn_type}")
            if type(fn_info.fn_type) is IntResolvedType or type(fn_info.fn_type) is BoolResolvedType:
                ret_val = "rax"
            elif type(fn_info.fn_type) is VoidResolvedType:
                ret_val = "rax"
            elif type(fn_info.fn_type) is FloatResolvedType:
                ret_val = "xmm0"
            elif type(fn_info.fn_type) is StructResolvedType:
                program.stack.push(fn, "rdi")
                fn.stack_map["$return"] = program.stack.size - stack_base
                ret_val = (int)(get_expr_size(fn_info.fn_type, env) / 8) - 1
                cc_stack_size += 8
                int_index = 1 
            else:
                program.stack.push(fn, "rdi")
                fn.stack_map["$return"] = program.stack.size - stack_base
                ret_val = fn_info.fn_type.rank
                cc_stack_size += 8
                int_index = 1      
            # Initialize calling convention
            for binding in node.binding_list:
                if type(binding.type) is ArrayType:
                    regs.append((1, (cc_stack_size, 8 + (8 * binding.type.dimension))))
                    cc_stack_size += 8 + (8 * binding.type.dimension)
                elif type(binding.type) is StructType:
                    size = get_expr_size(binding.type, env)
                    regs.append((1, (cc_stack_size, size)))
                    cc_stack_size += size
                elif type(binding.type) is FloatType:
                    if float_index < len(float_regs):
                        regs.append((0, float_regs[float_index]))
                        float_index += 1
                    else:
                        regs.append((1, (cc_stack_size, 8)))
                        cc_stack_size += 8
                elif type(binding.type) is IntType or type(binding.type) is BoolType or type(binding.type) is VoidType:
                    if int_index < len(int_regs):
                        regs.append((0, int_regs[int_index]))
                        int_index += 1
                    else:
                        regs.append((1, (cc_stack_size, 8)))
                        cc_stack_size += 8
                else:
                    raise Exception(f"Invalid type passed as function argument")
            cc = CallingConvention(regs, ret_val, cc_stack_size, stack_base)
            env.functions[node.variable].cc = cc
            # Receive arguments
            # extra_space is because changing program.stack.size for the nonstack arguments messed up the add_lvalue call for stack arguments down below
            extra_space = 0
            for i in range(len(node.binding_list)):
                binding = node.binding_list[i]
                arg = cc.regs[i]
                if arg[0] == 0: #int
                    if arg[1].startswith("xmm"):
                        fn.code.append("sub rsp, 8")
                        fn.code.append(f"movsd [rsp], {arg[1]}")
                        program.stack.size += 8
                        extra_space += 8
                    else:
                        program.stack.push(fn, arg[1])
                        extra_space += 8
                    add_lvalue(binding.lvalue, fn, program, program.stack.size - cc.stack_base)
            for i in range(len(node.binding_list)):
                binding = node.binding_list[i]
                arg = cc.regs[i]
                if arg[0] == 1: #stack
                    add_lvalue(binding.lvalue, fn, program, program.stack.size - extra_space - arg[1][0] - cc.stack_base - 16)
            # Process statements
            has_ret = False
            for stmt in node.stmt_list:
                fn.code.append(f"; Processing statement: {stmt.toString()}")
                if type(stmt) is ReturnStmt:
                    has_ret = True
                fn = gen_cmd(stmt, program, fn, env, cc)
            if not has_ret:
                fn = gen_expr(VoidExpr(0), program, fn, env)
                program.stack.pop(fn, "rax")
                diff = program.stack.size - stack_base
                fn.code.append(f"add rsp, {diff}")
                program.stack.size -= diff
                program.stack.pop(fn, "rbp")
                fn.code.append("ret")
            # just change it at the end???
            program.stack.size = stack_base - 8
            program.fns.append(fn)
            return old_fn
        case "ReturnStmt":
            fn = gen_expr(node.expr, program, fn, env)
            if isinstance(cc.ret_val, int):
                if fn.name.startswith(".jump"):
                    ret_loc = fn.jump_parent.stack_map["$return"]
                else:
                    ret_loc = fn.stack_map["$return"]
                fn.code.append(f"mov rax, [rbp - {ret_loc}]") 
                #if type(node.expr.type) is ArrayResolvedType:
                copy_data_to_ret_address(8 * cc.ret_val, fn)
            elif(cc.ret_val.startswith("xmm")):
                fn.code.append(f"movsd {cc.ret_val}, [rsp]")
                fn.code.append("add rsp, 8 ; Local variables")
                program.stack.size -= 8
            else:
                program.stack.pop(fn, cc.ret_val)

            diff = program.stack.size - cc.stack_base
            fn.code.append(f"add rsp, {diff} ; Local variables")
            fn.code.append("pop rbp")
            fn.code.append("ret")
            return fn
        case "AssertCmd" | "AssertStmt":
            fn = gen_expr(node.expr, program, fn, env)
            program.stack.pop(fn, "rax")
            fn.code.append("cmp rax, 0")
            label = program.gen_jump()
            fn = assert_asm(node.string, "jne", label, fn, program, env)
            return fn
        case "ReadCmd":
            alloc(24, program, fn)
            fn.code.append("lea rdi, [rsp]")
            align = False
            if program.stack.size % 16 != 0:
                program.stack.align(fn, 8)
                align = True
            str = node.string.replace("\"", "")
            if (f"`{str}`, 0", "") in program.constants:
                type_const = program.constants[(f"`{str}`, 0", "")][0]
            else:
                type_const = program.gensym_const()
                program.add_const(type_const, "db", f"`{str}`, 0", "")
            fn.code.append(f"lea rsi, [rel {type_const}]")
            fn.code.append("call _read_image")
            if align:
                program.stack.unalign(fn)
            add_lvalue(node.lvalue, fn, program, program.stack.size)
            return fn
        case "WriteCmd":
            align = False
            if (program.stack.size + 24) % 16 != 0:
                program.stack.align(fn, 8)
                align = True
            fn = gen_expr(node.expr, program, fn, env)
            str = node.string.replace("\"", "")
            if (f"`{str}`, 0", "") in program.constants:
                type_const = program.constants[(f"`{str}`, 0", "")][0]
            else:
                type_const = program.gensym_const()
                program.add_const(type_const, "db", f"`{str}`, 0", "")
            fn.code.append(f"lea rdi, [rel {type_const}]")
            fn.code.append("call _write_image")
            program.stack.free(fn, get_expr_size(node.expr.type, env))
            if align:
                program.stack.unalign(fn)
            return fn
        case "PrintCmd":
            # if type(node.expr.type) is StructResolvedType:
            #     str = print_struct(node.expr.type, env)
            # elif type(node.expr.type) is ArrayResolvedType and type(node.expr.type.type) is StructResolvedType:
            #     str = f"(ArrayType "
            #     str += print_struct(node.expr.type.type, env)
            #     str += f" {node.expr.type.rank})"
            # else:
            #     str = node.expr.type.toString()[1:]
            str = node.string
            if (f"`{str}`, 0", "") in program.constants:
                const = program.constants[(f"`{str}`, 0", "")][0]
            else:
                const = program.gensym_const()
                program.add_const(const, "db", f"`{str}`, 0", "")
            fn.code.append(f"lea rdi, [rel {const}]")
            align = False
            if program.stack.size % 16 != 0:
                program.stack.align(fn, 8)
                align = True
            fn.code.append("call _print")
            if align:
                program.stack.unalign(fn)
            return fn
        case "StructCmd":
            return fn
        case "TimeCmd":
            fn = get_time(fn, program)
            size_before = program.stack.size #does this go before or after first get_time call?
            fn = gen_cmd(node.cmd, program, fn, env, None)
            fn = get_time(fn, program)
            fn.code.append(f"movsd xmm0, [rsp]")
            program.stack.size -= 8
            fn.code.append(f"add rsp, 8")
            fn.code.append(f"movsd xmm1, [rsp + {program.stack.size - size_before}]")
            fn.code.append(f"subsd xmm0, xmm1")
            align = False
            if program.stack.size % 16 != 0:
                program.stack.align(fn, 8)
                align = True
            fn.code.append("call _print_time")
            if align:
                program.stack.unalign(fn)
            return fn
        case _:
            raise Exception(f"ASTNode of type {type(node).__name__}; invalid for HW10")
        
def get_time(fn, program):
    #cc = CallingConvention([], "xmm0", 0, program.stack.size)
    align = False
    if program.stack.size % 16 != 0:
        program.stack.align(fn, 8)
        align = True
    fn.code.append("call _get_time")
    if align:
        program.stack.unalign(fn)
    fn.code.append("sub rsp, 8")
    program.stack.size += 8
    fn.code.append("movsd [rsp], xmm0")
    return fn

def gen_prologue(fn, assembly_code):
    return assembly_code + "\tpush rbp\n\tmov rbp, rsp\n\tpush r12\n\tmov r12, rbp\n"

def print_struct(struct_type, env):
    code = "(TupleType"
    name_info = env.get_struct(struct_type.name)
    for field in name_info:
        if type(field[1]) is StructResolvedType:
            code += " "
            code += print_struct(field[1], env)
        elif type(field[1]) is ArrayResolvedType and type(field[1].type) is StructResolvedType:
            code += " (ArrayType "
            code += print_struct(field[1].type, env)
            code += f" {field[1].rank})"
        else:
            code += field[1].toString()
    if len(name_info) == 0:
        code += " "
    code += f")"
    return code

def gen_epilogue(fn, assembly_code):
    return assembly_code + "\tpop r12\n\tpop rbp\n\tret"

def process_fn(assembly_code, fn):
    if fn.processed == True:
        return assembly_code
    fn.processed = True
    if not fn.name.startswith(".jump"):
        assembly_code += f"{fn.name[1:]}:\n"
    assembly_code += f"{fn.name}:\n"
    if fn.name == "_jpl_main":
        assembly_code = gen_prologue(fn, assembly_code)
    #process the parent first
    if fn.jump_parent is not None:
        assembly_code = process_parent(assembly_code, fn.jump_parent)
    #then we process this function
    for line in fn.code:
        assembly_code += f"\t{line}\n"
    #then we process the child
    for child in fn.jump_children:
        assembly_code = process_fn(assembly_code, child)
    if fn.name=="_jpl_main":
        assembly_code = gen_epilogue(fn, assembly_code)
    return assembly_code

def process_parent(assembly_code, fn):
    if fn.processed == True:
        return assembly_code
    fn.processed = True
    for line in fn.code:
        assembly_code += f"\t{line}\n"
    return assembly_code
#currently unused but might be used later
def process_child(assembly_code, fn):
    if fn.processed == True:
        return assembly_code
    fn.processed = True
    for line in fn.code:
        assembly_code += f"\t{line}\n"
    return assembly_code

def gen_assembly_program(nodes, env, opt_level):
    linkage_init = ["global jpl_main", "global _jpl_main", "extern _fail_assertion", "extern _jpl_alloc", "extern _get_time", 
                    "extern _show", "extern _print", "extern _print_time", "extern _read_image", "extern _write_image", "extern _fmod", 
                    "extern _sqrt", "extern _exp", "extern _sin", "extern _cos", "extern _tan", "extern _asin", "extern _acos", "extern _atan", 
                    "extern _log", "extern _pow", "extern _atan2", "extern _to_int", "extern _to_float"] 
    stack = Stack([])
    program = Assembly({}, linkage_init, [], stack, {}, opt_level)
    main_fn = Function("_jpl_main", [], {}, None, []) # prologue and epilogue will be generated when formatting the output
    program.fns.append(main_fn)

    fn = main_fn

    arg_lval = (ArrayLvalue(0, "args", ["argnum"]))
    add_lvalue(arg_lval, fn, program, -16)

    for node in nodes:
        fn = gen_cmd(node, program, fn, env, None)
    #this is done to free all local variables at the end of code
    if program.stack.size > 8:
        program.stack.free(fn, program.stack.size-8)

    assembly_code = ""

    for cmd in program.linkage_cmds:
        assembly_code += f"{cmd}\n"
    
    assembly_code += "\nsection .data\n"

    sorted_consts = sorted(program.constants.items(), key=lambda item: int(item[1][0][5:]))
    for item in sorted_consts:
        assembly_code += f"{item[1][0]}: {item[1][1]} {item[0][0]}\n"

    assembly_code += "\nsection .text\n"

    for i in range(1,len(program.fns)):
        fn = program.fns[i]
        if not fn.processed and fn not in program.fns[0].jump_children:
            assembly_code = process_fn(assembly_code, fn)
    
    assembly_code = process_fn(assembly_code,program.fns[0]) #process JPL main

    return assembly_code