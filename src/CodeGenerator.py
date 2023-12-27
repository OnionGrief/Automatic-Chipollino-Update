import yaml

# генерация cpp кода вектора функций интерпретатора
def generate_funcs_vector():
    with open("funcs.yaml", "r") as file:
        data = yaml.safe_load(file)
    funcs_vector = "inline static const std::vector<Function> functions = {\n"
    for func in data["functions"]:
        input = [f"ObjectType::{type}" for type in func["arguments"]]
        funcs_vector += f'\t{{"{func["name"]}", {{{", ".join(input)}}}, ObjectType::{func["return_type"]}}},\n'
    funcs_vector += "};\n"
    return funcs_vector

def write_to_file(file_path, insert_place, new_text):
    with open(file_path, "r", encoding='utf-8') as file:
        lines = file.readlines()

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

    with open(file_path, "w", encoding='utf-8') as file:
        file.writelines(lines)

write_to_file(
    file_path="../Chipollino/libs/FuncLib/include/FuncLib/Functions.h",
    insert_place="vector<Function> functions",
    new_text=generate_funcs_vector(),
)