from environment import *
#TODO: ADD SEMICOLONS TO CODE
#TODO: ADD PROGRAM PARAM TO EVERY METHOD CALL
#C_program using string literals for type hints
class C_fn():
    def __init__(self, name: str, code: list[str], parent: 'C_program', name_ctr: int, ctx: dict[str, str], args: list[str]):
        self.name = name
        self.code = code
        self.parent = parent
        self.name_ctr = name_ctr #initialize to 0 or use a parameter? dont all variable names need to be unique?
        self.ctx = ctx
        self.args = args

    def gensym(self):
        n = "_" + str(self.name_ctr)
        self.name_ctr += 1
        return n

class C_program():
    def __init__(self, fns: list[C_fn], structs: list[(str, list[str])], jump_ctr: int, ctx: Environment): ##replace C_fields with actual data type later
        self.fns = fns
        self.structs = structs
        self.jump_ctr = jump_ctr
        self.ctx = ctx

    def genjump(self):
        n = "_jump" + str(self.jump_ctr)
        self.jump_ctr += 1
        return n
    
def gen_array_struct(rank, type, program):
    arr_name = f"_a{rank}_{type}"
    if arr_name == "_a2_rgba":
        return arr_name
    fields = []
    for i in range(rank):
        fields.append(f"int64_t d{i};")
    fields.append(f"{type} *data;")
    if (arr_name, fields) in program.structs:
        return arr_name
    program.structs.append((arr_name, fields))
    return arr_name
    
def type_to_C(type_node, program):
    match (type(type_node).__name__):
        case "IntType" | "IntResolvedType":
            return "int64_t"
        case "BoolType" | "BoolResolvedType":
            return "bool"
        case "FloatType" | "FloatResolvedType":
            return "double"
        case "ArrayType":
            return gen_array_struct(type_node.dimension, type_to_C(type_node.type, program), program)
        case "ArrayResolvedType":
            return gen_array_struct(type_node.rank, type_to_C(type_node.type, program), program)
        case "StructType":
            return type_node.variable
        case "StructResolvedType":
            return type_node.name
        case "VoidType" | "VoidResolvedType":
            return "void_t"
        case _:
            raise Exception(f"ASTNode of type {type(type_node).__name__}; invalid at {type_node.start}")

def expr_to_C(expr_node, parent_fn, env, program):
    # call gensym to generate ugly name
    # generate c code assigning this name to the expression's value and return the name
    # update ctx
    match (type(expr_node).__name__):
        case "IntExpr":
            name = parent_fn.gensym()
            parent_fn.code.append(f"int64_t {name} = {expr_node.i};")
        case "FloatExpr":
            name = parent_fn.gensym()
            parent_fn.code.append(f"double {name} = {int(expr_node.f)}.0;")
        case "TrueExpr":
            name = parent_fn.gensym()
            parent_fn.code.append(f"bool {name} = true;")
        case "FalseExpr":
            name = parent_fn.gensym()
            parent_fn.code.append(f"bool {name} = false;")
        case "VariableExpr":
            if expr_node.variable in parent_fn.ctx:
                name = parent_fn.ctx[expr_node.variable]
            else:
                name = expr_node.variable
        case "ArrayExpr":
            gen_names = []
            d0 = len(expr_node.expr_list)
            for expr in expr_node.expr_list:
                gen_names.append(expr_to_C(expr, parent_fn, env, program)) 
            arr_name = parent_fn.gensym()
            arr_type = type_to_C(expr_node.type, program)
            actual_type = type_to_C(expr_node.type.type, program)
            parent_fn.code.append(f"{arr_type} {arr_name};")
            parent_fn.code.append(f"{arr_name}.d0 = {d0};")
            parent_fn.code.append(f"{arr_name}.data = jpl_alloc(sizeof({actual_type}) * {d0});")
            for i in range(d0):
                parent_fn.code.append(f"{arr_name}.data[{i}] = {gen_names[i]};")
            name = arr_name
        case "VoidExpr":
            name = parent_fn.gensym()
            parent_fn.code.append(f"void_t {name} = {{}};")
        case "StructLiteralExpr":
            gen_names = []
            for expr in expr_node.expr_list:
                gen_names.append(expr_to_C(expr, parent_fn, env, program))
            struct_name = parent_fn.gensym()
            code = f"{expr_node.variable} {struct_name} = " + "{ "
            if len(gen_names) > 0:
                code += (f"{gen_names[0]}")
            for name in gen_names[1:]:
                code += (f", {name}")
            code += (" };")
            parent_fn.code.append(code)
            name = struct_name
        case "DotExpr":
            #we will be "binding" the dot expr here by creating a new variable and assigning its value to a new var
            expr_name = expr_to_C(expr_node.expr, parent_fn, env, program)
            expr_type = type_to_C(expr_node.type, program)
            binding_name = parent_fn.gensym()
            parent_fn.code.append(f"{expr_type} {binding_name} = {expr_name}.{expr_node.variable};")
            name = binding_name
        case "ArrayIndexExpr":
            arr_name = expr_to_C(expr_node.expr, parent_fn, env, program)
            idx_names = []
            for expr in expr_node.expr_list:
                idx_names.append(expr_to_C(expr, parent_fn, env, program))
            for i in range(len(idx_names)):
                idx = idx_names[i]
                jump_name = program.genjump()
                parent_fn.code.append(f"if ({idx} >= 0)")
                parent_fn.code.append(f"goto {jump_name};")
                parent_fn.code.append(f"fail_assertion(\"{"negative array index"}\");")
                parent_fn.code.append(f"{jump_name}:;")
                jump_name = program.genjump()
                parent_fn.code.append(f"if ({idx} < {arr_name}.d{i})")
                parent_fn.code.append(f"goto {jump_name};")
                parent_fn.code.append(f"fail_assertion(\"{"index too large"}\");")
                parent_fn.code.append(f"{jump_name}:;")
            iname = parent_fn.gensym()
            parent_fn.code.append(f"int64_t {iname} = 0;")
            for i in range(len(idx_names)):
                parent_fn.code.append(f"{iname} *= {arr_name}.d{i};")
                parent_fn.code.append(f"{iname} += {idx_names[i]};")
            data_type = type_to_C(expr_node.type, program)
            data_var = parent_fn.gensym()
            parent_fn.code.append(f"{data_type} {data_var} = {arr_name}.data[{iname}];")
            name = data_var
        case "CallExpr":
            args = []
            for expr in expr_node.expr_list:
                args.append(expr_to_C(expr, parent_fn, env, program))
            name = parent_fn.gensym()
            code = f"{type_to_C(expr_node.type, program)} {name} = {expr_node.variable}("
            for arg in args[:-1]:
                code += f"{arg}, "
            if len(args) > 0:
                code += f"{args[-1]}"
            code += ");"
            parent_fn.code.append(code)
        case "UnopExpr":
            expr_name = expr_to_C(expr_node.expr, parent_fn, env, program)
            expr_type = type_to_C(expr_node.type, program)
            name = parent_fn.gensym()
            parent_fn.code.append(f"{expr_type} {name} = {expr_node.op.text}{expr_name}")
        case "BinopExpr":
            if expr_node.op.text == "&&" or expr_node.op.text == "||":
                name = parent_fn.gensym()
                l_expr = expr_to_C(expr_node.l_expr, parent_fn, env, program)
                expr_type = type_to_C(expr_node.type, program)
                parent_fn.code.append(f"{expr_type} {name} = {l_expr};")
                if expr_node.op.text == "&&":
                    parent_fn.code.append(f"if (0 == {l_expr})")
                else:
                    parent_fn.code.append(f"if (0 != {l_expr})")
                end_label = program.genjump()
                parent_fn.code.append(f"goto {end_label};")
                r_expr = expr_to_C(expr_node.r_expr, parent_fn, env, program)
                parent_fn.code.append(f"{name} = {r_expr};")
                parent_fn.code.append(f"{end_label}:;")
            else:
                l_expr = expr_to_C(expr_node.l_expr, parent_fn, env, program)
                r_expr = expr_to_C(expr_node.r_expr, parent_fn, env, program)
                name = parent_fn.gensym()
                if expr_node.op.text == "%" and type(expr_node.type) is FloatResolvedType:
                    parent_fn.code.append(f"double {name} = fmod({l_expr}, {r_expr});")
                else:
                    expr_type = type_to_C(expr_node.type, program)
                    parent_fn.code.append(f"{expr_type} {name} = {l_expr} {expr_node.op.text} {r_expr};")
        case "IfExpr":
            e_1_name = expr_to_C(expr_node.cndn_expr, parent_fn, env, program)
            name = parent_fn.gensym()
            expr_type = type_to_C(expr_node.type, program)
            parent_fn.code.append(f"{expr_type} {name};")
            parent_fn.code.append(f"if (!{e_1_name})")
            jump_label1 = program.genjump()
            parent_fn.code.append(f"goto {jump_label1}")
            e_2_name = expr_to_C(expr_node.then_expr, parent_fn, env, program)
            parent_fn.code.append(f"{name} = {e_2_name}")
            jump_label2 = program.genjump()
            parent_fn.code.append(f"goto {jump_label2};")
            parent_fn.code.append(f"{jump_label1}:;")
            e_3_name = expr_to_C(expr_node.else_expr, parent_fn, env, program)
            parent_fn.code.append(f"{name} = {e_3_name}")
            parent_fn.code.append(f"{jump_label2}:;")
        case "ArrayLoopExpr":
            out_type = type_to_C(expr_node.type, program)
            out_name = parent_fn.gensym()
            parent_fn.code.append(f"{out_type} {out_name};")
            bound_names = []
            for i in range(len(expr_node.list)):
                expr_tuple = expr_node.list[i]
                bound_name = expr_to_C(expr_tuple[1], parent_fn, env, program)
                bound_names.append(bound_name)
                parent_fn.code.append(f"{out_name}.d{i} = {bound_name}")
                parent_fn.code.append(f"if ({bound_name} > 0)")
                jump_label = program.genjump()
                parent_fn.code.append(f"goto {jump_label};")
                parent_fn.code.append("fail_assertion(\"non-positive loop bound\");")
                parent_fn.code.append(f"{jump_label}:;")
            index_vars = []
            size = parent_fn.gensym()
            parent_fn.code.append(f"int64_t {size} = 1;")
            for name in (bound_names):
                parent_fn.code.append(f"{size} *= {name};")
            parent_fn.code.append(f"{size} *= sizeof({type_to_C(expr_node.type.type, program)});")
            parent_fn.code.append(f"{out_name}.data = jpl_alloc({size});")
            for i in range(len(expr_node.list)):
                index_var = parent_fn.gensym()
                parent_fn.ctx[expr_node.list[len(expr_node.list)-i-1][0]] = index_var #add to context here or in expr loop?
                index_vars.append(index_var)
                parent_fn.code.append(f"int64_t {index_var} = 0;")
            top_loop_jump = program.genjump()
            parent_fn.code.append(f"{top_loop_jump}:;")
            body_name = expr_to_C(expr_node.expr, parent_fn, env, program)
            index = parent_fn.gensym()
            parent_fn.code.append(f"int64_t {index} = 0;")
            for i in range(len(index_vars)):
                parent_fn.code.append(f"{index} *= {out_name}.d{i}")
                parent_fn.code.append(f"{index} += {index_vars[len(index_vars)-i-1]};")
            parent_fn.code.append(f"{out_name}.data[{index}] = {body_name}")
            for i in range(len(index_vars)): #may need to iterate through list in reverse order
                parent_fn.code.append(f"{index_vars[i]}++;")
                parent_fn.code.append(f"if ({index_vars[i]} < {bound_names[len(index_vars)-i-1]})")
                parent_fn.code.append(f"goto {top_loop_jump};")
                if i < len(expr_node.list) - 1:
                    parent_fn.code.append(f"{index_vars[i]} = 0;")
            name = out_name
        case "SumLoopExpr":
            out_type = type_to_C(expr_node.type, program)
            out_name = parent_fn.gensym()
            parent_fn.code.append(f"{out_type} {out_name};")
            bound_names = []
            for expr_tuple in expr_node.list:
                bound_name = expr_to_C(expr_tuple[1], parent_fn, env, program)
                bound_names.append(bound_name)
                parent_fn.code.append(f"if ({bound_name} > 0)")
                jump_label = program.genjump()
                parent_fn.code.append(f"goto {jump_label};")
                parent_fn.code.append("fail_assertion(\"non-positive loop bound\");")
                parent_fn.code.append(f"{jump_label}:;")
            parent_fn.code.append(f"{out_name} = 0;")
            index_vars = []
            for i in range(len(expr_node.list)):
                index_var = parent_fn.gensym()
                parent_fn.ctx[expr_node.list[len(expr_node.list)-i-1][0]] = index_var #add to context here or in expr loop?
                index_vars.append(index_var)
                parent_fn.code.append(f"int64_t {index_var} = 0;")
            top_loop_jump = program.genjump()
            parent_fn.code.append(f"{top_loop_jump}:;")
            body_name = expr_to_C(expr_node.expr, parent_fn, env, program)
            parent_fn.code.append(f"{out_name} += {body_name};")
            for i in range(len(index_vars)): #may need to iterate through list in reverse order
                parent_fn.code.append(f"{index_vars[i]}++;")
                parent_fn.code.append(f"if ({index_vars[i]} < {bound_names[len(index_vars)-i-1]})")
                parent_fn.code.append(f"goto {top_loop_jump};")
                if i < len(expr_node.list) - 1:
                    parent_fn.code.append(f"{index_vars[i]} = 0;")
            name = out_name
        case _:
            raise Exception(f"ASTNode of type {type(expr_node).__name__}; invalid at {expr_node.start}")
    return name

def print_struct(struct_type, program):
    code = "(TupleType"
    name_info = program.ctx.get_struct(struct_type.name)
    for field in name_info:
        if type(field[1]) is StructResolvedType:
            code += " "
            code += print_struct(field[1], program)
        elif type(field[1]) is ArrayResolvedType and type(field[1].type) is StructResolvedType:
            code += " (ArrayType "
            code += print_struct(field[1].type, program)
            code += f" {field[1].rank})"
        else:
            code += field[1].toString()
    if len(name_info) == 0:
        code += " "
    code += f")"
    return code

def cmd_to_C(node, parent_fn, env, program):
     match (type(node).__name__):
        case "ShowCmd":
            name = expr_to_C(node.expr, parent_fn, env, program)
            if type(node.expr.type) is StructResolvedType:
                code = f"show(\""
                code += print_struct(node.expr.type, program)
                code += f"\", &{name})"
                parent_fn.code.append(code)
            elif type(node.expr.type) is ArrayResolvedType and type(node.expr.type.type) is StructResolvedType:
                code = f"show(\"(ArrayType "
                code += print_struct(node.expr.type.type, program)
                code += f" {node.expr.type.rank})"
                parent_fn.code.append(code)
            else:
                parent_fn.code.append(f"show(\"{node.expr.type.toString()[1:]}\", &{name})")
        case "StructCmd":
            c_fields = []
            for field in node.field_list:
                c_fields.append(f"{type_to_C(field[1], program)} {field[0]}")
            program.structs.append((node.variable, c_fields))
        case "LetCmd" | "LetStmt":
            name = expr_to_C(node.expr, parent_fn, env, program)
            if type(node.lvalue).__name__ == "ArrayLvalue":
                for i in range(len(node.lvalue.variable_list)):
                    parent_fn.ctx[node.lvalue.variable_list[i]] = f"{name}.d{i}"
            parent_fn.ctx[node.lvalue.variable] = name #lvalue is mapped to the generated name in fn context
        case "ReadCmd":
            name = parent_fn.gensym()
            parent_fn.code.append(f"_a2_rgba {name} = read_image({node.string});")
            parent_fn.ctx[node.lvalue.variable] = name
            if type(node.lvalue) is ArrayLvalue:
                for i in range(len(node.lvalue.variable_list)):
                    parent_fn.code.append(f"int64_t {node.lvalue.variable_list[i]} = {name}.d{i};")
                    parent_fn.ctx[node.lvalue.variable_list[i]] = f"{name}.d{i}"
        case "WriteCmd":
            name = expr_to_C(node.expr, parent_fn, env, program)
            parent_fn.code.append(f"write_image({name}, {node.string});")
        case "AssertCmd" | "AssertStmt":
            name = expr_to_C(node.expr, parent_fn, env, program)
            parent_fn.code.append(f"if (0 != {name})")
            jump = program.genjump()
            parent_fn.code.append(f"goto {jump}")
            parent_fn.code.append(f"fail_assertion({node.string})")
            parent_fn.code.append(f"{jump}:")
        case "PrintCmd":
            parent_fn.code.append(f"print({node.string})")
        case "TimeCmd":
            start_name = parent_fn.gensym()
            parent_fn.code.append(f"double {start_name} = get_time();")
            cmd_to_C(node.cmd, parent_fn, env, program)
            end_name = parent_fn.gensym()
            parent_fn.code.append(f"double {end_name} = get_time();")
            parent_fn.code.append(f"print_time({end_name} - {start_name});")
        case "FnCmd":
            args = []
            arg_dict = {}
            type_to_C(env.get_function(node.variable).fn_type, program)
            for binding in node.binding_list:
                args.append(f"{type_to_C(binding.type, program)} {binding.lvalue.variable}") # do we need to handle ArrayLvalue case?
                if type(binding.lvalue) is ArrayLvalue:
                    for i in range(len(binding.lvalue.variable_list)):
                        arg_dict[binding.lvalue.variable_list[i]] =f"{binding.lvalue.variable}.d{i}"
                arg_dict[binding.lvalue.variable] = binding.lvalue.variable
            fn = C_fn(node.variable, [], program, 0, arg_dict, args)
            child_env = env.get_function(node.variable).env
            has_ret = False
            for stmt in node.stmt_list:
                cmd_to_C(stmt, fn, child_env, program) # this function's child env instead of root env, right?
                if type(stmt) is ReturnStmt:
                    has_ret = True
            if type(env.get_function(node.variable).fn_type) is VoidResolvedType and has_ret is False:
                ret_val = fn.gensym()
                fn.code.append(f"void_t {ret_val} = {{}};")
                fn.code.append(f"return {ret_val};")
            program.fns.append(fn)
        case "ReturnStmt":
            ret_expr = expr_to_C(node.expr, parent_fn, env, program)
            parent_fn.code.append(f"return {ret_expr};")
        case _:
            raise Exception(f"ASTNode of type {type(node).__name__}; invalid for HW8 at {node.start}")
         
def gen_struct_header(struct: (str, list[str])): # type: ignore
    code = "typedef struct { \n"
    for field in struct[1]:
        code += f"\t {field}\n"
    code += "} " + f"{struct[0]}; \n \n"
    return code

#TODO: for hw9 find a way to account for parameters in function calls
# the environment contains return types and types of parameters, but jpl_main is its own special case
def gen_function_code(fn, fn_info, program):
    code = ""
    if fn.name == "jpl_main":
        code += "void jpl_main(struct args args) { \n"
    else:
        code += f"{type_to_C(fn_info.fn_type, program)} {fn.name}("
        for arg in fn.args[:-1]:
            code += f"{arg}, "
        if len(fn.args) > 0:
            code += f"{fn.args[-1]}"
        code += ") { \n"

    for line in fn.code:
        code += "\t" + line + "\n" 
    code += "} \n"
    return code
            
def gen_C_program(nodes, env):
    program = C_program([], [], 1, env)
    main_fn = C_fn("jpl_main", [], program, 0, {"argnum": "args.d0"}, [])
    program.fns.append(main_fn)
    c_code = ""

    for node in nodes:
        cmd_to_C(node, main_fn, env, program)

    header = f"{"#include <math.h>"}\n{"#include <stdbool.h>"}\n{"#include <stdint.h>"}\n{"#include <stdio.h>"}\n#include \"{"rt/runtime.h"}\" \n"
    void_struct = "typedef struct { } void_t;\n\n"
    c_code += header + void_struct
    for struct in program.structs:
        c_code += gen_struct_header(struct)
    if len(program.fns) > 1:
        for fn in program.fns[1:]: 
            c_code += gen_function_code(fn, env.get_function(fn.name), program)
    c_code += gen_function_code(program.fns[0], env.get_function(program.fns[0].name), program)

    return c_code
