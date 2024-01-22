import yaml
import difflib
import os
import networkx as nx
import pymorphy2

with open("config.yaml", "r", encoding="utf-8") as file:
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
    #f.setdefault('prog_name', f["name"])
# граф вложенности
adjacency_dict = {}
for t, info in data["types"].items():
    if info != None and "children" in info:
            adjacency_dict[t] = info["children"]
# Создаём направленный граф из словаря смежности
typesGraph = nx.DiGraph(adjacency_dict)

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
            if get_func_mini_head(func) not in file_content: # нужен рабский труд чтобы исп-ть get_func_mini_head(func)
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

def create_AlgExpr_heir(name, h_file, cpp_file):
    file_content = ""

    with open(h_file, "w", encoding="utf-8") as file:
        file.write(file_content)

def create_AbstMachine_heir(name, h_file, cpp_file):
    file_content = ""

    with open(h_file, "w", encoding="utf-8") as file:
        file.write(file_content)

# создание новых классов
def create_new_classes():
    for cl, info in data["classes"].items():
        if "extends" in info:
            file_path = f"{data['chipollino_path']}/libs/Objects/include/Objects/{info['file']}.h"
            file_path2 = f"{data['chipollino_path']}/libs/Objects/src/{info['file']}.cpp"
            if not os.path.exists(file_path) or not os.path.exists(file_path2):
                # создание файла
                with open(file_path, "w", encoding="utf-8") as file:
                    pass
                        
                if info["extends"] == "AlgExpression":
                    create_AlgExpr_heir(cl, file_path, file_path2)
                elif info["extends"] == "AbstractMachine":
                    create_AbstMachine_heir(cl, file_path, file_path2)
                else: 
                    continue

                print_diff([], file_path)
                print_diff([], file_path2)

# получить часть файла от begin до end_mark
def get_content(file_path, begin, end_mark="}"):
    with open(file_path, "r", encoding="utf-8") as file:
        file_content = file.read()
    insert_index = file_content.find(begin)
    if insert_index == -1:
        print("not found " + begin)
        return
    brace_index = file_content.find(end_mark, insert_index)

    return (
        file_content[:insert_index],
        file_content[insert_index:brace_index],
        file_content[brace_index:],
    )

# получить часть файла от begin + { блок между скобками }
def get_content_in_brackets(file_path, begin):
    with open(file_path, "r", encoding="utf-8") as file:
        file_content = file.read()
    insert_index = file_content.find(begin)
    insert_index = file_content.find('{', insert_index)
    if insert_index == -1:
        print("not found " + begin)
        return
    i = insert_index
    count = 1
    for s in file_content[insert_index+1:]:
        count += 1 if s == '{' else -1 if s == '}' else 0
        i+=1
        if count == 0:
            break

    return (
        file_content[:insert_index],
        file_content[insert_index:i],
        file_content[i:],
    )

def add_to_includes(file_path):
    insert_place = "#include \"Objects"
    file_begin, placeholder, file_end = get_content(
        file_path, insert_place, end_mark="\n\n"
    )
    for c, info in data["classes"].items():
        include_str = f'#include \"Objects/{info["file"]}.h\"'
        if include_str not in placeholder:
            placeholder += '\n' + include_str

    with open(file_path, "w", encoding="utf-8") as file:
        file.write(file_begin + placeholder + file_end)

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

def generate_map_children():
    map_str = "inline static const std::unordered_map<ObjectType, std::vector<ObjectType>> types_children = {\n"
    for t in data["types"]:
        try:
            children = list(nx.descendants(typesGraph, t))
            if len(children) > 0:
                childs_str = [f"ObjectType::{type}" for type in children]
                map_str += f"\t{{ObjectType::{t}, {{{', '.join(childs_str)}}}}},\n"
        except:
            pass
    map_str += "};\n"
    return map_str

def generate_map_parents():
    map_str = "inline static const std::unordered_map<ObjectType, std::vector<ObjectType>> types_parents = {\n"
    for t in data["types"]:
        try:
            children = list(nx.ancestors(typesGraph, t))
            if len(children) > 0:
                childs_str = [f"ObjectType::{type}" for type in children]
                map_str += f"\t{{ObjectType::{t}, {{{', '.join(childs_str)}}}}},\n"
        except:
            pass
    map_str += "};\n"
    return map_str

def add_to_typization():
    typization_path = data["chipollino_path"] + "/libs/FuncLib/include/FuncLib/Typization.h"

    with open(typization_path, "r", encoding="utf-8") as file:
        prev_lines = file.readlines()

    add_to_includes(typization_path)
    add_to_includes(data["chipollino_path"] + "/libs/Interpreter/include/Interpreter/Interpreter.h")
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
    rewrite_in_file(
        file_path=typization_path,
        insert_place="types_children",
        new_text=generate_map_children(),
        is_logged = False
    )
    rewrite_in_file(
        file_path=typization_path,
        insert_place="types_parents",
        new_text=generate_map_parents(),
        is_logged = False
    )

    print_diff(prev_lines, typization_path)
    

def add_to_tex_types(file_path):
    insert_place = "% типы интерпретатора"
    file_begin, placeholder, file_end = get_content(
        file_path, insert_place, end_mark="\def\TypeIs"
    )
    for type, info in data["types"].items():
        if "\\def\\" + type not in placeholder and info != None:
            placeholder += f"\\def\\{type}TYPE{{\\mathtt{{{type}}}}}\n"

    with open(file_path, "w", encoding="utf-8") as file:
        file.write(file_begin + placeholder + file_end)

def add_to_tex_func_names(file_path):
    insert_place = "% названия операций"
    file_begin, placeholder, file_end = get_content(
        file_path, insert_place, end_mark="\n% типы интерпретатора"
    )
    for f in data["functions"]:
        if "\\def\\" + f["name"] not in placeholder and f["need_template"]:
            placeholder += f"\\def\\{f['name']}{{\\mathtt{{{f['name']}}}}}\n"

    with open(file_path, "w", encoding="utf-8") as file:
        file.write(file_begin + placeholder + file_end)

def add_to_tex_head():
    tex_head_path = data["chipollino_path"] + "/resources/template/head.tex"
    with open(tex_head_path, "r", encoding="utf-8") as file:
        prev_lines = file.readlines()

    add_to_tex_func_names(tex_head_path)
    add_to_tex_types(tex_head_path)
    print_diff(prev_lines, tex_head_path)


def add_readme_types(file_path):
    insert_place = "Интерпретатор поддерживает следующие типы:"
    file_begin, placeholder, file_end = get_content(file_path, insert_place, end_mark="\n### Синтаксические конструкции")
    for type, info in data["types"].items():
        if type not in placeholder and info != None:
            placeholder += f"* {type}\n"

    with open(file_path, "w", encoding="utf-8") as file:
        file.write(file_begin + placeholder + file_end)

def add_readme_funcs(file_path):
    def create_func_readme(f):
        if len(f["arguments"]) == 1:
            return f"- `{f['name']}: {f['arguments'][0]} -> {f['return_type']}`"
        return f"- `{f['name']}: ({', '.join(f['arguments'])}) -> {f['return_type']}`"
    insert_place = "Функции преобразователя"
    file_begin, placeholder, file_end = get_content(
        file_path, insert_place, end_mark="\n**Метод Test**"
    )
    for f in data["functions"]:
        if create_func_readme(f) not in placeholder:
            placeholder += create_func_readme(f) + "\n"

    with open(file_path, "w", encoding="utf-8") as file:
        file.write(file_begin + placeholder + file_end)

    
def add_to_readme():
    readme_path = data["chipollino_path"] + "/README.md"
    with open(readme_path, "r", encoding="utf-8") as file:
        prev_lines = file.readlines()
    add_readme_types(readme_path)
    add_readme_funcs(readme_path)
    print_diff(prev_lines, readme_path)


# Создаем экземпляр класса MorphAnalyzer
morph = pymorphy2.MorphAnalyzer()

def add_placeholder(array, elem):
    array.append(elem)
    return elem

def generate_template(f, placeholders = []):
    file_content = f"\\section{{{f['name']}}}\n"
    file_content += f"\\begin{{frame}}{{$\\{f['name']}\\TypeIs"
    # хз что делать если аргументов > 2
    if len(f["arguments"]) == 1:
        file_content += f"\\{f['arguments'][0]}TYPE"
    else:
        file_content += f"\\pair{{\\{f['arguments'][0]}TYPE}}{{\\{f['arguments'][1]}TYPE}}"
    file_content += f"\\to\\{f['return_type']}TYPE$}}\n"
    # генерация аргументов:
    if len(f["arguments"]) == 1:
        type = data["types"][f["arguments"][0]]
        file_content += f"\t{type['ru_str'].capitalize()}"
        if type["class"] == data["types"][f["return_type"]]["class"]:
            file_content += " до преобразования:\n"
            file_content += f"\t%template_{add_placeholder(placeholders, 'old'+f['arguments'][0].lower())}\n\n"
        else:
            file_content += ":\n"
            file_content += f"\t%template_{add_placeholder(placeholders, f['arguments'][0].lower())}\n\n"
    elif len(f["arguments"]) == 2 and data["types"][f["arguments"][0]]["class"] == data["types"][f["arguments"][1]]["class"]:
        type1 = data["types"][f["arguments"][0]]
        # Склоняем прилагательное по роду
        arg1_ru_str = morph.parse("первый")[0].inflect({morph.parse(type1["ru_str"])[0].tag.gender}).word + " " + type1["ru_str"]
        file_content += f"\t{arg1_ru_str.capitalize()}:\n"
        file_content += f"\t%template_{add_placeholder(placeholders, f['arguments'][0].lower() + '1')}\n\n"
        type2 = data["types"][f["arguments"][1]]
        arg2_ru_str = morph.parse("вторая")[0].inflect({morph.parse(type2["ru_str"])[0].tag.gender}).word + " " + type2["ru_str"]
        file_content += f"\t{arg2_ru_str.capitalize()}:\n"
        file_content += f"\t%template_{add_placeholder(placeholders, f['arguments'][1].lower() + '2')}\n\n"
    else:
        for i in range(len(f["arguments"])):
            file_content += f"\t%template_{add_placeholder(placeholders, f['arguments'][i].lower() + str(i+1))}\n\n"

    # генерация результата        
    if len(f["arguments"]) == 1 and data["types"][f["arguments"][0]]["class"] == data["types"][f["return_type"]]["class"]:
        file_content += f"\t{data['types'][f['return_type']]['ru_str'].capitalize()} после преобразования:\n"
    else:
        file_content += f"\tРезультат:\n"
    file_content += f"\t%template_{add_placeholder(placeholders, 'result')}\n\n"
    file_content += "\\end{frame}"
    return file_content

def generate_templates():
    for f in data["functions"]:
        file_path = data["chipollino_path"] + f'/resources/template/{f["template_name"]}.tex'
        if not os.path.exists(file_path) and f["need_template"]:
            # создание файла
            with open(file_path, "w", encoding="utf-8") as file:
                prev_lines = []
                
            file_content = generate_template(f)

            with open(file_path, "w", encoding="utf-8") as file:
                file.write(file_content)
            print_diff(prev_lines, file_path)

def generate_logs(f):
    logs_str = '\tif (log) {\n'
    placeholders = []
    generate_template(f, placeholders)
    for i, p in enumerate(placeholders, 1):
        logs_str += f'\t\tlog->set_parameter(\"{p}\", {"res" if i == len(placeholders) else "*this"});\n'
    logs_str += '\t}\n'
    return logs_str

def add_to_classes():
    for c, info in data["classes"].items():
        file_path = f'{data["chipollino_path"]}/libs/Objects/include/Objects/{info["file"]}.h'
        file_path2 = f'{data["chipollino_path"]}/libs/Objects/src/{info["file"]}.cpp'
        with open(file_path, "r", encoding="utf-8") as file:
            prev_lines = file.readlines()
        with open(file_path2, "r", encoding="utf-8") as file:
            prev_lines2 = file.readlines()

        insert_place = "class " + c
        file_begin, placeholder, file_end = get_content_in_brackets(
            file_path, insert_place)
        for f in data["functions"]:
            if data["types"][f["arguments"][0]]["class"] == c and f["prog_name"] != None and f["prog_name"] not in placeholder:
                func_str = f'\n\n{data["types"][f["return_type"]]["class"]} {c}::{f["prog_name"]}('
                placeholder += f'\t{data["types"][f["return_type"]]["class"]} {f["prog_name"]}('
                for i, arg in enumerate(f["arguments"][1:], 1):
                    placeholder += f'const {data["types"][arg]["class"]}&, '
                    func_str += f'const {data["types"][arg]["class"]}& a{i}, '
                placeholder += 'iLogTemplate* log = nullptr) const;\n'
                func_str += 'iLogTemplate* log) const {\n'
                func_str += generate_logs()
                func_str += '\treturn res;\n}'

                with open(file_path2, "a", encoding="utf-8") as file:
                    file.write(func_str)


        with open(file_path, "w", encoding="utf-8") as file:
            file.write(file_begin + placeholder + file_end)
        
        print_diff(prev_lines, file_path)
        print_diff(prev_lines2, file_path2)

def generate_fast_logs(funcs):
    for f in data["functions"]:
        if f["name"] in funcs:
            print(f["name"]+":")
            print(generate_logs(f))

def main():
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
    # head.tex
    add_to_tex_head()
    # *class*.h и *.cpp
    add_to_classes()

main()

# воспользуйтесь этим, чтобы вставить в свою функцию в бэке
generate_fast_logs(["ToMFA"])