import numpy as np
# import struct
from dataclasses import dataclass, field
from enum import Enum
import os
import sys
import stat

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
    PREPARE_NEGATIVE_ID = 1
    PREPARE_STRING_TOO_LONG = 2
    PREPARE_SYNTAX_ERROR = 3
    PREPARE_UNRECOGNIZED_STATEMENT = 4

class StatementType(Enum):
    STATEMENT_INSERT = 0
    STATEMENT_SELECT = 1

COLUMN_USERNAME_SIZE = 32
COLUMN_EMAIL_SIZE = 255

@dataclass
class Row:
    id: int = 0
    username: str = " " * COLUMN_USERNAME_SIZE
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
# ROWS_PER_PAGE = int(PAGE_SIZE / ROW_SIZE)
# TABLE_MAX_ROWS = ROWS_PER_PAGE * TABLE_MAX_PAGES 

@dataclass
class Pager:
    file_descriptor: int = 0
    file_length: int = 0
    num_pages: int = 0
    pages: list = field(default_factory=lambda: [None] * TABLE_MAX_PAGES)

@dataclass
class Table:
    pager: Pager
    root_page_num: int = 0

@dataclass
class Cursor:
    table: Table
    end_of_table: bool # Indicates a position one past the last element
    page_num: int = 0
    cell_num: int = 0

class NodeType(Enum):
    NODE_INTERNAL = 0
    NODE_LEAF = 1

# Common Node Header Layout

NODE_TYPE_SIZE = sys.sizeof(np.uint8)
NODE_TYPE_OFFSET = 0
IS_ROOT_SIZE = sys.syzeof(np.uint8)
IS_ROOT_OFFSET = NODE_TYPE_SIZE
PARENT_POINTER_SIZE = sys.sizeof(np.uint32)
PARENT_POINTER_OFFSET = IS_ROOT_OFFSET + IS_ROOT_SIZE
COMMON_NODE_HEADER_SIZE = NODE_TYPE_SIZE + IS_ROOT_SIZE + PARENT_POINTER_SIZE

# Leaf Node Header Layout

LEAF_NODE_NUM_CELLS_SIZE = sys.sizeof(np.uint32)
LEAF_NODE_NUM_CELLS_OFFSET = COMMON_NODE_HEADER_SIZE
LEAF_NODE_HEADER_SIZE = COMMON_NODE_HEADER_SIZE + LEAF_NODE_NUM_CELLS_SIZE

# Leaf Node Body Layout

LEAF_NODE_KEY_SIZE = sys.sizeof(np.uint32)
LEAF_NODE_KEY_OFFSET = 0
LEAF_NODE_KEY_VALUE_SIZE = ROW_SIZE
LEAF_NODE_VALUE_OFFSET = LEAF_NODE_KEY_OFFSET + LEAF_NODE_KEY_SIZE
LEAF_NODE_CELL_SIZE = LEAF_NODE_KEY_SIZE + LEAF_NODE_VALUE_SIZE
LEAF_NODE_SPACE_FOR_CELLS = PAGE_SIZE - LEAF_NODE_HEADER_SIZE
LEAF_NODE_MAX_CELLS = LEAF_NODE_SPACE_FOR_CELLS / LEAF_NODE_CELL_SIZE

def leaf_node_num_cells(node: int) -> list:
    return node[LEAF_NODE_NUM_CELLS_OFFSET]

def leaf_node_cell(node: int, cell_num: int) -> list:
    return node[LEAF_NODE_HEADER_SIZE : cell_num * LEAF_NODE_CELL_SIZE]

def leaf_node_key(node: int, cell_num: int) -> list:
    return leaf_node_cell(node, cell_num)

def leaf_node_value(node: int, cell_num: int) -> list:
    cell = leaf_node_cell(node, cell_num)
    return cell[LEAF_NODE_KEY_SIZE]

def print_leaf_node(node: int) -> None:
    num_cells = leaf_node_num_cells(node)
    print(f"leaf (size {num_cells})")
    for i in range(num_cells):
        key = leaf_node_key(node, i)
        print(f"  - {i} : {key}")

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

def initialize_leaf_node(node: int) -> None:
    leaf_node_num_cells(node) = 0

def get_page(pager: Pager, page_num: int) -> list:
    if page_num > TABLE_MAX_PAGES:
        print("Tried to fetch page number out of bounds. {page_num} > {TABLE_MAX_PAGES}")
        exit() # Not sure if to keep this here.

    if pager.pages[page_num] is None:
        # Cache miss. Allocate memory and load from file.
        page = np.zeros(PAGE_SIZE, dtype=np.uint8)
        num_pages = pager.file_length / PAGE_SIZE

        # We might save a partial page at the end of the file.
        if pager.file_length % PAGE_SIZE:
            num_pages += 1

        if page_num <= num_pages:
            os.lseek(pager.file_descriptor, page_num * PAGE_SIZE, os.SEEK_SET)
            bytes_read = os.read(pager.file_descriptor, PAGE_SIZE)

            if bytes_read == -1:
                print(f"Error reading file: {errno}")
                exit()
            else:
                page[:len(bytes_read)] = np.frombuffer(bytes_read, dtype=np.uint8)

        pager.pages[page_num] = page

        if page_num >= pager.num_pages:
            pager.num_pages = page_num + 1

    return pager.pages[page_num]

def table_start(table: Table, row_num: int) -> Table:
    root_node = get_page(table.pager, table.root_page_num)
    num_cells = leaf_node_num_cells(root_node)
    cursor = Cursor(table, (num_cells == 0), table.root_page_num, 0)
    return cursor

def table_end(table: Table) -> Cursor:
    root_node = get_page(table.pager, table.root_page_num)
    num_cells = leaf_node_num_cells(root_node)
    cursor = Cursor(table, True, table.root_page_num, num_cells)
    return cursor

def cursor_value(cursor: Cursor) -> int:
    page_num = cursor.page_num
    page = get_page(cursor.table.pager, page_num)

    return leaf_node_value(page, cursor.cell_num)
    # return page[byte_offset : byte_offset + ROW_SIZE]

def cursor_advance(cursor: Cursor) -> None:
    page_num = cursor.page_num
    node = get_page(cursor.table.pager, page_num)

    cursor.row_number += 1
    if cursor.cell_num >= leaf_node_num_cells(node):
        cursor.end_of_table = True

def pager_open(filename):
    fd = os.open(filename, os.O_RDWR | os.O_CREAT, stat.S_IWUSR | stat.S_IRUSR)

    if fd == -1:
        print("Unable to open file")
        exit()

    file_length = os.lseek(fd, 0, os.SEEK_END)

    pager = Pager()
    pager.file_descriptor = fd
    pager.file_length = file_length
    pager.num_pages = file_length / PAGE_SIZE

    if file_length % PAGE_SIZE != 0:
        print("Db file is not a whole number of pages. Corrupt file.")
        exit()

    for i in range(TABLE_MAX_PAGES):
        pager.pages[i] = None
    return pager

def free_table(table):
    for i in range(len(table.pages)):
        table.pages[i] = None
    table.pages.clear()
    table.num_rows = 0

def db_open(filename):
    pager = pager_open(filename)
    # num_rows = pager.file_length // ROW_SIZE

    table = Table(pager)
    table.pager = pager
    table.root_page_num = 0

    if pager.num_pages == 0:
        # New database file. Initialize page 0 as leaf node.
        root_node = get_page(pager, 0)
        initialize_leaf_node(root_node)

    return table

def new_input_buffer():
    return InputBuffer()

def print_promt():
    print("db > ", end="")

def read_input(input_buffer):
    bytes_read = input()

    if not sys.stdin.isatty():
        print(bytes_read)

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

def pager_flusher(pager: Pager, page_num: int) -> None:
    if pager.pages[page_num] is None:
        print("Tried to flush null page")
        exit()

    offset = os.lseek(pager.file_descriptor, page_num * PAGE_SIZE, os.SEEK_SET)

    if offset == -1:
        print(f"Error seeking: {page_num}")
        exit()

    bytes_to_write = pager.pages[page_num][:PAGE_SIZE].tobytes()
    bytes_written = os.write(pager.file_descriptor, bytes_to_write)

    if bytes_written == -1:
        print(f"Error writting: {page_num}")
        exit()

def db_close(table: Table) -> None:
    pager = table.pager
    # num_full_pages = table.num_rows // ROWS_PER_PAGE

    for i in range(pager.num_pages):
        if pager.pages[i] is None:
            continue
        pager_flusher(pager, i)
        pager.pages[i] = None

    # There may be a partial page to write to the end of the file
    # This should not be needed after we switch to a B-tree
    # num_additional_rows = table.num_rows % ROWS_PER_PAGE
    # if num_additional_rows > 0:
    #    page_num = num_full_pages
    #    if pager.pages[page_num] is not None:
    #        pager_flusher(pager, page_num, num_additional_rows * ROW_SIZE)

    #for i in range(TABLE_MAX_PAGES):
    #    page = pager.pages[i]
    #    if page is not None:
    #        pager.pages[i] = None

    result = pager.file_descriptor.close()
    if result == -1:
        print("Error closing db file.")

def do_meta_command(input_buffer: str, table: Table) -> MetaCommandResult:
    if input_buffer.buffer == ".exit":
        close_input_buffer(input_buffer)
        db_close(table)
        exit()
    elif input_buffer == ".btree":
        print("Tree:")
        print_leaf_node(get_page(table.pager, 0))
        return MetaCommandResult.META_COMMAND_SUCCESS
    elif input_buffer.buffer == ".constants":
        print("Constants:")
        print_constants()
        print_leaf_node(get_page(table.pager, 0))
    else:
        return MetaCommandResult.META_COMMAND_UNRECOGNIZED_COMMAND

def prepare_insert(input_buffer: str, statement: Statement) -> PrepareResult:
    statement.type = StatementType.STATEMENT_INSERT

    total = input_buffer.buffer.split()

    keyword = total[0]
    id_string = total[1]
    username = total[2]
    email = total[3]

    if id_string == None or username == None or email == None:
        return PrepareResult.PREPARE_SYNTAX_ERROR

    try:
        id = int(id_string)
    except ValueError:
        return PrepareResult.PREPARE_SYNTAX_ERROR

    if id < 0:
        return PrepareResult.PREPARE_NEGATIVE_ID

    if len(username) > COLUMN_USERNAME_SIZE:
        return PrepareResult.PREPARE_STRING_TOO_LONG

    if len(email) > COLUMN_EMAIL_SIZE:
        return PREPARE_STRING_TOO_LONG

    statement.row_to_insert.id = id
    statement.row_to_insert.username = username
    statement.row_to_insert.email = email

    return PrepareResult.PREPARE_SUCCESS

def prepare_statement(input_buffer: str, statement: Statement) -> PrepareResult:
    if input_buffer.buffer.split()[0] == "insert":
        return prepare_insert(input_buffer, statement)

    elif input_buffer.buffer.split()[0] == "select":
        statement.type = StatementType.STATEMENT_SELECT
        return PrepareResult.PREPARE_SUCCESS

    else:
        return PrepareResult.PREPARE_UNRECOGNIZED_STATEMENT

def leaf_node_insert(cursor: Cursor, ket: int, value: Row) ->None:
    node = get_page(cursor.table.pager, cursor.page_num)

    num_cells = leaf_node_num_cells(node)
    if num_cells >= LEAF_NODE_MAX_CELLS:
        # Node full
        print("Need to implement splitting a leaf node.")
        exit()

    if cursor.cell_new < num_cells:
        # Make room for new cell
        for i in range(num_cells, cursor.cell_num):
            ctypes.memmove(leaf_node_cell(node, i), leaf_node_cell(node, i - 1), LEAF_NODE_CELL_SIZE)

    cells = leaf_node_num_cells(node) += 1
    keys = leaf_node_key(node, cursor.cell_num)
    keys = key
    serialize_row(value, leaf_node_value(node, cursow.cell_num))

def execute_insert(statement: Statement, table: Table) -> ExecuteResult:
    node = get_page(table.pager, table.root_page_num)
    if leaf_node_num_cells(node) >= LEAF_NODE_MAX_CELLS:
        return ExecuteResult.EXECUTE_TABLE_FULL

    row_to_insert = statement.row_to_insert
    cursor = table_end(table)

    # serialize_row(row_to_insert, cursor_value(cursor))
    # table.num_rows += 1
    leaf_node_insert(cursor, row_to_insert.id, row_to_insert)

    return ExecuteResult.EXECUTE_SUCCESS

def execute_select(statement: Statement, table: Table) -> ExecuteResult:
    cursor = table_start(table, statement.row_to_insert)
    row = Row()
    while not cursor.end_of_table:
        deserialize_row(cursor_value(cursor), row)
        print_row(row)
        cursor_advance(cursor)

    return ExecuteResult.EXECUTE_SUCCESS

def execute_statement(statement: Statement, table: Table) -> ExecuteResult:
    match statement.type:
        case StatementType.STATEMENT_INSERT:
            return execute_insert(statement, table)
        case StatementType.STATEMENT_SELECT:
            return execute_select(statement, table)

def main(*args):
    filename = sys.argv[1]
    table = db_open(filename)

    input_buffer = new_input_buffer()
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
            case PrepareResult.PREPARE_NEGATIVE_ID:
                print("ID must be positive.")
                continue
            case PrepareResult.PREPARE_STRING_TOO_LONG:
                print("String is too long.")
                continue
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
