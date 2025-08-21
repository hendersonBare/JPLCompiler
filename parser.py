from tokens import *
from astnodes import *
import math
from enum import Enum

################################################################################
# Helper Functions
################################################################################

class SequenceType(Enum):
    EXPR = 1
    VARIABLE = 2
    BINDING = 3
    STATEMENT = 4
    STRUCT_FIELD = 5
    LOOP = 6

def peek_token(tokens, index):
    return tokens[index]

def get_start(tokens, index):
    return tokens[index].start

def expect_token(tokens, index, expected):
    given = tokens[index]
    if type(given) == expected:
        return (given.text, index + 1)
    else:
        raise Exception("UNEXPECTED TOKEN TYPE", index, given.text, type(given), expected)

def parse_sequence(tokens, start_index, seq_type, delimiter, terminator):
    list = []
    index = start_index
    next_token = tokens[index]
    
    # Check for termination outside the loop first no matter what; this handles empty sequences
    if type(next_token) == terminator:
            return (list, index + 1)
    while True:
        # Check for termination after trailing newline in the case of struct fields
        if (seq_type == SequenceType.STRUCT_FIELD or seq_type == SequenceType.STATEMENT) and type(next_token) == terminator:
            #print(list)
            return (list, index + 1)
        else:
            match seq_type:
                case SequenceType.EXPR:
                    (item, index) = parse_Expr(tokens, index)
                case SequenceType.VARIABLE:
                    item = next_token.text
                    index += 1
                case SequenceType.BINDING:
                    (item, index) = parse_Binding(tokens, index)
                case SequenceType.STATEMENT:
                    (item, index) = parse_Stmt(tokens, index)
                case SequenceType.STRUCT_FIELD:
                    (item1, index) = expect_token(tokens, index, VARIABLE)
                    (x, index) = expect_token(tokens, index, COLON)
                    (item2, index) = parse_Type(tokens, index)
                    item = (item1, item2)
                case SequenceType.LOOP:
                    (item1, index) = expect_token(tokens, index, VARIABLE)
                    (x, index) = expect_token(tokens, index, COLON)
                    (item2, index) = parse_Expr(tokens, index)
                    item = (item1, item2)
            
            list.append(item)
            next_token = tokens[index]
            # Check for termination without final delimiter in all cases except struct fields
            if not (seq_type == SequenceType.STRUCT_FIELD or seq_type == SequenceType.STATEMENT) and type(next_token) == terminator:
                return (list, index + 1)
            else:
                (x, index) = expect_token(tokens, index, delimiter)
                next_token = tokens[index]

    # this is intended to be a versatile extension of this algorithm; I'll leave it here for reference for now
    #
    # while True:
    #     if type(next_token) == RSQUARE:
    #         return (ArrayExpr(tokens[start_index].start, expr_list), index + 1)
    #     else:
    #         (expr, index) = parse_ExprLiteral(tokens, index)
    #         expr_list.append(expr)
    #         next_token = tokens[index]
    #         if type(next_token) == RSQUARE:
    #             return (ArrayExpr(tokens[start_index].start, expr_list), index + 1)
    #         else:
    #             (x, index) = expect_token(tokens, index, COMMA)
    #             next_token = tokens[index]

################################################################################
# Parse Types
################################################################################

def parse_IntType(tokens, start_index):
    return (IntType(tokens[start_index].start), start_index + 1)

def parse_BoolType(tokens, start_index):
    return (BoolType(tokens[start_index].start), start_index + 1)

def parse_FloatType(tokens, start_index):
    return (FloatType(tokens[start_index].start), start_index + 1)

def parse_ArrayType(tokens, start_index, head):
    index = start_index + 1
    next_token = tokens[index]
    dimension = 1

    while type(next_token) != RSQUARE:
        (x, index) = expect_token(tokens, index, COMMA)
        dimension += 1
        next_token = tokens[index]

    return (ArrayType(tokens[start_index].start, head, dimension), index + 1)

def parse_StructType(tokens, start_index):
    return (StructType(tokens[start_index].start, tokens[start_index].text), start_index + 1)

def parse_VoidType(tokens, start_index):
    return (VoidType(tokens[start_index].start), start_index + 1)

def parse_typeCont(tokens, start_index, head):
    next_token = tokens[start_index]

    match type(next_token).__name__:
        case 'LSQUARE':
            (new_head, index) = parse_ArrayType(tokens, start_index, head)
        case _:
            return (head, start_index)
        
    return parse_typeCont(tokens, index, new_head)

def parse_Type(tokens, start_index):
    next_token = tokens[start_index]

    match type(tokens[start_index]).__name__:
        case 'INT':
            (head, index) = parse_IntType(tokens, start_index)
        case 'BOOL':
            (head, index) = parse_BoolType(tokens, start_index)
        case 'FLOAT':
            (head, index) = parse_FloatType(tokens, start_index)
        case 'VARIABLE':
            (head, index) = parse_StructType(tokens, start_index)
        case 'VOID':
            (head, index) = parse_VoidType(tokens, start_index)
        case _:
            raise Exception("UNEXPECTED TOKEN STARTING EXPRESSION")

    return parse_typeCont(tokens, index, head)

################################################################################
# Parse Lvalues
################################################################################

def parse_VariableLvalue(tokens, start_index):
    return (VariableLvalue(tokens[start_index].start, tokens[start_index].text), start_index + 1)

def parse_ArrayLvalue(tokens, start_index):
    (x, index) = expect_token(tokens, start_index + 1, LSQUARE)
    (list, index) = parse_sequence(tokens, index, SequenceType.VARIABLE, COMMA, RSQUARE)
    return (ArrayLvalue(tokens[start_index].start, tokens[start_index].text, list), index)

def parse_Lvalue(tokens, start_index):
    next_token = tokens[start_index]

    match type(tokens[start_index]).__name__:
        case "VARIABLE":
            if type(tokens[start_index + 1]) == LSQUARE:
                return parse_ArrayLvalue(tokens, start_index)
            else:
                return parse_VariableLvalue(tokens, start_index)
        case _:
            raise Exception("UNEXPECTED TOKEN STARTING LVALUE")

################################################################################
# Parse Bindings
################################################################################

# no S-expression for this
def parse_Binding(tokens, start_index):
    (lvalue, index) = parse_Lvalue(tokens, start_index)
    (x, index) = expect_token(tokens, index, COLON)
    (type, index) = parse_Type(tokens, index)

    return (Binding(tokens[start_index].start, lvalue, type), index)

################################################################################
# Parse Expressions
################################################################################

#helper method to check if the next tokens start with if, array, or sum
def isExprPrefx(tokens, start_index):
    #should evaluate to true if the start token matches conditional, sum, or array
    return (type(peek_token(tokens, start_index)) is IF or
        type(peek_token(tokens, start_index)) is ARRAY or
        type(peek_token(tokens, start_index)) is SUM)

    
'''
expr        :   <expr_prefix>
            |   <expr_bool>
'''
def parse_Expr(tokens, start_index):
    if isExprPrefx(tokens, start_index):
        return parse_ExprPrefix(tokens, start_index)
    else:
        return parse_ExprBool(tokens, start_index)

'''
expr_prefix :   if <expr> then <expr> else <expr>
            |   array [ <variable> : <expr> , ... ] <expr>
            |   sum [ <variable> : <expr> , ... ] <expr>
'''
def parse_ExprPrefix(tokens, start_index):
    start_token = peek_token(tokens, start_index)
    match type(start_token).__name__:
        case 'IF':
            return parse_IfExpr(tokens, start_index)
        case 'ARRAY':
            return parse_ArrayLoopExpr(tokens, start_index) #no incrementing done
        case 'SUM':
            return parse_SumLoopExpr(tokens, start_index)
        
def parse_IfExpr(tokens, start_index):
    (x, index) = expect_token(tokens, start_index, IF)
    (cndn_expr, index) = parse_Expr(tokens, index)
    (x, index) = expect_token(tokens, index, THEN)
    (then_expr, index) = parse_Expr(tokens, index)
    (x, index) = expect_token(tokens, index, ELSE)
    (else_expr, index) = parse_Expr(tokens, index)
    return (IfExpr(tokens[start_index].start, cndn_expr, then_expr, else_expr), index)

def parse_ArrayLoopExpr(tokens, start_index):
    (x, index) = expect_token(tokens, start_index, ARRAY)
    (x, index) = expect_token(tokens, index, LSQUARE)
    (list, index) = parse_sequence(tokens, index, SequenceType.LOOP, COMMA, RSQUARE)
    (expr, index) = parse_Expr(tokens, index)
    return (ArrayLoopExpr(tokens[start_index].start, list, expr), index)

def parse_SumLoopExpr(tokens, start_index):
    (x, index) = expect_token(tokens, start_index, SUM)
    (x, index) = expect_token(tokens, index, LSQUARE)
    (list, index) = parse_sequence(tokens, index, SequenceType.LOOP, COMMA, RSQUARE)
    (expr, index) = parse_Expr(tokens, index)
    return (SumLoopExpr(tokens[start_index].start, list, expr), index)

'''
expr_bool   :   <expr_comp> <expr_bool'>
'''
def parse_ExprBool(tokens, start_index):
    (comp, index) = parse_ExprComp(tokens, start_index)
    return parse_ExprBoolCont(tokens, index, comp)

'''
expr_bool'  :   && <expr_comp> <expr_bool'>
            |   || <expr_comp> <expr_bool'>
            |   && <expr_prefix> <expr_bool'>
            |   || <expr_prefix> <expr_bool'>
            |   (empty)
'''
def parse_ExprBoolCont(tokens, start_index, expr_head): #expr_head needed for all left recursive rules?
    start_token = peek_token(tokens, start_index) 
    if type(start_token) is OP:
        start_text = start_token.text
        next_index = start_index+1
        if start_text == "&&" or start_text == "||":
            if isExprPrefx(tokens, next_index):
                (head, index) = parse_ExprPrefix(tokens, next_index)
            else:
                (head, index) = parse_ExprComp(tokens, next_index)
            new_head = BinopExpr(tokens[start_index].start, expr_head, head, start_token)
            return parse_ExprBoolCont(tokens, index, new_head)
    return (expr_head, start_index)
    
'''
expr_comp   :   <expr_add> <expr_comp'>
'''
def parse_ExprComp(tokens, start_index):
    (add, index) = parse_ExprAdd(tokens, start_index)
    return parse_ExprCompCont(tokens, index, add)

'''
expr_comp'  :   < <expr_add> <expr_comp'>
            |   > <expr_add> <expr_comp'>
            |   <= <expr_add> <expr_comp'>
            |   >= <expr_add> <expr_comp'>
            |   == <expr_add> <expr_comp'>
            |   != <expr_add> <expr_comp'>
            |   < <expr_prefix> <expr_comp'>
            |   > <expr_prefix> <expr_comp'>
            |   <= <expr_prefix> <expr_comp'>
            |   >= <expr_prefix> <expr_comp'>
            |   == <expr_prefix> <expr_comp'>
            |   != <expr_prefix> <expr_comp'>
            |   (empty)
'''
def parse_ExprCompCont(tokens, start_index, expr_head):
    start_token = peek_token(tokens, start_index) 
    if type(start_token) is OP:
        start_text, next_index = start_token.text, start_index+1
        if (start_text == "<" or start_text == ">" or start_text == "<=" or start_text == ">=" 
            or start_text == "==" or start_text == "!="): 
            if isExprPrefx(tokens, next_index):
                (head, index) = parse_ExprPrefix(tokens, next_index)
            else:
                (head, index) = parse_ExprAdd(tokens, next_index)
            new_head = BinopExpr(peek_token(tokens, start_index).start, expr_head, head, start_token)
            return parse_ExprCompCont(tokens, index, new_head)
    return expr_head, start_index

'''
expr_add    :   <expr_mult> <expr_add'>
'''
def parse_ExprAdd(tokens, start_index):
    (mult, index) = parse_ExprMult(tokens, start_index)
    return parse_ExprAddCont(tokens, index, mult)

'''
expr_add'   :   + <expr_mult> <expr_add'>
            |   - <expr_mult> <expr_add'>   
            |   + <expr_prefix> <expr_add'>
            |   - <expr_prefix> <expr_add'>  
            |   (empty)
'''
def parse_ExprAddCont(tokens, start_index, expr_head):
    start_token = peek_token(tokens, start_index) 
    if type(start_token) is OP:
        start_text = start_token.text
        next_index = start_index+1
        if start_text == "+" or start_text == "-":
            if isExprPrefx(tokens, next_index):
                (head, index) = parse_ExprPrefix(tokens, next_index)
            else:
                (head, index) = parse_ExprMult(tokens, next_index)
            new_head = BinopExpr(tokens[start_index].start, expr_head, head, start_token)
            return parse_ExprAddCont(tokens, index, new_head)
    return (expr_head, start_index)
'''
expr_mult   :   <expr_unop> <expr_mult'>
'''
def parse_ExprMult(tokens, start_index):
    (unop, index) = parse_ExprUnop(tokens, start_index)
    return parse_ExprMultCont(tokens, index, unop)

'''
expr_mult'  :   * <expr_unop> <expr_mult'>
            |   / <expr_unop> <expr_mult'>
            |   % <expr_unop> <expr_mult'>
            |   * <expr_prefix> <expr_mult'>
            |   / <expr_prefix> <expr_mult'>
            |   % <expr_prefix> <expr_mult'>
            |   (empty)
'''
def parse_ExprMultCont(tokens, start_index, expr_head):
    start_token = peek_token(tokens, start_index) 
    if type(start_token) is OP:
        start_text = start_token.text
        next_index = start_index+1
        if start_text == "*" or start_text == "/" or start_text == '%':
            if isExprPrefx(tokens, next_index):
                (head, index) = parse_ExprPrefix(tokens, next_index)
            else:
                (head, index) = parse_ExprUnop(tokens, next_index)
            new_head = BinopExpr(peek_token(tokens, start_index).start, expr_head, head, start_token)
            return parse_ExprMultCont(tokens, index, new_head)
    return (expr_head, start_index)

'''
expr_unop   :   ! <expr_unop>
            |   - <expr_unop>
            |   ! <expr_prefix>
            |   - <expr_prefix>
            |   <expr_literal>
'''
def parse_ExprUnop(tokens, start_index):
    start_token = peek_token(tokens, start_index) 
    if type(start_token) is OP:
        start_text = start_token.text
        next_index = start_index+1
        if start_text == "!" or start_text == "-":
            if isExprPrefx(tokens, next_index):
                (head, index) = parse_ExprPrefix(tokens, next_index)
            else:
                (head, index) = parse_ExprUnop(tokens, next_index)
            return (UnopExpr(peek_token(tokens, start_index).start, head, start_token), index)
    return parse_ExprLiteral(tokens, start_index)

def parse_IntExpr(tokens, start_index):
    i = int(tokens[start_index].text)
    if i >= 2 << 63 - 1 or i <= -2 << 63:
        raise Exception("INTEGER OVERFLOW")
    return (IntExpr(tokens[start_index].start, i), start_index + 1)

def parse_FloatExpr(tokens, start_index):
    f = float(tokens[start_index].text)
    if math.isnan(f) or math.isinf(f):
        raise Exception("BAD FLOAT")
    return (FloatExpr(tokens[start_index].start, f), start_index + 1)

def parse_TrueExpr(tokens, start_index):
    return (TrueExpr(tokens[start_index].start), start_index + 1)

def parse_FalseExpr(tokens, start_index):
    return (FalseExpr(tokens[start_index].start), start_index + 1)

def parse_VariableExpr(tokens, start_index):
    return (VariableExpr(tokens[start_index].start, tokens[start_index].text), start_index + 1)

def parse_ArrayExpr(tokens, start_index):
    (list, index) = parse_sequence(tokens, start_index + 1, SequenceType.EXPR, COMMA, RSQUARE)
    return (ArrayExpr(tokens[start_index].start, list), index)

def parse_VoidExpr(tokens, start_index):
    return (VoidExpr(tokens[start_index].start), start_index + 1)

def parse_StructExpr(tokens, start_index):
    (list, index) = parse_sequence(tokens, start_index + 2, SequenceType.EXPR, COMMA, RCURLY)
    return (StructLiteralExpr(tokens[start_index].start, tokens[start_index].text, list), index)

# continuation after left recursion
def parse_DotExpr(tokens, start_index, expr_head):
    (variable, index) = expect_token(tokens, start_index + 1, VARIABLE)
    return parse_ExprLiteralCont(tokens, index, DotExpr(tokens[start_index].start, expr_head, variable))

# continuation after left recurision
def parse_ArrayIndexExpr(tokens, start_index, expr_head):
    (list, index) = parse_sequence(tokens, start_index + 1, SequenceType.EXPR, COMMA, RSQUARE)
    return parse_ExprLiteralCont(tokens, index, ArrayIndexExpr(tokens[start_index].start, expr_head, list))

# continuation after variable
def parse_CallExpr(tokens, start_index):
    (list, index) = parse_sequence(tokens, start_index + 2, SequenceType.EXPR, COMMA, RPAREN)
    return (CallExpr(tokens[start_index].start, tokens[start_index].text, list), index)

def parse_ExprLiteralCont(tokens, start_index, expr_head):
    next_token = tokens[start_index]

    match type(next_token).__name__:
        case 'DOT':
            (new_head, index) = parse_DotExpr(tokens, start_index, expr_head)
        case 'LSQUARE':
            (new_head, index) = parse_ArrayIndexExpr(tokens, start_index, expr_head)
        case _:
            return (expr_head, start_index)

    return parse_ExprLiteralCont(tokens, index, new_head)

def parse_ExprLiteral(tokens, start_index):
    next_token = tokens[start_index]

    match type(next_token).__name__:
        case 'INTVAL':
            (head, index) = parse_IntExpr(tokens, start_index)
        case 'FLOATVAL':
            (head, index) = parse_FloatExpr(tokens, start_index)
        case 'TRUE':
            (head, index) = parse_TrueExpr(tokens, start_index)
        case 'FALSE':
            (head, index) = parse_FalseExpr(tokens, start_index)
        case 'VARIABLE':
            if type(peek_token(tokens, start_index + 1)) == LCURLY:
                (head, index) = parse_StructExpr(tokens, start_index)
            elif type(peek_token(tokens, start_index + 1)) == LPAREN:
                (head, index) = parse_CallExpr(tokens, start_index)
            else:
                (head, index) = parse_VariableExpr(tokens, start_index)
        case 'LSQUARE':
            (head, index) = parse_ArrayExpr(tokens, start_index)
        case 'VOID':
            (head, index) = parse_VoidExpr(tokens, start_index)
        case 'LPAREN':
            (expr, index) = parse_Expr(tokens, start_index + 1)
            (x, index) = expect_token(tokens, index, RPAREN)
            (head, index) = (expr, index)
        case _:
            raise Exception("UNEXPECTED TOKEN STARTING EXPRESSION", type(next_token), start_index)
    
    return parse_ExprLiteralCont(tokens, index, head)

################################################################################
# Parse Statements
################################################################################ 

def parse_LetStmt(tokens, start_index):
    index = start_index + 1
    (lvalue, index) =   parse_Lvalue(tokens, index)           # Parse Lvalue field
    (x, index) =        expect_token(tokens, index, EQUALS)
    (expr, index) =     parse_Expr(tokens, index)             # Parse expression field

    return (LetStmt(tokens[start_index].start, lvalue, expr), index)

def parse_AssertStmt(tokens, start_index):
    index = start_index + 1
    (expr, index) =     parse_Expr(tokens, index)             # Parse expression field
    (x, index) =        expect_token(tokens, index, COMMA)
    (string, index) =   expect_token(tokens, index, STRING)   # Extract string field

    return (AssertStmt(tokens[start_index].start, expr, string), index)

def parse_ReturnStmt(tokens, start_index):
    index = start_index + 1
    (expr, index) =     parse_Expr(tokens, index)             # Parse expression field

    return (ReturnStmt(tokens[start_index].start, expr), index)

def parse_Stmt(tokens, start_index):
    next_token = tokens[start_index]

    match type(next_token).__name__:
        case 'LET':
            return parse_LetStmt(tokens, start_index)
        case 'ASSERT':
            return parse_AssertStmt(tokens, start_index)
        case 'RETURN':
            return parse_ReturnStmt(tokens, start_index)
        case _:
            raise Exception("UNEXPECTED TOKEN STARTING COMMAND")

################################################################################
# Parse Commands 
################################################################################

def parse_ReadCmd(tokens, start_index):
    index = start_index + 1
    (x, index) =        expect_token(tokens, index, IMAGE)
    (string, index) =   expect_token(tokens, index, STRING)   # Extract string field
    (x, index) =        expect_token(tokens, index, TO)
    (lvalue, index) =   parse_Lvalue(tokens, index)           # Parse Lvalue field
    (x, index) =        expect_token(tokens, index, NEWLINE)

    return (ReadCmd(tokens[start_index].start, string, lvalue), index)

def parse_WriteCmd(tokens, start_index):
    index = start_index + 1
    (x,index) =         expect_token(tokens, index, IMAGE)
    (expr, index) =     parse_Expr(tokens, index)             # Parse expression field
    (x, index) =        expect_token(tokens, index, TO)
    (string, index) =   expect_token(tokens, index, STRING)   # Extract string field
    (x, index) =        expect_token(tokens, index, NEWLINE)

    return (WriteCmd(tokens[start_index].start, expr, string), index)

def parse_LetCmd(tokens, start_index):
    index = start_index + 1
    (lvalue, index) =   parse_Lvalue(tokens, index)           # Parse Lvalue field
    (x, index) =        expect_token(tokens, index, EQUALS)
    (expr, index) =     parse_Expr(tokens, index)             # Parse expression field
    (x, index) =        expect_token(tokens, index, NEWLINE)

    return (LetCmd(tokens[start_index].start, lvalue, expr), index)

def parse_AssertCmd(tokens, start_index):
    index = start_index + 1
    (expr, index) =     parse_Expr(tokens, index)             # Parse expression field
    (x, index) =        expect_token(tokens, index, COMMA)
    (string, index) =   expect_token(tokens, index, STRING)   # Extract string field
    (x, index) =        expect_token(tokens, index, NEWLINE)

    return (AssertCmd(tokens[start_index].start, expr, string), index)

def parse_PrintCmd(tokens, start_index):
    index = start_index + 1
    (string, index) =   expect_token(tokens, index, STRING)   # Extract string field
    (x, index) =        expect_token(tokens, index, NEWLINE)

    return (PrintCmd(tokens[start_index].start, string), index)

def parse_ShowCmd(tokens, start_index):
    index = start_index + 1
    (expr, index) =     parse_Expr(tokens, index)             # Parse expression field
    (x, index) =        expect_token(tokens, index, NEWLINE)

    return (ShowCmd(tokens[start_index].start, expr), index)

def parse_TimeCmd(tokens, start_index):
    index = start_index + 1
    (cmd, index) =      parse_Cmd(tokens, index)              # Parse command field
    
    return (TimeCmd(tokens[start_index].start, cmd), index)

def parse_FnCmd(tokens, start_index):
    index = start_index + 1
    (variable, index) = expect_token(tokens, index, VARIABLE) # Extract variable field
    (x, index) =        expect_token(tokens, index, LPAREN)
    (b_list, index) =   parse_sequence(tokens, index, SequenceType.BINDING, COMMA, RPAREN)  # Parse binding list
    (x, index) =        expect_token(tokens, index, COLON)
    (type, index) =     parse_Type(tokens, index)             # Parse type field
    (x, index) =        expect_token(tokens, index, LCURLY)
    (x, index) =        expect_token(tokens, index, NEWLINE)
    (s_list, index) =          parse_sequence(tokens, index, SequenceType.STATEMENT, NEWLINE, RCURLY)
    (x, index) =        expect_token(tokens, index, NEWLINE)

    return (FnCmd(tokens[start_index].start, variable, b_list, type, s_list), index)

def parse_StructCmd(tokens, start_index):
    index = start_index + 1
    (variable, index) = expect_token(tokens, index, VARIABLE) # Extract variable field
    (x, index) =        expect_token(tokens, index, LCURLY)
    (x, index) =        expect_token(tokens, index, NEWLINE)
    (f_list, index) =          parse_sequence(tokens, index, SequenceType.STRUCT_FIELD, NEWLINE, RCURLY)
    (x, index) =        expect_token(tokens, index, NEWLINE)

    return (StructCmd(tokens[start_index].start, variable, f_list), index)

def parse_Cmd(tokens, start_index):
    next_token = tokens[start_index]
    match type(next_token).__name__:
        case 'READ':
            return parse_ReadCmd(tokens, start_index)
        case 'WRITE':
            return parse_WriteCmd(tokens, start_index)
        case 'LET':
            return parse_LetCmd(tokens, start_index)
        case 'ASSERT':
            return parse_AssertCmd(tokens, start_index)
        case 'PRINT':
            return parse_PrintCmd(tokens, start_index)
        case 'SHOW':
            return parse_ShowCmd(tokens, start_index)
        case 'TIME':
            return parse_TimeCmd(tokens, start_index)
        case 'FN':
            return parse_FnCmd(tokens, start_index)
        case 'STRUCT':
            return parse_StructCmd(tokens, start_index)
        case 'NEWLINE':
            return parse_Cmd(tokens, start_index + 1)
        case _:
            raise Exception("UNEXPECTED TOKEN STARTING COMMAND")

################################################################################
# Top-Level Parser 
################################################################################

def parse(tokens):
    nodes = []
    index = 0

    while (index < len(tokens) - 1):
        (node, index) = parse_Cmd(tokens, index)
        nodes.append(node)
        
    return nodes
