from tokens import *
import re

keywords = {"array": ARRAY, "assert": ASSERT, "bool": BOOL, "else": ELSE, "false": FALSE, "float": FLOAT,
            "fn": FN, "if": IF, "image": IMAGE, "int": INT, "let": LET, "print": PRINT, "read": READ,
            "return": RETURN, "show": SHOW, "struct": STRUCT, "sum": SUM, "then": THEN, "time": TIME,
            "to": TO, "true": TRUE, "void": VOID, "write": WRITE}

#in order of regex: line comments, multiline comments, newline escape, any number of spaces
whitespace_alternatives = [r'\/\/[^\n]*\n', r'\/\*(?:(?!\*\/).|\n)*\*\/', r'\\\n', r' +']

string_tuple = (STRING, r'"[\x20-\x21\x23-\x7E]*"')

variable_tuple = (VARIABLE, r'[a-zA-Z][\w]*')

float_tuple = (FLOATVAL, r'\d*\.\d+|\d+\.\d*')

int_tuple = (INTVAL, r'\d+')

dub_op_tuple = (OP, r'%|\|\||\&\&|>=|<=|!=|==')

op_tuple = (OP, r'\+|-|!|\*|\/|%|>|<')

equals_tuple = (EQUALS, r'=')

lcurly_tuple = (LCURLY, r'{')

rcurly_tuple = (RCURLY, r'}')

lbracket_tuple = (LSQUARE, r'\[')

rbracket_tuple = (RSQUARE, r'\]')

lparen_tuple = (LPAREN, r'\(')

rparen_tuple = (RPAREN, r'\)')

dot_tuple = (DOT, r'\.')

comma_tuple = (COMMA, r',')

colon_tuple = (COLON, r':')

newline_tuple = (NEWLINE, r'\n+')

eof_tuple = (END_OF_FILE, r'\Z') #this is not working properly

Token_regex = [string_tuple, float_tuple, int_tuple, variable_tuple, dub_op_tuple, op_tuple, equals_tuple, 
               lcurly_tuple, rcurly_tuple, lbracket_tuple, rbracket_tuple, lparen_tuple, rparen_tuple, dot_tuple,
               comma_tuple, colon_tuple, newline_tuple, eof_tuple]

def lex(text):
    tokens = []
    start = 0
    while start < len(text):
        t_start, end, t_type, t_content= next_token(start, text)
        if t_type is None:
            #raise a lexer error if there is no match
            raise Exception("COULD NOT LEX")
        else:
            start = end
            if t_type == WHITESPACE:
                continue #go to next iteration of the loop
            new_token = t_type(t_start, t_content)
            if len(tokens) == 0 or not (type(tokens[-1]) == NEWLINE and t_type == NEWLINE):
                tokens.append(new_token)
    #end of file must be reached, if it cant then we will never exit
    eof_token = END_OF_FILE(len(text), "")
    tokens.append(eof_token)
    return tokens

def next_token(start, text):
    #use matchfull instead and iterate backwards so that we avoid matching with previous strings
    #refer to: https://stackoverflow.com/questions/12251545/how-do-i-implement-a-lexer-given-that-i-have-already-implemented-a-basic-regular
    for w_regex in whitespace_alternatives:
        does_match = re.match(w_regex, text[start:len(text)])
        if does_match:
            if w_regex == r'\/\/[^\n]*\n':
                return start + does_match.start(), start + does_match.end(), NEWLINE, ""
            else:
                return start + does_match.start(), start + does_match.end(), WHITESPACE, ""
        
    for t_type, t_regex in Token_regex:
        does_match = re.match(t_regex, text[start:len(text)])
        if does_match:
            content = text[start+does_match.start():start+does_match.end()]
            if t_type is VARIABLE:
                if content.lower() in keywords: #are the keywords case sensitive?
                    t_type = keywords[content.lower()]
            return start + does_match.start(), start + does_match.end(), t_type, content
        
    return 0,0, None, ""