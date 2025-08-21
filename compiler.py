#!/usr/bin/env python3
from lexerRegex import *
from parser import *
from typechecker import *
from generatingC import *
from generatingAssembly import *
from assemblyOptimized import *
from tensorContraction import *

if __name__ == "__main__":
    import sys
    import argparse
    parser = argparse.ArgumentParser(prog = 'JPL Compiler', 
                                     description='A file that compilers JPL code into assembly code, designed by Draden and Henderson')
    parser.add_argument('-l', '--lexer', action="store_true", help="will print lexed tokens, one per line")
    parser.add_argument('-p', '--parser', action="store_true", help="will print parsed S-expressions, one per line")
    parser.add_argument('-t', '--typechecker', action="store_true", help="will print parsed S-expressions along with checked types, one per line")
    parser.add_argument('-i', '--c_ir', action="store_true", help="will output compiled C code")
    parser.add_argument('-s', '--assembly', action="store_true", help="will output compiled assembly code")
    parser.add_argument('-O1', '--peephole', action="store_true", help="will run peephole optimizations")
    parser.add_argument('-O3', '--loop_permutation', action="store_true", help="will run peephole optimizations")
    parser.add_argument('filename', type=str)
    args = parser.parse_args()
    
    # Build list of tokens
    tokens = []
    try:
        with open(args.filename, "r") as file:
            try:
                #TODO: clean up format based on compiler flags
                tokens = lex(file.read()) #need to try catch for file not found (compilation failed) exception
                if args.lexer:
                    for t in tokens:
                        if type(t) is NEWLINE or type(t) is END_OF_FILE:
                            print(type(t).__name__)
                        else:
                            print(type(t).__name__ + " " + '\'' + t.text + '\'') #make sure this space doesn't cause problems for newline or eof
            except Exception:
                print("Compilation failed: Could not lex")
                sys.exit()
            
            try:
                nodes = parse(tokens)
                if args.parser:
                    for n in nodes:
                        print(n.toString()) 
            
            except Exception as e:
                print("Compilation failed: Could not parse", e.args)
                sys.exit()

            try:
                env = typecheck(nodes)
                if args.typechecker:
                    for n in nodes:
                        print(n.toString()) 
            except Exception as e:
                print("Compilation failed: Could not typecheck", e.args)
                sys.exit()

            try:
                if args.c_ir:
                    code = gen_C_program(nodes, env)
                    print(code)
            except Exception as e:
                print("Compilation failed: could not generate C-IR", e.args)
                sys.exit()

            try:
                if args.assembly:
                    #TODO: DOES O3 OPTIMIZATION MEAN WE ALSO USE O1 OPTIMIZATION???
                    nodes = tensorContraction(nodes, env, args.loop_permutation)
                    if args.peephole or args.loop_permutation: # and args.loop_permutation:
                        code = gen_assembly_program(nodes, env, 1)
                    else:
                        code = gen_assembly_program(nodes, env, 0)
                    print(code)
            except Exception as e:
                print("Compilation failed: could not generate assembly", e.args)
                sys.exit()

            #print("Compilation Succeeded")

    except (FileNotFoundError, UnicodeDecodeError):
        print("Compilation failed: Could not open file")
        sys.exit()

    print("Compilation succeeded")
