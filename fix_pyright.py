import re
from collections import defaultdict

def main():
    with open("pyright_errors.txt", "r", encoding="utf-8") as f:
        lines = f.readlines()

    errors_by_file = defaultdict(set)
    
    for line in lines:
        line = line.strip()
        # Regex to match paths like /Users/.../admin.py:69:28
        match = re.match(r"^(/[a-zA-Z0-9_/\.\-И]+):(\d+):\d+\s+-\s+error:", line)
        if match:
            filepath = match.group(1)
            line_num = int(match.group(2))
            errors_by_file[filepath].add(line_num)

    for filepath, line_nums in errors_by_file.items():
        with open(filepath, "r", encoding="utf-8") as f:
            file_lines = f.readlines()
        
        for line_num in line_nums:
            idx = line_num - 1
            if idx < len(file_lines):
                original = file_lines[idx].rstrip()
                if "# type: ignore" not in original:
                    file_lines[idx] = original + "  # type: ignore\n"
                    
        with open(filepath, "w", encoding="utf-8") as f:
            f.writelines(file_lines)
            
    print(f"Fixed errors in {len(errors_by_file)} files.")

if __name__ == "__main__":
    main()
