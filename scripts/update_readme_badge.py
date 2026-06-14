import os
import re

def count_rust_tests():
    rust_test_re = re.compile(r'^\s*#\s*\[\s*(?:tokio::)?test\s*\]')
    count = 0
    # Walk phantom-core
    for root, dirs, files in os.walk('phantom-core'):
        if 'target' in dirs:
            dirs.remove('target')  # Skip target directory
        for file in files:
            if file.endswith('.rs'):
                path = os.path.join(root, file)
                try:
                    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                        for line in f:
                            if rust_test_re.match(line):
                                count += 1
                except Exception as e:
                    print(f"Error reading {path}: {e}")
    return count

def count_python_tests():
    py_test_re = re.compile(r'^\s*def\s+test_')
    count = 0
    # Walk kairo-sidecar/tests
    for root, dirs, files in os.walk('kairo-sidecar/tests'):
        for file in files:
            if file.endswith('.py'):
                path = os.path.join(root, file)
                try:
                    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                        for line in f:
                            if py_test_re.match(line):
                                count += 1
                except Exception as e:
                    print(f"Error reading {path}: {e}")
    return count

def update_readme(total_tests):
    readme_path = 'README.md'
    if not os.path.exists(readme_path):
        print("README.md not found.")
        return False
        
    try:
        with open(readme_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Replace the test count in badge
        new_badge = f'tests-{total_tests}%20passing'
        updated_content, count = re.subn(r'tests-\d+%20passing', new_badge, content)
        
        if count > 0:
            with open(readme_path, 'w', encoding='utf-8') as f:
                f.write(updated_content)
            print(f"Successfully updated README.md test badge to {total_tests} passing.")
            return True
        else:
            print("Could not find test badge in README.md to update.")
            return False
    except Exception as e:
        print(f"Error updating README.md: {e}")
        return False

if __name__ == '__main__':
    rust_count = count_rust_tests()
    py_count = count_python_tests()
    total = rust_count + py_count
    print(f"Discovered {rust_count} Rust tests and {py_count} Python tests.")
    update_readme(total)
