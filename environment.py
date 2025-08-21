from astnodes import *
from functioninfo import *

@dataclass #Henderson: added error messages so that key errors are easier to determine if coming from internal maps or env class
class Environment:
    def __init__(self, parent):
        self.parent = parent
        self.structs = {}
        self.variables = {}
        self.functions = {}
    def add_struct(self, key: str, name_info: list[(str, ResolvedType)]):
        if not isinstance(key, str):
            raise Exception("attempted to ADD struct with key that is not str to environment")
        if self.has(key):
            raise Exception("Tried to add key that is already present")
        self.structs[key] = name_info
    def add_var(self, key: str, name_info: ResolvedType): #unsure about what name_infor should be here
        if not isinstance(key, str):
            raise Exception("attempted to ADD variable with key that is not str to environment")
        if self.has(key):
            raise Exception("Tried to add key that is already present")
        self.variables[key] = name_info
    def add_function(self, key: str, fn_info):
        if not isinstance(key, str):
            raise Exception("attempted to ADD function with key that is not str to environment")
        if self.has(key):
            raise Exception("Tried to add key that is already present")
        else:
            self.functions[key] = fn_info
    def get_struct(self, key: str):
        if not isinstance(key, str):
            raise Exception("attempted to GET struct with key that is not str from environment")
        if key in self.structs:
            return self.structs[key]
        elif self.parent is not None:
            return self.parent.get_struct(key)
        else:
            return None
    def get_var(self, key: str):
        if not isinstance(key, str):
            raise Exception("attempted to GET variable with key that is not str from environment")
        if key in self.variables:
            return self.variables[key]
        elif self.parent is not None:
            return self.parent.get_var(key)
        else:
            raise Exception(f"attempted to GET variable with key {key} that is not defined")
    def get_function(self, key: str):
        if not isinstance(key, str):
            raise Exception("attempted to GET function with key that is not str from environment")
        if key in self.functions:
            return self.functions[key]
        elif self.parent is not None:
            return self.parent.get_function(key)
        else:
            return None
    def has(self, key: str):
        if not isinstance(key, str):
            raise Exception("called has function on key that is not an str in environment")
        if key in self.variables:
            return True
        elif key in self.structs:
            return True
        elif key in self.functions:
            return True
        elif self.parent is not None:
            return self.parent.has(key)
        else:
            return False