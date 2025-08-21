from astnodes import *
from environment import *

class CallingConvention:
    # regs is list[(int, str)] or list[(int, int)]. Case 0 is int, 1 is float, 2 is stack for arguments
    def __init__(self, regs, ret_val, stack_size, stack_base):
        self.regs = regs
        self.ret_val = ret_val
        self.stack_size = stack_size
        self.stack_base = stack_base

class FunctionInfo:
    def __init__(self, fn_type: ResolvedType, arg_types: list[ResolvedType], env):
        self.fn_type = fn_type
        self.arg_types = arg_types
        self.env = env