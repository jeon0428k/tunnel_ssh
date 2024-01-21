from javalang.tree import MemberReference, ElementValuePair
from sqlalchemy import create_engine, Column, Integer, String, inspect, ForeignKey
from sqlalchemy.orm import sessionmaker, declarative_base, relationship
from enum import Enum

import javalang
import glob
import os

SRC_ROOT_DIR = r"E:\workspace\get-in-line\src\main\java"
FILE_DIR = r"E:\workspace\get-in-line\src\main\java\com\uno\getinline"
FILE_LIST = [
    # r'E:\workspace\get-in-line\src\main\java\com\uno\getinline\service\EventService.java',
    r'E:\workspace\get-in-line\src\main\java\com\uno\getinline\controller\AdminController.java',
]
# FILE_LIST = []
EXECUTE_FILES = ["Controller", "Service"]
# EXECUTE_FILES = []

Base = declarative_base()

engine = create_engine("mysql+pymysql://root:5402@localhost:3306/ZDB")

Session = sessionmaker(bind=engine)
session = Session()


class T_M(Base):
    __tablename__ = 'mbt'
    ID = Column(Integer, primary_key=True, autoincrement=True)
    PACKAGE = Column(String(200))
    CLASS = Column(String(50))
    METHOD = Column(String(50))
    PARAM = Column(String(500))
    RETURN = Column(String(100))
    API = Column(String(200))


class T_R(Base):
    __tablename__ = 'mbt_r'
    ID = Column(Integer, primary_key=True, autoincrement=True)
    T_M_ID = Column(Integer, ForeignKey('mbt.ID'))
    PACKAGE = Column(String(200))
    CLASS = Column(String(50))
    METHOD = Column(String(50))
    PARAM = Column(String(500))
    CALL = Column(String(50))
    T_M = relationship("T_M")


if inspect(engine).has_table(T_R.__tablename__):
    T_R.__table__.drop(engine)
if inspect(engine).has_table(T_M.__tablename__):
    T_M.__table__.drop(engine)

Base.metadata.create_all(engine)


class CallType(Enum):
    INNER = "INNER"
    NORMAL = "NORMAL"
    ASYNC = "ASYNC"


def get_expression_string(expression):
    if isinstance(expression, javalang.tree.MethodInvocation):
        return f"{expression.qualifier}.{expression.member}()"
    elif isinstance(expression, javalang.tree.MemberReference):
        return expression.member
    elif isinstance(expression, javalang.tree.Literal):
        return str(expression.value)
    else:
        return str(expression)


def get_annotation_recurve(element):
    if element is None:
        return ""
    elif isinstance(element, list):
        for _element in element:
            return get_annotation_recurve(_element)
    elif isinstance(element, ElementValuePair):
        return get_annotation_recurve(element.value)
    elif isinstance(element, MemberReference):
        return element.member
    elif isinstance(element, javalang.tree.Literal):
        return element.value.strip('\"')
    else:
        return element.value.value.strip('\"')


def get_api_annotation_value(annotations):
    result = ""
    try:
        for annotation in annotations:
            if "Mapping" in annotation.name:
                result = get_annotation_recurve(annotation.element)
    except Exception as ex:
        print(ex)
        result = ""
    return result


def get_field_types(fields, import_paths):
    result = {}
    for field in fields:
        field_name = field.declarators[0].name
        field_type = field.type.name
        for import_path in import_paths:
            if import_path.endswith(field_type):
                result[field_name] = import_path
                break
        else:
            result[field_name] = field_type
    return result


def is_async_call(invocation):
    return invocation.member == 'execute' and invocation.qualifier == 'executorService'


def analysis(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    tree = javalang.parse.parse(content)

    package_name = None
    for path, node in tree.filter(javalang.tree.PackageDeclaration):
        package_name = node.name

    masters = []
    calls = []
    for path, node in tree.filter(javalang.tree.ClassDeclaration):
        class_name = node.name
        class_api = get_api_annotation_value(node.annotations)

        import_paths = [import_decl.path for import_decl in tree.imports]
        method_names = [method.name for method in node.methods]
        field_names = [field.declarators[0].name for field in node.fields]
        field_types = get_field_types(node.fields, import_paths)

        for method in node.methods:
            method_name = method.name
            method_api = class_api + get_api_annotation_value(method.annotations)

            method_params = ', '.join([f"{param.type.name} {param.name}" for param in method.parameters])
            method_return = method.return_type.name if method.return_type else None

            master = T_M(PACKAGE=package_name, CLASS=class_name, METHOD=method_name, PARAM=method_params, RETURN=method_return, API=method_api)
            masters.append(master)

            async_calls = []
            for path, invocation in method.filter(javalang.tree.MethodInvocation):
                if invocation.qualifier == 'executorService' and invocation.member == 'execute':
                    print('tt')
                    if invocation.qualifier in field_names:
                        call_pacakge, call_class_name = field_types[invocation.qualifier].rsplit(".", 1)
                        call_method_name = {invocation.member}
                        call_method_params = ', '.join([get_expression_string(arg) for arg in invocation.arguments])
                        calls.append(T_R(PACKAGE=call_pacakge, CLASS=call_class_name, METHOD=call_method_name, PARAM=call_method_params, CALL=CallType.NORMAL.value, T_M=master))
                    elif (invocation.qualifier == "this" or invocation.qualifier == "" or invocation.qualifier is None) and invocation.member in method_names:
                        call_pacakge, call_class_name = package_name, class_name
                        call_method_name = {invocation.member}
                        call_method_params = ', '.join([get_expression_string(arg) for arg in invocation.arguments])
                        calls.append(T_R(PACKAGE=call_pacakge, CLASS=call_class_name, METHOD=call_method_name, PARAM=call_method_params, CALL=CallType.INNER.value, T_M=master))
                else:
                    if invocation.qualifier in field_names:
                        call_pacakge, call_class_name = field_types[invocation.qualifier].rsplit(".", 1)
                        call_method_name = {invocation.member}
                        call_method_params = ', '.join([get_expression_string(arg) for arg in invocation.arguments])
                        calls.append(T_R(PACKAGE=call_pacakge, CLASS=call_class_name, METHOD=call_method_name, PARAM=call_method_params, CALL=CallType.NORMAL.value, T_M=master))
                    elif (invocation.qualifier == "this" or invocation.qualifier == "" or invocation.qualifier is None) and invocation.member in method_names:
                        call_pacakge, call_class_name = package_name, class_name
                        call_method_name = {invocation.member}
                        call_method_params = ', '.join([get_expression_string(arg) for arg in invocation.arguments])
                        calls.append(T_R(PACKAGE=call_pacakge, CLASS=call_class_name, METHOD=call_method_name, PARAM=call_method_params, CALL=CallType.INNER.value, T_M=master))

    if len(masters) > 0:
        session.add_all(masters)
        if len(calls) > 0:
            session.add_all(calls)
        session.commit()

def is_exists_class_file(call_package, call_class_name):
    call_package = call_package.replace('.', os.sep)
    target_path = os.path.join(SRC_ROOT_DIR, call_package, f'{call_class_name}.java')

    file_exists = os.path.exists(target_path)
    print(f'File exists: {file_exists}, {call_package}.{call_class_name}, {target_path}')


def get_parse_constant_java(file_path):
    with open(file_path, 'r') as java_file:
        java_code = java_file.read()

    tree = javalang.parse.parse(java_code)

    package_name = None
    for path, node in tree.filter(javalang.tree.PackageDeclaration):
        package_name = node.name

    field_values = {}
    for path, node in tree.filter(javalang.tree.ClassDeclaration):
        class_name = node.name
        if node.name == 'Custom':
            for field in node.fields:
                for declarator in field.declarators:
                    if isinstance(declarator.initializer, javalang.tree.Literal):
                        field_values[declarator.name] = declarator.initializer.value.strip('"')
                    elif isinstance(declarator.initializer, javalang.tree.BinaryOperation):
                        left = field_values[declarator.initializer.operandl.member] if isinstance(declarator.initializer.operandl, javalang.tree.MemberReference) else declarator.initializer.operandl.value.strip('"')
                        right = field_values[declarator.initializer.operandr.member] if isinstance(declarator.initializer.operandr, javalang.tree.MemberReference) else declarator.initializer.operandr.value.strip('"')
                        field_values[declarator.name] = left + right

    for field, value in field_values.items():
        print(f"{package_name}.{class_name}.{field} : {value}")


get_parse_constant_java(r'E:\workspace\get-in-line\src\main\java\com\test\constants\Custom.java')
for file_path in glob.glob(os.path.join(FILE_DIR, '**', '*.java'), recursive=True) if len(FILE_LIST) == 0 else FILE_LIST:
    try:
        if len(EXECUTE_FILES) == 0:
            print(file_path)
            analysis(file_path)
        else:
            for execute_file in EXECUTE_FILES:
                if execute_file in file_path:
                    print(file_path)
                    analysis(file_path)
    except Exception as ex:
        print(f"(error) {ex.description}, {file_path}")
        print(ex)
