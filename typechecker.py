from astnodes import *
from environment import *
from functioninfo import *

# add the default structs and functions to our environemnt map
def prepopulate_env():
    #env = {"rgba" :[("r", FloatResolvedType()), ("g", FloatResolvedType()), ("b", FloatResolvedType()), ("a", FloatResolvedType())]}
    env = Environment(None)
    #variables
    env.add_var("args", ArrayResolvedType(1, IntResolvedType()))
    env.add_var("argnum", IntResolvedType())
    #structs
    env.add_struct("rgba", [("r", FloatResolvedType()), ("g", FloatResolvedType()), ("b", FloatResolvedType()), ("a", FloatResolvedType())])
    #math functions with one float argument that return a float
    one_float = FunctionInfo(FloatResolvedType(), [FloatResolvedType()], Environment(env))
    one_float.cc = CallingConvention([(0, "xmm0")], "xmm0", 0, 0)
    env.add_function("sqrt", one_float)
    env.add_function("exp", one_float)
    env.add_function("sin", one_float)
    env.add_function("cos", one_float)
    env.add_function("tan", one_float)
    env.add_function("asin", one_float)
    env.add_function("acos", one_float)
    env.add_function("atan", one_float)
    env.add_function("log", one_float)
    #math functions with two float arguments that return a float
    two_float = FunctionInfo(FloatResolvedType(), [FloatResolvedType(), FloatResolvedType()], Environment(env))
    two_float.cc = CallingConvention([(0, "xmm0"), (0, "xmm1")], "xmm0", 0, 0)
    env.add_function("pow", two_float)
    env.add_function("atan2", two_float)
    #conversion functions
    env.add_function("to_float", FunctionInfo(FloatResolvedType(), [IntResolvedType()], Environment(env)))
    env.get_function("to_float").cc = CallingConvention([(0, "rdi")], "xmm0", 0, 0)
    env.add_function("to_int", FunctionInfo(IntResolvedType(), [FloatResolvedType()], Environment(env)))
    env.get_function("to_int").cc = CallingConvention([(0, "xmm0")], "rax", 0, 0)
    # add other builtins
    return env

"""
    Recursively compute the type of each subexpression
    Apply the type rules to determine what the type of the output is
    Raise a type error if the type rules are violated
    Store the output type in the input AST node (useful when printing S-expressions)
    Return the output type as well (useful in recursive type_of calls)

In your compiler, call typecheck after parsing. Then use your exising S-expression printer (modified to print types too) to print the results.
"""
def type_of(expr_node, env):
    match(type(expr_node).__name__):
        case "IntExpr":
            expr_node.type = IntResolvedType()
        case "FloatExpr":
            expr_node.type = FloatResolvedType()
        case "TrueExpr":
            expr_node.type = BoolResolvedType()
        case "FalseExpr":
            expr_node.type = BoolResolvedType()
        case "VariableExpr":
            # Verify that this variable is in the environment
            # Return this variable's type
            result = env.get_var(expr_node.variable)
            if result is None:
                raise Exception(f"Undefined variable at {expr_node.start}, {expr_node.variable}")
            else:
                expr_node.type = result
        case "ArrayExpr":
            #maybe some inconsistency with the way we have AST nodes (?)
            if len(expr_node.expr_list) == 0: #is this even allowed?
                raise Exception(f"Empty Array at {expr_node.start}")
            else:
                first_type = type_of(expr_node.expr_list[0], env)
                for expr in expr_node.expr_list[1:]:
                    if first_type != type_of(expr, env):
                        raise Exception(f"Type mismatch in array at index: {expr_node.start}")
            expr_node.type = ArrayResolvedType(1, first_type)
        case "VoidExpr":
            expr_node.type = VoidResolvedType()
        case "StructLiteralExpr":
            struct_name = expr_node.variable
            if not env.has(struct_name):
                raise Exception(f"struct {struct_name} not declared at index: {expr_node.start}")
            env_fields = env.get_struct(struct_name)
            if len(env_fields) != len(expr_node.expr_list):
                raise Exception(f"inconsistent lengths for struct fields at index: {expr_node.start}")
            else:
                for i in range(len(env_fields)):
                    if (env_fields[i][1] != type_of(expr_node.expr_list[i], env)):
                        raise Exception(f"inconsistent types for struct fields at index: {expr_node.start}")
            expr_node.type = StructResolvedType(struct_name)
        case "DotExpr":
            struct_type = type_of(expr_node.expr, env)
            if type(struct_type) is not StructResolvedType:
                raise Exception(f"expression in dotexpr was not a struct index: {expr_node.start}")
            else:
                for tup in env.get_struct(struct_type.name):
                    if tup[0] == expr_node.variable:
                        expr_node.type = tup[1]
                        return tup[1]
                raise Exception(f"attempting to access non-existent field in struct {struct_type.name} at index: {expr_node.start}")
        case "ArrayIndexExpr":
            array_type = type_of(expr_node.expr, env)
            if type(array_type) is not ArrayResolvedType:
                raise Exception(f"expression in array index expression was not an array at index: {expr_node.start}")
            if len(expr_node.expr_list) != array_type.rank:
                raise Exception(f"array ranks did not match at index: {expr_node.start}")
            expr_type = array_type.type
            for expr in expr_node.expr_list:
                if type_of(expr, env) != IntResolvedType():
                    raise Exception(f"Non-integer array index at index: {expr_node.start}")
            expr_node.type = expr_type
        case "CallExpr":
            fn_info = env.get_function(expr_node.variable)
            if fn_info is None:
                raise Exception(f"Tried to call a function that is not defined at index: {expr_node.start} in function {expr_node.variable}")
            elif len(fn_info.arg_types) != len(expr_node.expr_list):
                raise Exception(f"mismatch for number of parameters passed and required at index: {expr_node.start}  in function {expr_node.variable}")
            for i in range(len(expr_node.expr_list)):
                if type_of(expr_node.expr_list[i], env) != fn_info.arg_types[i]:
                    raise Exception(f"type mismatch for {i}th parameter in function {expr_node.variable} at index: {expr_node.start}")
            expr_node.type = fn_info.fn_type
        case "UnopExpr":
            match expr_node.op.text:
                case "!":
                    if type_of(expr_node.expr, env) != BoolResolvedType():
                        raise Exception(f"non-boolean expression at index: {expr_node.start}")
                    expr_node.type = BoolResolvedType()
                case "-":
                    expr_type = type_of(expr_node.expr, env)
                    if expr_type == IntResolvedType():
                        expr_node.type = IntResolvedType()
                    elif expr_type == FloatResolvedType():
                        expr_node.type = FloatResolvedType()
                    else:
                        raise Exception(f"non-numerical expression at index: {expr_node.start}")
        case "BinopExpr":
            ret_val = ""
            expr_type = type_of(expr_node.l_expr, env)
            if expr_node.op.text == "==" or expr_node.op.text == "!=":
                if expr_type != IntResolvedType() and expr_type != FloatResolvedType() and expr_type != BoolResolvedType():
                    raise Exception(f"{expr_type} instead of numerical or boolean type for equality operator at index: {expr_node.start}")
            elif expr_node.op.text == "&&" or expr_node.op.text == "||":
                if expr_type != BoolResolvedType():
                    raise Exception(f"{expr_type} instead of boolean type for boolean operator at index: {expr_node.start}")
            else:
                if expr_type != IntResolvedType() and expr_type != FloatResolvedType():
                    raise Exception(f"{expr_type} instead of numerical type for arithmetic operator at index: {expr_node.start} {expr_node.toString()}")
            if type_of(expr_node.r_expr, env) != expr_type:
                raise Exception(f"mismatched types for binary operator at index: {expr_node.start}")
            if expr_node.op.text == "==" or expr_node.op.text == "!=" or expr_node.op.text == "<=" or expr_node.op.text == ">=" or expr_node.op.text == "<" or expr_node.op.text == ">":
                expr_node.type = BoolResolvedType()
            else:
                expr_node.type = expr_type
        case "IfExpr":
            if type_of(expr_node.cndn_expr, env) != BoolResolvedType():
                raise Exception(f"{expr_type} instead of boolean for if expression condition at index: {expr_node.start}")
            then_type = type_of(expr_node.then_expr, env) 
            if then_type != type_of(expr_node.else_expr, env):
                raise Exception(f"mismatched types for if expression at index: {expr_node.start}")
            expr_node.type = then_type
        case "ArrayLoopExpr":
            # Check that bound expressions have int type
            # Create child environment with these expressions mapped to integers
            # Verify that the body evaluates to an array type of correct rank
            child = Environment(env)
            if len(expr_node.list) == 0:
                raise Exception(f"Empty array loop bounds at index: {expr_node.start}")
            for tup in expr_node.list:
                if type_of(tup[1], env) != IntResolvedType():
                    raise Exception(f"Non-integer type for array loop bound at index: {expr_node.start}")
                child.add_var(tup[0], IntResolvedType())
            body_type = type_of(expr_node.expr, child)
            """if body_type is not ArrayResolvedType:
                raise Exception(f"Non-array type for array loop body at index: {expr_node.start}")
            if body_type.rank != expr_node.list.length:
                raise Exception(f"Mismatched rank for array loop body at index: {expr_node.start}")"""
            #else:
            expr_node.type = ArrayResolvedType(len(expr_node.list), body_type)
        case "SumLoopExpr":
            # Check that bound expressions have int type
            # Create child environment with these expressions mapped to integers
            # Verify that the body evaluates to an int or float type
            child = Environment(env)
            if len(expr_node.list) == 0:
                raise Exception(f"Empty array loop bounds at index: {expr_node.start}")
            for tup in expr_node.list:
                if type_of(tup[1], env) != IntResolvedType():
                    raise Exception(f"Non-integer type for array loop bound at index: {expr_node.start}")
                child.add_var(tup[0], IntResolvedType())
            body_type = type_of(expr_node.expr, child)
            if body_type != IntResolvedType() and body_type != FloatResolvedType():
                raise Exception(f"Non-numerical type for sum loop body at index: {expr_node.start}")
            else:
                expr_node.type = body_type            
        case _:
            raise Exception(f"type name {type(expr_node).__name__} matches no cases at index: {expr_node.start}")
    return expr_node.type

def get_resolved_type(field, env):
    match type(field).__name__:
        case "IntType":
            return IntResolvedType()
        case "BoolType":
            return BoolResolvedType()
        case "FloatType":
            return FloatResolvedType()
        case "ArrayType":
            return ArrayResolvedType(field.dimension, get_resolved_type(field.type, env))
        case "VoidType":
            return VoidResolvedType()
        case "StructType":
            struct_name = field.variable
            if not env.has(struct_name):
                raise Exception(f"Struct {struct_name} undeclared at index: {field.start}")
            return StructResolvedType(struct_name)
        
def typecheck_cmd(node, env):
    match(type(node).__name__):
            case "ShowCmd":
                node.type = type_of(node.expr, env) #why do we have this?
            case "StructCmd":
                struct_name = node.variable
                #how would we handle if a second struct is made with same name?
                if env.has(struct_name):
                    raise Exception(f"Struct {struct_name} previously declared at index: {node.start}")
                struct_fields = []
                field_names = {}
                for field in node.field_list:
                    if field[0] in field_names:
                        raise Exception(f"redfining struct field {field[0]} at index: {node.start}")
                    struct_fields.append((field[0],get_resolved_type(field[1], env)))
                    field_names[field[0]] = True
                env.add_struct(struct_name, struct_fields)
            case "LetCmd":
                # Typecheck expression and update node
                # Update environment with (lvalue, node) mapping
                if type(node.lvalue) is ArrayLvalue:
                    expr_type = type_of(node.expr, env)
                    if type(expr_type) is not ArrayResolvedType:
                        raise Exception(f"Type mismatch for Lvalue in LetCmd at {node.start}")
                    if len(node.lvalue.variable_list) != expr_type.rank:
                        raise Exception(f"Rank mismatch for Lvalue in LetCmd at {node.start}")
                    if env.has(node.lvalue.variable):
                        raise Exception(f"Variable already defined in LetCmd at {node.start}")
                    for var in node.lvalue.variable_list:
                        try:
                            env.add_var(var, IntResolvedType())
                        except:
                            raise Exception(f"Length variable already defined in LetCmd at {node.start}")
                    env.add_var(node.lvalue.variable, expr_type)
                else:
                    expr_type = type_of(node.expr, env)
                    node.expr.type = expr_type
                    env.add_var(node.lvalue.variable, expr_type)
            case "ReadCmd":
                # Update environment with (argument, rgba struct) mapping
                if type(node.lvalue) is ArrayLvalue:
                    if len(node.lvalue.variable_list) != 2:
                        raise Exception(f"Invalid rank for image at ReadCmd: {node.start}")
                    else:
                        env.add_var(node.lvalue.variable, ArrayResolvedType(2, StructResolvedType("rgba")))
                        env.add_var(node.lvalue.variable_list[0], IntResolvedType())
                        env.add_var(node.lvalue.variable_list[1], IntResolvedType())
                elif type(node.lvalue) is VariableLvalue:
                    env.add_var(node.lvalue.variable, ArrayResolvedType(2, StructResolvedType("rgba")))
            case "WriteCmd":
                if type_of(node.expr, env) != ArrayResolvedType(2, StructResolvedType("rgba")):
                    raise Exception(f"Trying to write image to non-image type at: {node.start}")
            case "AssertCmd":
                node.expr.type = type_of(node.expr, env)
                if node.expr.type != BoolResolvedType():
                    raise Exception(f"Non-boolean asser condition at {node.start}")
            case "PrintCmd":
                pass #we already know the rest is a string
            case "TimeCmd":
                typecheck_cmd(node.cmd, env)
            case "FnCmd":
                child = Environment(env)
                resolved_bindings = []
                for binding in node.binding_list:
                    resolved_binding = get_resolved_type(binding.type, env)
                    if type(binding.lvalue) is ArrayLvalue:
                        if type(resolved_binding) is not ArrayResolvedType:
                            raise Exception(f"Lvalue and Type mismatch in binding at index: {node.start}")
                        elif len(binding.lvalue.variable_list) != resolved_binding.rank:
                            raise Exception(f"argument number mismatch for binding and resolved binding at: {node.start}")
                        for var in binding.lvalue.variable_list:
                            try:
                                child.add_var(var, IntResolvedType())
                            except:
                                raise Exception(f"variable already defined in function definition at {node.start}")
                    child.add_var(binding.lvalue.variable, resolved_binding) 
                    resolved_bindings.append(get_resolved_type(binding.type, env))
                function_ret = get_resolved_type(node.type, child) #pass in child or env?
                env.add_function(node.variable, FunctionInfo(function_ret, resolved_bindings, child))
                typecheck_stmt(node.stmt_list, child, function_ret)
            case _:
                raise Exception(f"ASTNode of type {type(node).__name__}; invalid for HW6 at {node.start}")

def typecheck(nodes):
    env = prepopulate_env()

    for node in nodes:
        typecheck_cmd(node, env)
    return env

def typecheck_stmt(stmts, env, ret_type):
    has_ret = False
    for stmt in stmts:
        match(type(stmt).__name__):
            case "LetStmt":
                if type(stmt.lvalue) is ArrayLvalue:
                    expr_type = type_of(stmt.expr, env)
                    if type(expr_type) is not ArrayResolvedType:
                        raise Exception(f"Type mismatch for Lvalue in LetCmd at {stmt.start}")
                    if len(stmt.lvalue.variable_list) != expr_type.rank:
                        raise Exception(f"Rank mismatch for Lvalue in LetCmd at {stmt.start}")
                    if env.has(stmt.lvalue.variable):
                        raise Exception(f"Variable already defined in LetCmd at {stmt.start}")
                    for var in stmt.lvalue.variable_list:
                        try:
                            env.add_var(var, IntResolvedType())
                        except:
                            raise Exception(f"Length variable already defined in LetCmd at {stmt.start}")
                    env.add_var(stmt.lvalue.variable, expr_type)
                else:
                    expr_type = type_of(stmt.expr, env)
                    stmt.expr.type = expr_type
                    env.add_var(stmt.lvalue.variable, expr_type)
            case "AssertStmt":
                stmt.expr.type = type_of(stmt.expr, env)
                if stmt.expr.type != BoolResolvedType():
                    raise Exception(f"Non-boolean assert condition at {stmt.start}")
            case "ReturnStmt":
                has_ret = True
                if ret_type is VoidResolvedType:
                    raise Exception(f"Void function has a return statement at index: {stmt.start}")
                if type_of(stmt.expr, env) != ret_type:
                    raise Exception(f"Function return type does not match declared type at index: {stmt.start}")
    if has_ret is False and ret_type != VoidResolvedType():
        raise Exception(f"Function needs but does not have a return type at index: {stmt.start}")
    return env