import re
import sys

def check_latex(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Check env balance
    begins = re.findall(r'\\begin\{([a-zA-Z*]+)\}', content)
    ends = re.findall(r'\\end\{([a-zA-Z*]+)\}', content)

    print(f"Total \\begin: {len(begins)}, Total \\end: {len(ends)}")
    stack = []
    lines = content.splitlines()
    for line_no, line in enumerate(lines, 1):
        # find all begins and ends in this line
        tokens = re.findall(r'\\(begin|end)\{([a-zA-Z*]+)\}', line)
        for kind, name in tokens:
            if kind == 'begin':
                stack.append((name, line_no))
            else:
                if not stack:
                    print(f"Error: unmatched \\end{{{name}}} at line {line_no}")
                    return False
                top_name, top_line = stack.pop()
                if top_name != name:
                    print(f"Error: mismatched \\begin{{{top_name}}} (line {top_line}) and \\end{{{name}}} (line {line_no})")
                    return False
    if stack:
        print(f"Error: unclosed environments: {stack}")
        return False
    print("All LaTeX environments balanced successfully!")
    return True

if __name__ == '__main__':
    if len(sys.argv) > 1:
        check_latex(sys.argv[1])
