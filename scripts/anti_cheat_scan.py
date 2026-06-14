import os
import sys
import ast
import warnings

# Suppress deprecation warnings from ast library in newer Python versions
warnings.filterwarnings("ignore", category=DeprecationWarning)

def check_file_for_cheating(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    try:
        tree = ast.parse(content, filename=filepath)
    except Exception as e:
        print(f"Error parsing {filepath}: {e}")
        return []

    violations = []
    ast_Num = getattr(ast, 'Num', None)
    
    class ClickVisitor(ast.NodeVisitor):
        def visit_Call(self, node):
            is_click = False
            func_name = ""
            
            if isinstance(node.func, ast.Attribute):
                if isinstance(node.func.value, ast.Name) and node.func.value.id == 'pyautogui':
                    func_name = node.func.attr
                    if func_name in ('click', 'doubleClick', 'tripleClick', 'rightClick', 'leftClick', 'middleClick', 'moveTo'):
                        is_click = True
            elif isinstance(node.func, ast.Name):
                func_name = node.func.id
                if func_name in ('click', 'doubleClick', 'tripleClick', 'rightClick', 'leftClick', 'middleClick', 'moveTo'):
                    is_click = True
            
            if is_click:
                # Check positional args: x and y are the first two arguments
                for idx, arg in enumerate(node.args):
                    if idx < 2:
                        is_literal = False
                        val = None
                        if isinstance(arg, ast.Constant) and isinstance(arg.value, (int, float)):
                            is_literal = True
                            val = arg.value
                        elif ast_Num and isinstance(arg, ast_Num):
                            is_literal = True
                            val = getattr(arg, 'n', None)
                        
                        if is_literal:
                            violations.append((node.lineno, f"Hardcoded coordinate argument index {idx} with value {val} in {func_name}"))
                
                # Check keyword args: x and y
                for kw in node.keywords:
                    if kw.arg in ('x', 'y'):
                        val_node = kw.value
                        is_literal = False
                        val = None
                        if isinstance(val_node, ast.Constant) and isinstance(val_node.value, (int, float)):
                            is_literal = True
                            val = val_node.value
                        elif ast_Num and isinstance(val_node, ast_Num):
                            is_literal = True
                            val = getattr(val_node, 'n', None)
                        
                        if is_literal:
                            violations.append((node.lineno, f"Hardcoded coordinate keyword argument '{kw.arg}' with value {val} in {func_name}"))
            
            self.generic_visit(node)

    visitor = ClickVisitor()
    visitor.visit(tree)
    return violations

def main():
    target_dirs = ['scripts/win', 'tests']
    all_violations = {}
    
    for d in target_dirs:
        if not os.path.exists(d):
            continue
        for root, _, files in os.walk(d):
            for file in files:
                if file.endswith('.py'):
                    path = os.path.join(root, file)
                    violations = check_file_for_cheating(path)
                    if violations:
                        all_violations[path] = violations
                        
    if all_violations:
        print("[FAIL] Anti-Cheat Scan Failed! The following hardcoded coordinate clicks were found:")
        for path, violations in all_violations.items():
            print(f"\nFile: {path}")
            for lineno, msg in violations:
                print(f"  Line {lineno}: {msg}")
        sys.exit(1)
    else:
        print("[OK] Anti-Cheat Scan Passed! No hardcoded click coordinates found.")
        sys.exit(0)

if __name__ == '__main__':
    main()
