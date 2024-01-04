import yaml
import difflib

with open("config.yaml", "r") as file:
    data = yaml.safe_load(file)

# вывод разницы версий файла
def print_diff(prev_file_lines, file_path):
    print(f"\n{file_path}:")
    with open(file_path, "r", encoding="utf-8") as file:
        diff = difflib.unified_diff(prev_file_lines, file.readlines())

    for line in diff:
        print(line, end="" if line[-1] == "\n" else "\n")

def rewrite_in_file(file_path, insert_place, new_text):
    with open(file_path, "r", encoding="utf-8") as file:
        lines = file.readlines()
    prev_lines = lines[:]

    # Место для вставки
    for i in range(len(lines)):
        if insert_place in lines[i]:
            brackets_num = lines[i].count("{") - lines[i].count("}")
            lines.remove(lines[i])
            while brackets_num > 0:
                brackets_num += lines[i].count("{") - lines[i].count("}")
                lines.pop(i)
            lines.insert(i, new_text)
            break

    with open(file_path, "w", encoding="utf-8") as file:
        file.writelines(lines)

    print_diff(prev_lines, file_path)

def write_in_file(file_path, insert_place, new_text):
    with open(file_path, "r", encoding="utf-8") as file:
        lines = file.readlines()
    prev_lines = lines[:]

    # Место для вставки
    for i in range(len(lines)):
        if insert_place in lines[i]:
            lines.insert(i, new_text)
            break

    with open(file_path, "w", encoding="utf-8") as file:
        file.writelines(lines)

    print_diff(prev_lines, file_path)

# генерация cpp кода вектора функций интерпретатора
def generate_funcs_vector():
    funcs_vector = "inline static const std::vector<Function> functions = {\n"
    for func in data["functions"]:
        input = [f"ObjectType::{type}" for type in func["arguments"]]
        funcs_vector += f'\t{{"{func["name"]}", {{{", ".join(input)}}}, ObjectType::{func["return_type"]}}},\n'
    funcs_vector += "};\n"
    return funcs_vector

def exist_func_with_same_name(name):
    count = sum(1 for func in data["functions"] if func["name"] == name)
    return count > 1

def is_child(type1, type2):
    if "children" not in data["types"][type2]:
        return False
    return type1 in data["types"][type2]["children"]

def same_input_output_types(func):
    type1 = func["arguments"][0]
    type2 = func["return_type"]
    return type1 == type2 or is_child(type1, type2) or is_child(type2, type1)

def get_func_mini_head(func):
    handler_str = f'if (function.name == "{func["name"]}"'
    if exist_func_with_same_name(func["name"]):
        handler_str += f' && function.input[0] == ObjectType::{func["arguments"][0]}'
    handler_str += ") {\n"
    return handler_str


# генерация cpp кода обработчика функции интерпретатора
def generate_func_handler(func):
    arg_types = func["arguments"]
    handler_str = "\t" + get_func_mini_head(func)
    handler_str += "\t\treturn "
    handler_str += f'Object{func["return_type"]}('
    if len(func["arguments"]) < 1:
        print(f"error: func {func['name']} has 0 args")
    else:
        handler_str += (
            f'get<Object{arg_types[0]}>(arguments[0]).value.{func["prog_name"]}('
        )
        for j in range(1, len(arg_types)):
            handler_str += f"get<Object{arg_types[j]}>(arguments[{j}]).value, "
        handler_str += "&log_template)"
    handler_str += ");\n\t}\n"
    return handler_str


def add_to_interpreter_apply_function():
    interpreter_path = data["chipollino_path"] + "/libs/Interpreter/src/Interpreter.cpp"
    with open(interpreter_path, "r", encoding="utf-8") as file:
        file_content = file.read()
        for func in data["functions"]:
            if f'if (function.name == "{func["name"]}"' not in file_content: # нужен рабский труд чтобы исп-ть get_func_mini_head(func)
                if same_input_output_types(func):
                    insert_place = "# place for another same types funcs"
                else:
                    insert_place = "# place for another diff types funcs"
                write_in_file(
                    file_path=interpreter_path,
                    insert_place=insert_place,
                    new_text=generate_func_handler(func),
                )

# Functions.h functions
rewrite_in_file(
    file_path=data["chipollino_path"] + "/libs/FuncLib/include/FuncLib/Functions.h",
    insert_place="vector<Function> functions",
    new_text=generate_funcs_vector(),
)
# interpreter.cpp apply_function()
add_to_interpreter_apply_function()