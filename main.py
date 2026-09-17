import numpy as np
import struct
from dataclasses import dataclass, field
from enum import Enum

#InputBuffer = "cNn"

@dataclass
class InputBuffer:
    buffer: str = ""
    buffer_length: int = 0
    input_length: int = 0

class ExecuteResult(Enum):
    EXECUTE_SUCCESS = 0
    EXECUTE_TABLE_FULL = 1

class MetaCommandResult(Enum):
    META_COMMAND_SUCCESS = 0
    META_COMMAND_UNRECOGNIZED_COMMAND = 1

class PrepareResult(Enum):
    PREPARE_SUCCESS = 0
    PREPARE_SYNTAX_ERROR = 1
    PREPARE_UNRECOGNIZED_STATEMENT = 2

class StatementType(Enum):
    STATEMENT_INSERT = 0
    STATEMENT_SELECT = 1

COLUMN_USER_NAME = 32
COLUMN_EMAIL_SIZE = 255

@dataclass
class Row:
    id: int = 0
    username: str = " " * COLUMN_USER_NAME
    email: str = " " * COLUMN_EMAIL_SIZE

@dataclass
class Statement:
    type: StatementType | None = None
    row_to_insert: Row = field(default_factory=Row) # Only used by insert statement.

def size_of_attribute(struct, attribute):
    attr = getattr(struct, attribute)
    if not isinstance(attr, int):
        attr = len(attr)
    return attr

#ID_SIZE = size_of_attribute(Row, "id")
ID_SIZE = 4
USERNAME_SIZE = size_of_attribute(Row, "username")
EMAIL_SIZE = size_of_attribute(Row, "email")
ID_OFFSET = 0
USERNAME_OFFSET = ID_OFFSET + ID_SIZE
EMAIL_OFFSET = USERNAME_OFFSET + USERNAME_SIZE
ROW_SIZE = ID_SIZE + USERNAME_SIZE + EMAIL_SIZE

PAGE_SIZE = 4096
TABLE_MAX_PAGES = 100
ROWS_PER_PAGE = int(PAGE_SIZE / ROW_SIZE)
TABLE_MAX_ROWS = ROWS_PER_PAGE * TABLE_MAX_PAGES 

@dataclass
class Table:
    num_rows: int = 0
    pages: list = field(default_factory=lambda: [None] * TABLE_MAX_PAGES)

def print_row(row):
    print(f"{row.id}, {row.username}, {row.email}")

def serialize_row(source, destination): # We can use struct in the future.
    id_bytes = source.id.to_bytes(ID_SIZE, byteorder='little')
    username_bytes = source.username.encode('ascii').ljust(USERNAME_SIZE, b'\x00')
    email_bytes = source.email.encode('ascii').ljust(EMAIL_SIZE, b'\x00')

    destination[ID_OFFSET : ID_OFFSET + ID_SIZE] = np.frombuffer(id_bytes, dtype=np.uint8)
    destination[USERNAME_OFFSET : USERNAME_OFFSET + USERNAME_SIZE] = np.frombuffer(username_bytes, dtype=np.uint8)
    destination[EMAIL_OFFSET : EMAIL_OFFSET + EMAIL_SIZE] = np.frombuffer(email_bytes, dtype=np.uint8)

def deserialize_row(source, destination): # We can use struct in the future.
    id_bytes = source[ID_OFFSET : ID_OFFSET + ID_SIZE].tobytes()
    username_bytes = source[USERNAME_OFFSET : USERNAME_OFFSET + USERNAME_SIZE].tobytes()
    email_bytes = source[EMAIL_OFFSET : EMAIL_OFFSET + EMAIL_SIZE].tobytes()

    destination.id = int.from_bytes(id_bytes, byteorder='little')
    destination.username = username_bytes.decode('ascii').rstrip('\x00')
    destination.email = email_bytes.decode('ascii').rstrip('\x00')

def row_slot(table, row_num):
    page_num = int(row_num / ROWS_PER_PAGE)
    if isinstance(table.pages[page_num], int) and table.pages[page_num] == 0:
        table.pages[page_num] = np.zeros(PAGE_SIZE, dtype=np.uint8) # Only "allocate" memory when we try to access page.

    page = table.pages[page_num]

    row_offset = row_num % ROWS_PER_PAGE
    byte_offset = row_offset * ROW_SIZE
    return page[byte_offset : byte_offset + ROW_SIZE]

def new_table():
    table = Table()
    table.num_rows = 0
    for i in range(TABLE_MAX_PAGES):
        table.pages[i] = 0
    return table

def free_table(table):
    for i in range(len(table.pages)):
        table.pages[i] = None
    table.pages.clear()
    table.num_rows = 0

def new_input_buffer():
    return InputBuffer()

def print_promt():
    print("db > ", end="")

def read_input(input_buffer):
    bytes_read = input()

    input_buffer.buffer = bytes_read
    #input_buffer.buffer[-1] = 0
    input_buffer.buffer_length = len(bytes_read) - 1
    input_buffer.input_length = len(bytes_read)

    if len(bytes_read) <= 0:
        print("Error reading input")

    return bytes_read

def close_input_buffer(input_buffer):
    input_buffer.buffer = ""
    input_buffer.buffer_length = 0
    input_buffer.input_length = 0

def do_meta_command(input_buffer, table):
    if input_buffer.buffer == ".exit":
        close_input_buffer(input_buffer)
        free_table(table)
        exit()
    else:
        return MetaCommandResult.META_COMMAND_UNRECOGNIZED_COMMAND

def prepare_statement(input_buffer, statement):
    if input_buffer.buffer.split()[0] == "insert":
        statement.type = StatementType.STATEMENT_INSERT
        try:
            statement.row_to_insert.id = int(input_buffer.buffer.split()[1])
        except ValueError:
            return PrepareResult.PREPARE_SYNTAX_ERROR
        statement.row_to_insert.username = input_buffer.buffer.split()[2]
        statement.row_to_insert.email = input_buffer.buffer.split()[3]
        input_buffer.buffer = f"insert {statement.row_to_insert.id} {statement.row_to_insert.username} {statement.row_to_insert.email}"
        args_assigned = [statement.row_to_insert.id, statement.row_to_insert.username, statement.row_to_insert.email]
        if len(args_assigned) < 3:
            return PrepareResult.PREPARE_SYNTAX_ERROR
        return PrepareResult.PREPARE_SUCCESS

    elif input_buffer.buffer.split()[0] == "select":
        statement.type = StatementType.STATEMENT_SELECT
        return PrepareResult.PREPARE_SUCCESS

    else:
        return PrepareResult.PREPARE_UNRECOGNIZED_STATEMENT

def execute_insert(statement, table):
    if table.num_rows >= TABLE_MAX_ROWS:
        return ExecuteResult.EXECUTE_TABLE_FULL

    row_to_insert = statement.row_to_insert

    serialize_row(row_to_insert, row_slot(table, table.num_rows))
    table.num_rows += 1

    return ExecuteResult.EXECUTE_SUCCESS

def execute_select(statement, table):
    row = Row()
    for i in range(table.num_rows):
        deserialize_row(row_slot(table, i), row)
        print_row(row)
    return ExecuteResult.EXECUTE_SUCCESS

def execute_statement(statement, table):
    match statement.type:
        case StatementType.STATEMENT_INSERT:
            return execute_insert(statement, table)
        case StatementType.STATEMENT_SELECT:
            return execute_select(statement, table)

def main(*args):
    input_buffer = new_input_buffer()
    table = new_table()
    while True:
        print_promt()
        read_input(input_buffer)

        if input_buffer.buffer[0] == ".":
            match do_meta_command(input_buffer, table):
                case MetaCommandResult.META_COMMAND_SUCCESS:
                    continue
                case MetaCommandResult.META_COMMAND_UNRECOGNIZED_COMMAND:
                    print(f"Unrecognized command '{input_buffer.buffer}'")
                    continue

        statement = Statement()
        match prepare_statement(input_buffer, statement):
            case PrepareResult.PREPARE_SUCCESS:
                pass
            case PrepareResult.PREPARE_SYNTAX_ERROR:
                print("Syntax error. Could not parse statement.")
                continue
            case PrepareResult.PREPARE_UNRECOGNIZED_STATEMENT:
                print(f"Unrecognized keyword at start of '{input_buffer.buffer}'.")
                continue

        state = execute_statement(statement, table)
        match state: # execute_statemnt(statement, table):
            case ExecuteResult.EXECUTE_SUCCESS:
                print("Executed.")
                continue
            case ExecuteResult.EXECUTE_TABLE_FULL:
                print("Error: Table full.")
                continue

if __name__ == "__main__":
    main()
