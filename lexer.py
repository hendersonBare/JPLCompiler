from tokens import *
from enum import Enum 
 
class State(Enum):
    START = 0
    WORD = 1
    INT = 2
    FLOAT = 3
    STRING = 4
    COMMENT = 5
    DOT = 6
    SLASH = 7
    BAcKSLASH = 8

    #Special cases: 
    #   backslash-newline
    #   equality ops
    #   special characters

def lexer(text):
    token_list = []
    operators = ['+', '-', '*', '<', '>', '%']
    matching = State.START
    start_index = 0
    for i in range(len(text)):
        c = text[i]
        match matching:
            case State.START:
                if c == " ":
                    pass
                elif c.isdigit():
                    matching = State.INT
                elif c.isalpha():
                    matching = State.WORD
                elif c == "\"":
                    matching = State.STRING
                elif c == ".":
                    matching = State.DOT
                elif c == "/":
                    matching = State.SLASH
                elif c == "\\":
                    matching = State.BACKSLASH #unclear on newline
                elif c in operators:
                    token_list.append(OP(start_index, i, c))
                elif c == ",":
                    token_list.append(COMMA(start_index, i))
                elif c == "[":
                    token_list.append(LSQUARE(start_index, i))
                elif c == "]":
                    token_list.append(RSQUARE(start_index, i))
                elif c == "{":
                    token_list.append(LCURLY(start_index, i))
                elif c == "}":
                    token_list.append(RCURLY(start_index, i))
                elif c == "(":
                    token_list.append(LPAREN(start_index, i))
                elif c == ")":
                    token_list.append(RPAREN(start_index, i))
                elif c == ":":
                    token_list.append(COLON(start_index, i))
                else:
                    #compilation failed?
                    pass
            case State.WORD:
                pass
            case State.INT:
                pass
            case State.FLOAT:
                pass
            case State.STRING:
                pass
            case State.COMMENT:
                pass
            case State.DOT:
                pass
            case State.SLASH:
                pass
            case State.BACKSLASH:
                pass





    return token_list