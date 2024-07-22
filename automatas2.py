import tkinter as tk
from tkinter import scrolledtext

class Token:
    def __init__(self, type, value):
        self.type = type
        self.value = value

class Lexer:
    def __init__(self, code):
        self.code = code
        self.position = 0

    def get_next_token(self):
        if self.position >= len(self.code):
            return Token('EOF', None)

        current_char = self.code[self.position]

        if current_char.isspace():
            self.position += 1
            return self.get_next_token()

        if current_char.isdigit():
            num = ''
            while self.position < len(self.code) and self.code[self.position].isdigit():
                num += self.code[self.position]
                self.position += 1
            return Token('NUMBER', int(num))

        if current_char.isalpha():
            identifier = ''
            while self.position < len(self.code) and (self.code[self.position].isalnum() or self.code[self.position] == '_'):
                identifier += self.code[self.position]
                self.position += 1
            
            keywords = {
                'print': 'PRINT', 'range': 'RANGE', 'def': 'DEF', 'return': 'RETURN',
                'import': 'IMPORT', 'class': 'CLASS', 'if': 'IF', 'else': 'ELSE',
                'for': 'FOR', 'while': 'WHILE', 'break': 'BREAK', 'continue': 'CONTINUE'
            }
            return Token(keywords.get(identifier, 'IDENTIFIER'), identifier)

        if current_char in '+-*/(){}:=<>,':
            self.position += 1
            return Token(current_char, current_char)

        if current_char == '"':
            string = ''
            self.position += 1
            while self.position < len(self.code) and self.code[self.position] != '"':
                string += self.code[self.position]
                self.position += 1
            self.position += 1
            return Token('STRING', string)

        raise Exception(f"Carácter no reconocido: {current_char}")

class Parser:
    def __init__(self, lexer):
        self.lexer = lexer
        self.current_token = self.lexer.get_next_token()

    def eat(self, token_type):
        if self.current_token.type == token_type:
            self.current_token = self.lexer.get_next_token()
        else:
            raise Exception(f"Error de sintaxis: se esperaba {token_type}, se obtuvo {self.current_token.type}")

    def program(self):
        statements = []
        while self.current_token.type != 'EOF':
            statements.append(self.statement())
        return statements

    def statement(self):
        if self.current_token.type == 'PRINT':
            return self.print_statement()
        elif self.current_token.type == 'IDENTIFIER':
            if self.lexer.code[self.lexer.position] == '(':
                return self.function_call_statement()
            else:
                return self.assignment_statement()
        elif self.current_token.type == 'DEF':
            return self.function_definition()
        else:
            raise Exception(f"Declaración no válida: {self.current_token.type}")

    def print_statement(self):
        self.eat('PRINT')
        self.eat('(')
        exprs = [self.expression()]
        while self.current_token.type == ',':
            self.eat(',')
            exprs.append(self.expression())
        self.eat(')')
        return ('PRINT', exprs)

    def assignment_statement(self):
        var = self.current_token.value
        self.eat('IDENTIFIER')
        self.eat('=')
        expr = self.expression()
        return ('ASSIGN', var, expr)

    def function_definition(self):
        self.eat('DEF')
        name = self.current_token.value
        self.eat('IDENTIFIER')
        self.eat('(')
        params = []
        if self.current_token.type == 'IDENTIFIER':
            params.append(self.current_token.value)
            self.eat('IDENTIFIER')
            while self.current_token.type == ',':
                self.eat(',')
                params.append(self.current_token.value)
                self.eat('IDENTIFIER')
        self.eat(')')
        self.eat('{')
        body = self.statements()
        self.eat('}')
        return ('FUNCTION_DEF', name, params, body)

    def function_call_statement(self):
        func_name = self.current_token.value
        self.eat('IDENTIFIER')
        self.eat('(')
        args = []
        if self.current_token.type in ('NUMBER', 'STRING', 'IDENTIFIER'):
            args.append(self.expression())
            while self.current_token.type == ',':
                self.eat(',')
                args.append(self.expression())
        self.eat(')')
        return ('CALL', func_name, args)

    def statements(self):
        statements = []
        while self.current_token.type != 'EOF' and self.current_token.type != '}':
            statements.append(self.statement())
        return statements

    def expression(self):
        node = self.term()
        while self.current_token.type in ('+', '-'):
            op = self.current_token.type
            self.eat(op)
            node = (op, node, self.term())
        return node

    def term(self):
        node = self.factor()
        while self.current_token.type in ('*', '/'):
            op = self.current_token.type
            self.eat(op)
            node = (op, node, self.factor())
        return node

    def factor(self):
        token = self.current_token
        if token.type == 'NUMBER':
            self.eat('NUMBER')
            return ('NUMBER', token.value)
        elif token.type == 'IDENTIFIER':
            self.eat('IDENTIFIER')
            return ('VARIABLE', token.value)
        elif token.type == 'STRING':
            self.eat('STRING')
            return ('STRING', token.value)
        elif token.type == '(':
            self.eat('(')
            expr = self.expression()
            self.eat(')')
            return expr
        else:
            raise Exception(f"Factor no válido: {token.type}")

class Interpreter:
    def __init__(self):
        self.variables = {}
        self.functions = {}
        self.custom_print = print

    def interpret(self, ast):
        if isinstance(ast, tuple):
            if ast[0] == 'PRINT':
                for expr in ast[1]:
                    self.custom_print(self.interpret(expr))
            elif ast[0] == 'ASSIGN':
                _, var, expr = ast
                self.variables[var] = self.interpret(expr)
            elif ast[0] == 'FUNCTION_DEF':
                _, name, params, body = ast
                self.functions[name] = (params, body)
            elif ast[0] == 'CALL':
                _, func_name, args = ast
                if func_name in self.functions:
                    params, body = self.functions[func_name]
                    local_vars = dict(zip(params, [self.interpret(arg) for arg in args]))
                    old_vars = self.variables.copy()
                    self.variables.update(local_vars)
                    result = None
                    for stmt in body:
                        result = self.interpret(stmt)
                    self.variables = old_vars
                    return result
                else:
                    raise Exception(f"Función no definida: {func_name}")
            elif ast[0] in ('+', '-', '*', '/'):
                op, left, right = ast
                left_val = self.interpret(left)
                right_val = self.interpret(right)
                if op == '+':
                    return left_val + right_val
                elif op == '-':
                    return left_val - right_val
                elif op == '*':
                    return left_val * right_val
                elif op == '/':
                    return left_val / right_val
            elif ast[0] == 'NUMBER':
                return ast[1]
            elif ast[0] == 'STRING':
                return ast[1]
            elif ast[0] == 'VARIABLE':
                return self.variables.get(ast[1], 0)
        return ast


class SimplePythonIDE:
    def __init__(self, master):
        self.master = master
        master.title("Compilador by: Jhonel Pesantes")

        # Estilo oscuro
        self.dark_bg = '#2E2E2E'
        self.dark_fg = '#D3D3D3'
        self.highlight_bg = '#444444'
        
        self.line_numbers = tk.Text(master, width=4, padx=3, takefocus=0, border=0, background=self.dark_bg, foreground=self.dark_fg, state='disabled', wrap='none')
        self.line_numbers.pack(side='left', fill='y')

        self.code_editor = scrolledtext.ScrolledText(master, wrap=tk.NONE, undo=True, width=60, height=20, font=("Consolas", 12), background=self.dark_bg, foreground=self.dark_fg, insertbackground='white')
        self.code_editor.pack(side='left', fill='both', expand=True)
        self.code_editor.bind('<KeyRelease>', self.update_line_numbers)
        self.update_line_numbers()

        self.run_button = tk.Button(master, text="Ejecutar", command=self.run_code, bg='#444444', fg=self.dark_fg, relief='flat')
        self.run_button.pack(pady=5)

        self.output_area = scrolledtext.ScrolledText(master, wrap=tk.WORD, width=60, height=10, state='disabled', font=("Consolas", 12), background=self.dark_bg, foreground=self.dark_fg)
        self.output_area.pack(padx=10, pady=10)

    def update_line_numbers(self, event=None):
        self.line_numbers.config(state='normal', background=self.dark_bg, foreground=self.dark_fg)
        self.line_numbers.delete(1.0, tk.END)
        line_count = int(self.code_editor.index('end-1c').split('.')[0])
        line_numbers = "\n".join(str(i) for i in range(1, line_count + 1))
        self.line_numbers.insert(1.0, line_numbers)
        self.line_numbers.config(state='disabled')

    def custom_print(self, *args, **kwargs):
        output = " ".join(map(str, args))
        self.output_area.config(state='normal')
        self.output_area.insert(tk.END, output + "\n")
        self.output_area.see(tk.END)
        self.output_area.config(state='disabled')

    def run_code(self):
        self.output_area.config(state='normal')
        self.output_area.delete(1.0, tk.END)
        
        code = self.code_editor.get(1.0, tk.END)

        try:
            lexer = Lexer(code)
            parser = Parser(lexer)
            interpreter = Interpreter()
            
            ast = list(parser.program())
            
            interpreter.custom_print = self.custom_print
            
            for node in ast:
                interpreter.interpret(node)
            
        except Exception as e:
            self.output_area.insert(tk.END, f"Error: {str(e)}")

        self.output_area.config(state='disabled')

if __name__ == "__main__":
    root = tk.Tk()
    ide = SimplePythonIDE(root)
    root.mainloop()
