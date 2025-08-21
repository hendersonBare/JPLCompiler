from dataclasses import dataclass

@dataclass
class Token:
    def __init__(self, start, text):
        self.start = start
        self.text = text


class WHITESPACE(Token):
    pass


class ARRAY(Token):
    pass


class ASSERT(Token):
    pass


class BOOL(Token):
    pass


class COLON(Token):
    pass


class COMMA(Token):
    pass


class DOT(Token):
    pass


class ELSE(Token):
    pass


class END_OF_FILE(Token):
    pass


class EQUALS(Token):
    pass


class FALSE(Token):
    pass


class FLOAT(Token):
    pass


class FLOATVAL(Token):
    pass


class FN(Token):
    pass


class IF(Token):
    pass


class IMAGE(Token):
    pass


class INT(Token):
    pass


class INTVAL(Token):
    pass


class LCURLY(Token):
    pass


class LET(Token):
    pass


class LPAREN(Token):
    pass


class LSQUARE(Token):
    pass


class NEWLINE(Token):
    pass


class OP(Token):
    pass


class PRINT(Token):
    pass


class RCURLY(Token):
    pass


class RPAREN(Token):
    pass


class RSQUARE(Token):
    pass


class SHOW(Token):
    pass


class STRING(Token):
    pass


class STRUCT(Token):
    pass


class SUM(Token):
    pass


class THEN(Token):
    pass


class TIME(Token):
    pass


class TO(Token):
    pass


class TRUE(Token):
    pass

class VARIABLE(Token):
    pass

class VOID(Token):
    pass

class WRITE(Token):
    pass

class READ(Token):
    pass

class RETURN(Token):
    pass