from astnodes import *

def find_topological_order(arr_loop_expr):
    nodes = arr_loop_expr.tc_nodes
    edges = arr_loop_expr.tc_edges
    top_order = []
    while len(nodes) > 0 and len(edges) > 0:
        for node in nodes:
            is_target = False
            for edge in edges:
                if edge[1] == node:
                    is_target = True
            if not is_target:
                top_order.append(node)
                to_remove = []
                for edge in edges:
                    if edge[0] == node:
                        to_remove.append(edge) 
                for rem_edge in to_remove:
                    edges.remove(rem_edge)    
                nodes.remove(node)
                break
    if len(nodes) > 0:
        top_order.extend(nodes)
    return top_order

def find_nodes(expr, tc_edges, tc_nodes):
    match(type(expr).__name__):
        case "ArrayLoopExpr":
            for i in range(0, len(expr.list)):
                tc_nodes.append(expr.list[i][0])
                for j in range(i+1, len(expr.list)):
                    edge = (expr.list[i][0], expr.list[j][0])
                    if edge not in tc_edges:
                        tc_edges.append(edge)
            tc_edges, tc_nodes = find_nodes(expr.expr, tc_edges, tc_nodes)
        case "SumLoopExpr":
            for i in range(0, len(expr.list)):
                tc_nodes.append(expr.list[i][0])
                if type(expr.expr.type).__name__ == "FloatResolvedType":
                    for j in range(i+1, len(expr.list)):
                        edge = (expr.list[i][0], expr.list[j][0])
                        if edge not in tc_edges:
                            tc_edges.append(edge)
            tc_edges, tc_nodes = find_nodes(expr.expr, tc_edges, tc_nodes)
        case "BinopExpr":
            tc_edges, tc_nodes = find_nodes(expr.l_expr, tc_edges, tc_nodes)
            tc_edges, tc_nodes = find_nodes(expr.r_expr, tc_edges, tc_nodes)
        case "ArrayIndexExpr":
            check_nodes = []
            for exp in expr.expr_list:
                if type(exp).__name__ == "VariableExpr" and exp.variable in tc_nodes:
                    check_nodes.append(exp)

            for i in range(0, len(check_nodes)):
                for j in range(i+1, len(check_nodes)):
                    edge = (check_nodes[i].variable, check_nodes[j].variable)
                    if edge not in tc_edges:
                        tc_edges.append(edge)
    return tc_edges, tc_nodes

def is_tc(expr, optim_level):
    if not optim_level:
        expr.is_tc = False
        return False
    match(type(expr).__name__):
        case "ArrayLoopExpr":
            expr_is_tc = True
            tc_nodes = []
            tc_edges = []
            if expr_is_tc:
                expr_is_tc = is_tc_sum(expr.expr)
            expr.is_tc = expr_is_tc
            if not expr_is_tc:
                is_tc(expr.expr, optim_level)
            if expr_is_tc:
                tc_edges, tc_nodes = find_nodes(expr, [], [])
            expr.tc_edges = tc_edges
            expr.tc_nodes = tc_nodes
            if expr_is_tc:
                top_list = find_topological_order(expr)
                expr.top_list = top_list
            return expr_is_tc
        case "IfExpr":
            is_tc(expr.then_expr, optim_level)
            is_tc(expr.else_expr, optim_level)
        case _: #other cases where the current expr cannot be a tc
            if hasattr(expr, "expr_list"):
                for new_expr in expr.expr_list:
                    is_tc(new_expr, optim_level)
            if hasattr(expr, "expr"):
                is_tc(expr.expr, optim_level)
    return False

def is_tc_sum(expr):
    if type(expr).__name__ == "SumLoopExpr":
        expr_is_sum =  True
        if expr_is_sum:
            expr_is_sum = is_tc_body(expr.expr)
        expr.is_tc_sum = expr_is_sum
        return expr_is_sum
    return False

def is_tc_body(expr):
    if type(expr).__name__ == "BinopExpr":
        expr_is_body = is_tc_body(expr.l_expr) and is_tc_body(expr.r_expr)
        expr.is_tc_body = expr_is_body
        return expr_is_body
    if type(expr).__name__ == "ArrayIndexExpr":
        expr_is_body = is_tc_primitive(expr.expr)
        if expr_is_body:
            for exp in expr.expr_list:
                if not is_tc_primitive(exp):
                    expr_is_body = False
        expr.is_tc_body = expr_is_body
        return expr_is_body
    else:
        expr_is_primitive = is_tc_primitive(expr)
        expr.is_tc_body = expr_is_primitive
        return expr_is_primitive

def is_tc_primitive(expr):
    is_prim = type(expr).__name__ == "IntExpr" or type(expr).__name__ == "FloatExpr" or type(expr).__name__ == "VariableExpr"
    expr.is_tc_primitive = is_prim
    return is_prim

def tensorCmd(node, optim_level: bool):
    match(type(node).__name__):
        case "ShowCmd":
            is_tc(node.expr, optim_level)
        case "StructCmd":
            pass
        case "LetCmd" | "LetStmt":
            is_tc(node.expr, optim_level)
        case "ReadCmd":
            pass
        case "WriteCmd":
            is_tc(node.expr, optim_level)
        case "AssertCmd" | "AssertStmt":
            is_tc(node.expr, optim_level)
        case "TimeCmd":
            tensorCmd(node.cmd, optim_level)
        case "FnCmd":
            for stmt in node.stmt_list:
                tensorCmd(stmt, optim_level)
        case "ReturnStmt":
            is_tc(node.expr, optim_level)
        case "PrintCmd":
            pass
        case _:
            raise Exception(f"ASTNode of type {type(node).__name__} not recognized")
    return

def tensorContraction(nodes, env , optim_bool: bool):
    for node in nodes:
        tensorCmd(node, optim_bool)
    return nodes