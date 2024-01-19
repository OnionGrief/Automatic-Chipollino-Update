import yaml
import difflib
import os

with open("config.yaml", "r") as file:
    data = yaml.safe_load(file)

# вывод разницы версий файла
def print_diff(prev_file_lines, file_path):
    print(f"\n{file_path}:")
    with open(file_path, "r", encoding="utf-8") as file:
        diff = difflib.unified_diff(prev_file_lines, file.readlines())

    for line in diff:
        print(line, end="" if line[-1] == "\n" else "\n")

def rewrite_in_file(file_path, insert_place, new_text, is_logged=True):
    with open(file_path, "r", encoding="utf-8") as file:
        lines = file.readlines()
    prev_lines = lines[:]

    # Место для вставки
    for i in range(len(lines)):
        if insert_place in lines[i]:
            brackets_num = lines[i].count("{") - lines[i].count("}")
            lines.pop(i)
            while brackets_num > 0:
                brackets_num += lines[i].count("{") - lines[i].count("}")
                lines.pop(i)
            lines.insert(i, new_text)
            break

    with open(file_path, "w", encoding="utf-8") as file:
        file.writelines(lines)

    if is_logged:
        print_diff(prev_lines, file_path)

def write_in_file(file_path, insert_place, new_text, is_logged=True):
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

    if is_logged:
        print_diff(prev_lines, file_path)

# мапа как в интерпретаторе (список функций по имени)
names_to_funcs = {}
for f in data["functions"]:
    if not names_to_funcs.get(f["name"]):
        names_to_funcs[f["name"]] = []
    names_to_funcs[f["name"]].append(f)
    f["id"] = len(names_to_funcs[f["name"]])
# имена шаблонов
for f in data["functions"]:
    f["template_name"] = f["name"]
    if len(names_to_funcs[f["name"]]) > 1:
        f["template_name"] += str(f["id"])
for f in data['functions']:
    f.setdefault('need_template', True)

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
        prev_lines = file.readlines()

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
                    is_logged=False
                )
    print_diff(prev_lines, interpreter_path)

def get_content(file_path, hint, end_mark="}"):
    with open(file_path, "r", encoding="utf-8") as file:
        file_content = file.read()
    insert_index = file_content.find(hint)
    if insert_index == -1:
        print("not found " + hint)
        return
    brace_index = file_content.find(end_mark, insert_index)

    return (
        file_content[:insert_index],
        file_content[insert_index:brace_index],
        file_content[brace_index:],
    )

def add_to_ObjectType(file_path):
    insert_place = "enum class ObjectType {"
    file_begin, placeholder, file_end = get_content(file_path, insert_place)
    for type in data["types"]:
        if type not in placeholder:
            placeholder += f"\t{type},\n"

    with open(file_path, "w", encoding="utf-8") as file:
        file.write(file_begin + placeholder + file_end)

def add_to_structs(file_path):
    insert_place = "// Сами структуры"
    file_begin, placeholder, file_end = get_content(
        file_path, insert_place, end_mark="\n\n"
    )
    for type, info in data["types"].items():
        if "Object" + type not in placeholder and info != None:
            placeholder += f"\nstruct Object{type};"

    with open(file_path, "w", encoding="utf-8") as file:
        file.write(file_begin + placeholder + file_end)

def add_to_GeneralObject(file_path):
    insert_place = "using GeneralObject ="
    file_begin, placeholder, file_end = get_content(
        file_path, insert_place, end_mark=">"
    )
    for type, info in data["types"].items():
        if "Object" + type not in placeholder and info != None:
            placeholder += f", Object{type}"

    with open(file_path, "w", encoding="utf-8") as file:
        file.write(file_begin + placeholder + file_end)

"""
def generate_object_definitions():
    res_str = ""
    for name, info in data["types"].items():
        if info == None:
            continue
        res_str += f'OBJECT_DEFINITION({name}, {info["class"]})\n'
    return res_str"""

def add_to_object_definitions(file_path):
    insert_place = "// Определение структур объектов"
    file_begin, placeholder, file_end = get_content(
        file_path, insert_place, end_mark="\n\n"
    )
    for type, info in data["types"].items():
        if f"({type}," not in placeholder and info != None:
            placeholder += f'\nOBJECT_DEFINITION({type}, {info["class"]})'

    with open(file_path, "w", encoding="utf-8") as file:
        file.write(file_begin + placeholder + file_end)

def generate_map_types_to_str():
    map_str = "inline static const std::unordered_map<ObjectType, std::string> types_to_string = {\n"
    for type in data["types"]:
        map_str += f'\t{{ObjectType::{type}, "{type}"}},\n'
    map_str += "};\n"
    return map_str

def add_to_typization():
    typization_path = (
        data["chipollino_path"] + "/libs/FuncLib/include/FuncLib/Typization.h"
    )

    with open(typization_path, "r", encoding="utf-8") as file:
        prev_lines = file.readlines()

    add_to_ObjectType(typization_path)
    add_to_structs(typization_path)
    add_to_GeneralObject(typization_path)
    add_to_object_definitions(typization_path)
    rewrite_in_file(
        file_path=typization_path,
        insert_place="unordered_map<ObjectType, std::string> types_to_string",
        new_text=generate_map_types_to_str(),
        is_logged = False
    )

    print_diff(prev_lines, typization_path)

def generate_templates():
    for f in data["functions"]:
        file_path = data["chipollino_path"] + f'/resources/template/{f["template_name"]}.tex'
        if not os.path.exists(file_path) and f["need_template"]:
            # создание файла
            with open(file_path, "w") as file:
                pass
            with open(file_path, "r", encoding="utf-8") as file:
                prev_lines = file.readlines()
                
            file_content = f"\\section{{{f['name']}}}\n"
            file_content += f"\\begin{{frame}}{{$\\{f['name']}\\TypeIs"
            # хз что делать если аргументов > 2
            if len(f["arguments"]) == 1:
                file_content += f"\\{f['arguments'][0]}TYPE"
            else:
                file_content += f"\\pair{{\\{f['arguments'][0]}TYPE}}{{\\{f['arguments'][1]}TYPE}}"
            file_content += f"\\to\\{f['return_type']}TYPE$}}\n"
            file_content += "\tДо:\n"
            for i in range(len(f["arguments"])):
                file_content += f"\t%template_{f['arguments'][i]}{i+1 if len(f['arguments']) != 1 else ''}\n"
            file_content += f"\n\tРезультат:\n\t%template_result\n\n"
            file_content += "\\end{frame}"

            with open(file_path, "w", encoding="utf-8") as file:
                file.write(file_content)
            print_diff(prev_lines, file_path)

# Functions.h functions
rewrite_in_file(
    file_path=data["chipollino_path"] + "/libs/FuncLib/include/FuncLib/Functions.h",
    insert_place="vector<Function> functions",
    new_text=generate_funcs_vector(),
)
# interpreter.cpp apply_function()
add_to_interpreter_apply_function()
# Typization.h
add_to_typization()
# templates
generate_templates()