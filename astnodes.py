from dataclasses import dataclass
from abc import ABC, abstractmethod
from tokens import *
from enum import Enum

@dataclass
class ASTNode:
    def __init__(self, start: int):
        self.start = start

@dataclass
class ResolvedType:
    def __eq__(self, other):
        #print(type(self))
        #print(type(other))
        if type(self) is type(other): #type(self) defaults to subclass? 
            if type(self) is ArrayResolvedType:
                return self.rank == other.rank and self.type == other.type
            elif type(self) is StructResolvedType:
                return self.name == other.name
            return True
        return False
    def toString(self):
        if type(self) is NoneResolvedType:
            return ""
        elif type(self) is ArrayResolvedType:
            return f" ({type(self).__name__.replace("Resolved","")}{self.type.toString()} {self.rank})"
        elif type(self) is StructResolvedType:
            return f" ({type(self).__name__.replace("Resolved","")} {self.name})"
        else:
            return f" ({type(self).__name__.replace("Resolved","")})"

class IntResolvedType(ResolvedType):
    pass

class FloatResolvedType(ResolvedType):
    pass

class BoolResolvedType(ResolvedType):
    pass

class ArrayResolvedType(ResolvedType):
    def __init__(self, rank: int, type: ResolvedType):
        self.rank = rank
        self.type = type

class StructResolvedType(ResolvedType):
    def __init__(self, name: str):
        self.name = name

class NoneResolvedType(ResolvedType):
    pass

class VoidResolvedType(ResolvedType):
    pass

################################################################################
# Types
################################################################################

class Type(ASTNode):
    @abstractmethod
    def toString(self):
        pass

class IntType(Type):
    def toString(self):
        return (f"(IntType)")

class BoolType(Type):
    def toString(self):
        return (f"(BoolType)")

class FloatType(Type):
    def toString(self):
        return (f"(FloatType)")

class ArrayType(Type):
    def __init__(self, start: int, type: Type, dimension: int):
        self.start = start
        self.type = type
        self.dimension = dimension
    def toString(self):
        return (f"(ArrayType {self.type.toString()} {self.dimension})")

class StructType(Type):
    def __init__(self, start: int, variable: str):
        self.start = start
        self.variable = variable
    def toString(self):
       return (f"(StructType {self.variable})")

class VoidType(Type):
    def toString(self):
        return (f"(VoidType)")

################################################################################
# Lvalues
################################################################################

class Lvalue(ASTNode):
    @abstractmethod
    def toString():
        pass

class VariableLvalue(Lvalue):
    def __init__(self, start: int, variable: str):
        self.start = start
        self.variable = variable
    def toString(self):
        #"if it is a string field, print with quotation marks" - hw3
        return f"(VarLValue {self.variable})"

class ArrayLvalue(Lvalue):
    def __init__(self, start: int, variable: str, variable_list: list[str]):
        self.start = start
        self.variable = variable
        self.variable_list = variable_list
    def toString(self):
        ret_str = f"(ArrayLValue {self.variable}"
        for var in self.variable_list:
            ret_str += f" {var}"
        ret_str += ")"
        return ret_str


################################################################################
# Bindings
################################################################################

# no S-expression for this
class Binding(ASTNode):
    def __init__(self, start: int, lvalue: Lvalue, type: Type):
        self.start = start
        self.lvalue = lvalue
        self.type = type
    def toString(self):
        return (f"{self.lvalue.toString()} {self.type.toString()}")

################################################################################
# Expressions
################################################################################

class Expr(ASTNode):
    type = NoneResolvedType()

class IntExpr(Expr):
    def __init__(self, start: int, i: int):
        self.start = start
        self.i = i
    def toString(self):
        return f"(IntExpr{self.type.toString()} {self.i})"

class FloatExpr(Expr):
    def __init__(self, start: int, f: float):
        self.start = start
        self.f = f
    def toString(self):
        return f"(FloatExpr{self.type.toString()} {int(self.f)})"

#TODO: add self.type.toString() after the name of the expression type in all toString methods for expr

class TrueExpr(Expr):
    def toString(self):
        return f"(TrueExpr{self.type.toString()})"

class FalseExpr(Expr):
    def toString(self):
        return f"(FalseExpr{self.type.toString()})"

class VariableExpr(Expr):
    def __init__(self, start: int, variable: str):
        self.start = start
        self.variable = variable
    def toString(self):
        return (F"(VarExpr{self.type.toString()} {self.variable})")

#WARNING: expr_list type change from list[int] to list[expr] in early HW6 development
class ArrayExpr(Expr):
    def __init__(self, start: int, expr_list: list[Expr]):
        self.start = start
        self.expr_list = expr_list

    def toString(self):
        out = f"(ArrayLiteralExpr{self.type.toString()}"
        for expr in self.expr_list:
            out += F" {expr.toString()}"
        out += ")"
        return out

class VoidExpr(Expr):
    def toString(self):
        return (f"(VoidExpr{self.type.toString()})")

class StructLiteralExpr(Expr):
    def __init__(self, start: int, variable: str, expr_list: list[Expr]):
        self.start = start
        self.variable = variable
        self.expr_list = expr_list
    def toString(self):
        ret_str = f"(StructLiteralExpr{self.type.toString()} {self.variable}" #may need quotes around variable? is str field
        for expr in self.expr_list:
            ret_str += f" {expr.toString()}"
        ret_str += ")"
        return ret_str

class DotExpr(Expr):
    def __init__(self, start: int, expr: Expr, variable: str):
        self.start = start
        self.expr = expr
        self.variable = variable
    def toString(self):
        return f"(DotExpr{self.type.toString()} {self.expr.toString()} {self.variable})"

class ArrayIndexExpr(Expr):
    def __init__(self, start: int, expr: Expr, expr_list: list[Expr]):
        self.start = start
        self.expr = expr
        self.expr_list = expr_list
    def toString(self):
        ret_str = f"(ArrayIndexExpr{self.type.toString()} {self.expr.toString()}"
        for e in self.expr_list:
            ret_str += f" {e.toString()}"
        ret_str += ")"
        return ret_str

class CallExpr(Expr):
    def __init__(self, start: int, variable: str, expr_list: list[Expr]):
        self.start = start
        self.variable = variable
        self.expr_list = expr_list
    def toString(self):
        ret_str = f"(CallExpr{self.type.toString()} {self.variable}"
        for expr in self.expr_list:
            ret_str += f" {expr.toString()}"
        ret_str += ")"
        return ret_str

class UnopExpr(Expr):
    def __init__(self, start: int, expr: Expr, op: OP):
        self.start = start
        self.expr = expr
        self.op = op
    def toString(self):
        return f"(UnopExpr{self.type.toString()} {self.op.text} {self.expr.toString()})"

class BinopExpr(Expr):
    def __init__(self, start: int, l_expr: Expr, r_expr: Expr, op: OP):
        self.start = start
        self.l_expr = l_expr
        self.r_expr = r_expr
        self.op = op
    def toString(self):
        return f"(BinopExpr{self.type.toString()} {self.l_expr.toString()} {self.op.text} {self.r_expr.toString()})"
    
class IfExpr(Expr):
    def __init__(self, start: int, cndn_expr: Expr, then_expr: Expr, else_expr: Expr):
        self.start = start
        self.cndn_expr = cndn_expr
        self.then_expr = then_expr
        self.else_expr = else_expr
    def toString(self):
        return f"(IfExpr{self.type.toString()} {self.cndn_expr.toString()} {self.then_expr.toString()} {self.else_expr.toString()})"

class ArrayLoopExpr(Expr):
    def __init__(self, start: int, list: list[tuple[str, Expr]], expr: Expr):
        self.start = start
        self.list = list
        self.expr = expr
    def toString(self):
        ret_str = f"(ArrayLoopExpr{self.type.toString()}"
        for pair in self.list:
            ret_str += f"{pair[0]} {pair[1].toString()} "
        ret_str += self.expr.toString()
        ret_str += ")"
        return ret_str

class SumLoopExpr(Expr):
    def __init__(self, start: int, list: list[tuple[str, Expr]], expr: Expr):
        self.start = start
        self.list = list
        self.expr = expr
    def toString(self):
        ret_str = f"(SumLoopExpr{self.type.toString()}"
        for pair in self.list:
            ret_str += f"{pair[0]} {pair[1].toString()} "
        ret_str += self.expr.toString()
        ret_str += ")"
        return ret_str

################################################################################
# Statements
################################################################################  

class Stmt(ASTNode):
    pass

class LetStmt(Stmt):
    def __init__(self, start: int, lvalue: Lvalue, expr: Expr):
        self.start = start
        self.lvalue = lvalue
        self.expr = expr
    def toString(self):
        return f"(LetStmt {self.lvalue.toString()} {self.expr.toString()})"

class AssertStmt(Stmt):
    def __init__(self, start: int, expr: Expr, string: str):
        self.start = start
        self.expr = expr
        self.string = string
    def toString(self):
        return f"(AssertStmt {self.expr.toString()} {self.string})"

class ReturnStmt(Stmt):
    def __init__(self, start: int, expr: Expr):
        self.start = start
        self.expr = expr
    def toString(self):
        return f"(ReturnStmt {self.expr.toString()})"

################################################################################
# Commands 
################################################################################

class Cmd(ASTNode):
    pass

class ReadCmd(Cmd):
    def __init__(self, start: int, string: str, lvalue: Lvalue):
        self.start = start
        self.string = string
        self.lvalue = lvalue
    def toString(self):
        return (f"(ReadCmd {self.string} {self.lvalue.toString()})")

class WriteCmd(Cmd):
    def __init__(self, start: int, expr: Expr, string: str):
        self.start = start
        self.expr = expr
        self.string = string
    def toString(self):
        return (f"(WriteCmd {self.expr.toString()} {self.string})")

class LetCmd(Cmd):
    def __init__(self, start: int, lvalue: Lvalue, expr: Expr):
        self.start = start
        self.lvalue = lvalue
        self.expr = expr
    def toString(self):
        return (f"(LetCmd {self.lvalue.toString()} {self.expr.toString()})")

class AssertCmd(Cmd):
    def __init__(self, start: int, expr: Expr, string: str):
        self.start = start
        self.expr = expr
        self.string = string
    def toString(self):
        return (f"(AssertCmd {self.expr.toString()} {self.string})")

class PrintCmd(Cmd):
    def __init__(self, start: int, string: str):
        self.start = start
        self.string = string
    def toString(self):
        return (f"(PrintCmd {self.string})")

class ShowCmd(Cmd):
    def __init__(self, start: int, expr: Expr):
        self.start = start
        self.expr = expr
    def toString(self):
        return (f"(ShowCmd {self.expr.toString()})")

class TimeCmd(Cmd):
    def __init__(self, start: int, cmd: Cmd):
        self.start = start
        self.cmd = cmd
    def toString(self):
        return (f"(TimeCmd {self.cmd.toString()})")

class FnCmd(Cmd):
    def __init__(self, start: int, variable: str, binding_list: list[Binding], type: Type, stmt_list: list[Stmt]):
        self.start = start
        self.variable = variable
        self.binding_list = binding_list
        self.type = type
        self.stmt_list = stmt_list
    def toString(self):
        ret_str = f"(FnCmd {self.variable} (("
        if len(self.binding_list) > 0:
            ret_str += f"{self.binding_list[0].toString()}"
            for i in range(1, len(self.binding_list)):
                ret_str += f" {self.binding_list[i].toString()}"
        ret_str += f")) {self.type.toString()}"
        for stmt in self.stmt_list:
            ret_str += f" {stmt.toString()}"
        ret_str += ")"
        return ret_str

class StructCmd(Cmd):
    def __init__(self, start: int, variable: str, field_list: list[tuple[str, Type]]):
        self.start = start
        self.variable = variable
        self.field_list = field_list
    def toString(self):
        ret_str = f"(StructCmd {self.variable}"
        for field in self.field_list:
            # ret_str += f" {field.toString()}"'
            ret_str += f" {field[0]} {field[1].toString()}"
        ret_str += ")"
        return ret_str