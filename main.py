import numpy as np
# import struct
from dataclasses import dataclass, field
from enum import Enum
import os
import sys
import stat
from typing import Any

#InputBuffer = "cNn"

@dataclass
class InputBuffer:
    buffer: str = ""
    buffer_length: int = 0
    input_length: int = 0

class ExecuteResult(Enum):
    EXECUTE_SUCCESS = 0
    EXECUTE_DUPLICATE_KEY = 1
    EXECUTE_TABLE_FULL = 2

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

# NODE_TYPE_SIZE = sys.getsizeof(np.uint8)
NODE_TYPE_SIZE = 1
NODE_TYPE_OFFSET = 0
# IS_ROOT_SIZE = sys.getsizeof(np.uint8)
IS_ROOT_SIZE = 1
IS_ROOT_OFFSET = NODE_TYPE_SIZE
# PARENT_POINTER_SIZE = sys.getsizeof(np.uint32)
PARENT_POINTER_SIZE = 4
PARENT_POINTER_OFFSET = IS_ROOT_OFFSET + IS_ROOT_SIZE
COMMON_NODE_HEADER_SIZE = np.uint32(NODE_TYPE_SIZE + IS_ROOT_SIZE + PARENT_POINTER_SIZE)

# Internal Node Header Layout
INTERNAL_NODE_NUM_KEYS_SIZE = np.uint32(4)
INTERNAL_NODE_NUM_KEYS_OFFSET = COMMON_NODE_HEADER_SIZE
INTERNAL_NODE_RIGHT_CHILD_SIZE = np.uint32(4)
INTERNAL_NODE_RIGHT_CHILD_OFFSET = INTERNAL_NODE_NUM_KEYS_OFFSET + INTERNAL_NODE_NUM_KEYS_SIZE
INTERNAL_NODE_HEADER_SIZE = COMMON_NODE_HEADER_SIZE + INTERNAL_NODE_NUM_KEYS_SIZE + INTERNAL_NODE_RIGHT_CHILD_SIZE

# Internal Node Body Layout
INTERNAL_NODE_KEY_SIZE = np.uint32(4)
INTERNAL_NODE_CHILD_SIZE = np.uint32(4)
INTERNAL_NODE_CELL_SIZE = INTERNAL_NODE_CHILD_SIZE + INTERNAL_NODE_KEY_SIZE
# INTERNAL_NODE_MAX_CELLS = np.uint32(3)
INTERNAL_NODE_MAX_CELLS = np.uint32(3)

# Leaf Node Header Layout

# LEAF_NODE_NUM_CELLS_SIZE = sys.getsizeof(np.uint32)
LEAF_NODE_NUM_CELLS_SIZE = 4
LEAF_NODE_NUM_CELLS_OFFSET = COMMON_NODE_HEADER_SIZE
LEAF_NODE_NEXT_LEAF_SIZE = np.uint32(4)
LEAF_NODE_NEXT_LEAF_OFFSET = LEAF_NODE_NUM_CELLS_OFFSET + LEAF_NODE_NUM_CELLS_SIZE
LEAF_NODE_HEADER_SIZE = COMMON_NODE_HEADER_SIZE + LEAF_NODE_NUM_CELLS_SIZE + LEAF_NODE_NEXT_LEAF_SIZE

# Leaf Node Body Layout

# LEAF_NODE_KEY_SIZE = sys.getsizeof(np.uint32)
LEAF_NODE_KEY_SIZE = 4
LEAF_NODE_KEY_OFFSET = 0
LEAF_NODE_VALUE_SIZE = ROW_SIZE
LEAF_NODE_VALUE_OFFSET = LEAF_NODE_KEY_OFFSET + LEAF_NODE_KEY_SIZE
LEAF_NODE_CELL_SIZE = LEAF_NODE_KEY_SIZE + LEAF_NODE_VALUE_SIZE
LEAF_NODE_SPACE_FOR_CELLS = PAGE_SIZE - LEAF_NODE_HEADER_SIZE
LEAF_NODE_MAX_CELLS = LEAF_NODE_SPACE_FOR_CELLS // LEAF_NODE_CELL_SIZE
LEAF_NODE_RIGHT_SPLIT_COUNT = np.uint32((LEAF_NODE_MAX_CELLS + 1) / 2)
LEAF_NODE_LEFT_SPLIT_COUNT = np.uint32((LEAF_NODE_MAX_CELLS + 1) - LEAF_NODE_RIGHT_SPLIT_COUNT )

def get_node_type(node: Any) -> NodeType:
    value = node[NODE_TYPE_OFFSET]
    return NodeType(value)

def set_node_type(node: Any, type: NodeType) -> None: # This can also be optimize.
    node[NODE_TYPE_OFFSET] = np.uint8(type.value)

def is_node_root(node: Any) -> bool:
    value = node[IS_ROOT_OFFSET]
    return bool(value)

def set_node_root(node: Any, is_root: bool) -> Any:
    value = np.uint8(is_root)
    node[IS_ROOT_OFFSET] = value
    return node[IS_ROOT_OFFSET]

def node_parent(node: Any) -> np.uint32:
    bytes = node[PARENT_POINTER_OFFSET : PARENT_POINTER_OFFSET + PARENT_POINTER_SIZE].tobytes()
    return int.from_bytes(bytes, byteorder="little")

def internal_node_num_keys(node: Any) -> np.uint32:
    bytes = node[INTERNAL_NODE_NUM_KEYS_OFFSET : INTERNAL_NODE_NUM_KEYS_OFFSET + INTERNAL_NODE_NUM_KEYS_SIZE].tobytes()
    return int.from_bytes(bytes, byteorder="little")

def internal_node_right_child(node: Any) -> np.uint32:
    bytes = node[INTERNAL_NODE_RIGHT_CHILD_OFFSET : INTERNAL_NODE_RIGHT_CHILD_OFFSET + INTERNAL_NODE_RIGHT_CHILD_SIZE].tobytes()
    return int.from_bytes(bytes, byteorder="little")

def internal_node_cell(node: Any, cell_num: np.uint32) -> np.uint32:
    cell = INTERNAL_NODE_HEADER_SIZE + cell_num * INTERNAL_NODE_CELL_SIZE
    return node[cell : cell + INTERNAL_NODE_CELL_SIZE]

def internal_node_child(node: Any, child_num: np.uint32) -> np.uint32:
    num_keys = np.uint32(internal_node_num_keys(node))
    if child_num > num_keys:
        print(f"Tried to access child_num {child_num} > num_keys {num_keys}")
        exit()
    elif child_num == num_keys:
        return internal_node_right_child(node)
    else:
        cell = internal_node_cell(node, child_num)
        return int.from_bytes(cell[:INTERNAL_NODE_CHILD_SIZE].tobytes(), byteorder="little")

def internal_node_key(node: Any, key_num: np.uint32) -> np.uint32:
    cell = internal_node_cell(node, key_num)
    bytes = cell[INTERNAL_NODE_CHILD_SIZE : INTERNAL_NODE_CHILD_SIZE + INTERNAL_NODE_KEY_SIZE]
    return int.from_bytes(bytes, byteorder="little")

def leaf_node_num_cells(node: np.ndarray) -> int:
    num_cells_bytes = node[LEAF_NODE_NUM_CELLS_OFFSET : LEAF_NODE_NUM_CELLS_OFFSET + LEAF_NODE_NUM_CELLS_SIZE].tobytes()
    return int.from_bytes(num_cells_bytes, byteorder="little")

def leaf_node_next_leaf(node: Any) -> np.uint32:
    cell = node[LEAF_NODE_NEXT_LEAF_OFFSET : LEAF_NODE_NEXT_LEAF_SIZE + LEAF_NODE_NEXT_LEAF_OFFSET]
    bytes = int.from_bytes(cell, byteorder="little")
    return bytes

def leaf_node_cell(node: np.ndarray, cell_num: int) -> np.ndarray:
    cell = LEAF_NODE_HEADER_SIZE + (cell_num * LEAF_NODE_CELL_SIZE)
    return node[cell : cell + LEAF_NODE_CELL_SIZE]

def leaf_node_key(node: np.ndarray, cell_num: int) -> np.ndarray:
    cell = leaf_node_cell(node, cell_num)
    return cell[0 : LEAF_NODE_KEY_SIZE]

def leaf_node_value(node: np.ndarray, cell_num: int) -> np.ndarray:
    cell = leaf_node_cell(node, cell_num)
    return cell[LEAF_NODE_KEY_SIZE : LEAF_NODE_KEY_SIZE + LEAF_NODE_VALUE_SIZE]

def get_node_max_key(node: Any) -> np.uint32: # It had pager: Pager as its first parameter.
    match get_node_type(node):
        case NodeType.NODE_INTERNAL:
            bytes = internal_node_key(node, internal_node_num_keys(node) - 1).tobytes()
            return int.from_bytes(bytes, byteorder="little")
        case NodeType.NODE_LEAF:
            bytes = leaf_node_key(node, leaf_node_num_cells(node) - 1).tobytes()
            return int.from_bytes(bytes, byteorder="little")

def print_constants() -> None:
    print(f"ROW_SIZE: {ROW_SIZE}")
    print(f"COMMON_NODE_HEADER_SIZE: {COMMON_NODE_HEADER_SIZE}")
    print(f"LEAF_NODE_HEADER_SIZE: {LEAF_NODE_HEADER_SIZE}")
    print(f"LEAF_NODE_CELL_SIZE: {LEAF_NODE_CELL_SIZE}")
    print(f"LEAF_NODE_SPACE_FOR_CELLS: {LEAF_NODE_SPACE_FOR_CELLS}")
    print(f"LEAF_NODE_MAX_CELLS: {LEAF_NODE_MAX_CELLS}")

def indent(level: np.uint32) -> None:
    for i in range(level):
        print("  ", end="")

def print_tree(pager: Pager, page_num: np.uint32, indentation_level: np.uint32) -> None:
    node = get_page(pager, page_num)
    
    match get_node_type(node):
        case NodeType.NODE_LEAF:
            num_keys = np.uint32(leaf_node_num_cells(node))
            indent(indentation_level)
            print(f"- leaf (size {num_keys})")
            for i in range(num_keys):
                indent(indentation_level + 1)
                key = int.from_bytes(leaf_node_key(node, i).tobytes(), byteorder="little")
                print(f"- {key}")
        case NodeType.NODE_INTERNAL:
            num_keys = np.uint32(internal_node_num_keys(node))
            indent(indentation_level)
            print(f"- internal (size {num_keys})")
            for i in range(num_keys):
                child = np.uint32(internal_node_child(node, i))
                print_tree(pager, child, indentation_level + 1)

                indent(indentation_level + 1)
                key = int.from_bytes(leaf_node_key(node, i).tobytes(), byteorder="little")
                print(f"- key {key}")
            child = np.uint32(internal_node_right_child(node))
            print_tree(pager, child, indentation_level + 1)

# THIS FUNCTIONS ONLY EXISTS BECAUSE IN PYTHON I CAN'T DIRECTLY MODIFY THE VALUE OF A MEMORY ADDRESS, ONLY A COPY.
def get_leaf_node_cell_offset(cell_num: int) -> int:
    return LEAF_NODE_HEADER_SIZE + (cell_num * LEAF_NODE_CELL_SIZE)

def set_leaf_node_num_cells(node: np.ndarray, num_cells: int) -> None:
    bytes_val = num_cells.to_bytes(LEAF_NODE_NUM_CELLS_SIZE, byteorder="little")
    node[LEAF_NODE_NUM_CELLS_OFFSET : LEAF_NODE_NUM_CELLS_OFFSET + LEAF_NODE_NUM_CELLS_SIZE] = np.frombuffer(bytes_val, dtype=np.uint8)

def set_leaf_node_key(node: np.ndarray, cell_num: int, key: int) -> None:
    offset = get_leaf_node_cell_offset(cell_num)
    key_bytes = key.to_bytes(LEAF_NODE_KEY_SIZE, byteorder="little")
    node[offset : offset + LEAF_NODE_KEY_SIZE] = np.frombuffer(key_bytes, dtype=np.uint8)
# PYTHON ONLY HELPER END HERE.

def print_row(row: Row) -> None:
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

def initialize_leaf_node(node: np.ndarray) -> None:
    node[NODE_TYPE_OFFSET] = np.uint8(NodeType.NODE_LEAF.value)
    node[IS_ROOT_OFFSET] = np.uint8(False)

    bytes_val = (0).to_bytes(LEAF_NODE_NUM_CELLS_SIZE, byteorder="little")
    node[LEAF_NODE_NUM_CELLS_OFFSET : LEAF_NODE_NUM_CELLS_OFFSET + LEAF_NODE_NUM_CELLS_SIZE] = np.frombuffer(bytes_val, dtype=np.uint8)

    bytes_val = (0).to_bytes(LEAF_NODE_NEXT_LEAF_SIZE, byteorder="little")
    node[LEAF_NODE_NEXT_LEAF_OFFSET : LEAF_NODE_NEXT_LEAF_OFFSET + LEAF_NODE_NEXT_LEAF_SIZE] = np.frombuffer(bytes_val, dtype=np.uint8) # Represents no siblings

def initialize_internal_node(node: Any) -> None:
    set_node_type(node, NodeType.NODE_INTERNAL)
    set_node_root(node, False)

    bytes = (0).to_bytes(int(INTERNAL_NODE_NUM_KEYS_SIZE), byteorder="little")
    node[INTERNAL_NODE_NUM_KEYS_OFFSET : INTERNAL_NODE_NUM_KEYS_OFFSET + INTERNAL_NODE_NUM_KEYS_SIZE] = np.frombuffer(bytes, dtype=np.uint8)

def leaf_node_find(table: Table, page_num: np.uint32, key: np.uint32) -> Cursor:
    node = get_page(table.pager, page_num)
    num_cells = np.uint32(leaf_node_num_cells(node))

    cursor = Cursor(table, False, page_num, 0)

    # Binary search
    min_index = np.uint32(0)
    one_past_max_index = num_cells
    while one_past_max_index != min_index:
        index = np.uint32((min_index + one_past_max_index) // 2)
        key_at_index = int.from_bytes(leaf_node_key(node, index).tobytes(), byteorder="little")
        key_at_index = np.uint32(key_at_index)
        if key == key_at_index:
            cursor.cell_num = index
            return cursor
        if key < key_at_index:
            one_past_max_index = index
        else:
            min_index = index + 1

    cursor.cell_num = min_index
    return cursor

def get_page(pager: Pager, page_num: int) -> Any:
    if page_num > TABLE_MAX_PAGES:
        print("Tried to fetch page number out of bounds. {page_num} > {TABLE_MAX_PAGES}")
        exit() # Not sure if to keep this here.

    if pager.pages[page_num] is None:
        # Cache miss. Allocate memory and load from file.
        page = np.zeros(PAGE_SIZE, dtype=np.uint8)
        num_pages = pager.file_length // PAGE_SIZE

        # We might save a partial page at the end of the file.
        if pager.file_length % PAGE_SIZE:
            num_pages += 1

        if page_num <= num_pages:
            try:
                os.lseek(pager.file_descriptor, page_num * PAGE_SIZE, os.SEEK_SET)
                bytes_read = os.read(pager.file_descriptor, PAGE_SIZE)
                page[:len(bytes_read)] = np.frombuffer(bytes_read, dtype=np.uint8)
            except OSError as errno:
                print(f"Error reading file: {errno}")
                exit()

        pager.pages[page_num] = page

        if page_num >= pager.num_pages:
            pager.num_pages = page_num + 1

    return pager.pages[page_num]

def internal_node_find_child(node: Any, key: np.uint32) -> np.uint32:
    # Return the index of the child which should contain the given key.

    num_keys = np.uint32(internal_node_num_keys(node))

    # Binary search
    min_index = np.uint32(0)
    max_index = np.uint32(num_keys) # There is one more child that key

    while min_index != max_index:
        index = np.uint32((min_index + max_index) // 2)
        key_to_right = internal_node_key(node, index)
        if key_to_right >= key:
            max_index = index
        else:
            min_index = index + 1

    return min_index

def internal_node_find(table: Table, page_num: np.uint32, key: np.uint32) -> Cursor:
    node = get_page(table.pager, page_num)
    child_index = np.uint32(internal_node_find_child(node, key))
    child_num = np.uint32(internal_node_child(node, child_index))
    child = get_page(table.pager, child_num)

    match get_node_type(child):
        case NodeType.NODE_LEAF:
            return leaf_node_find(table, child_num, key)
        case NodeType.NODE_INTERNAL:
            return internal_node_find(table, child_num, key)

def table_start(table: Table) -> Cursor:
    cursor = table_find(table, 0)

    node = get_page(table.pager, cursor.page_num)
    num_cells = leaf_node_num_cells(node)
    cursor.end_of_table = (num_cells == 0)

    return cursor

# Return the position of the given key.
# If the key is not present, return the position where it should be inserted.

def table_find(table: Table, key: np.uint32) -> Cursor:
    root_page_num = np.uint32(table.root_page_num)
    root_node = get_page(table.pager, root_page_num)

    if get_node_type(root_node) == NodeType.NODE_LEAF:
        return leaf_node_find(table, root_page_num, key)
    else:
        return internal_node_find(table, root_page_num, key)

def cursor_value(cursor: Cursor) -> int:
    page_num = cursor.page_num
    page = get_page(cursor.table.pager, page_num)

    return leaf_node_value(page, cursor.cell_num)

def cursor_advance(cursor: Cursor) -> None:
    page_num = cursor.page_num
    node = get_page(cursor.table.pager, page_num)

    cursor.cell_num += 1
    if cursor.cell_num >= leaf_node_num_cells(node):
        # Advance to next lead node
        next_page_num = np.uint32(leaf_node_next_leaf(node))
        if next_page_num == np.uint32(0):
            # This was rightmost leaf
            cursor.end_of_table = True
        else:
            cursor.page_num = next_page_num
            cursor.cell_num = 0

def pager_open(filename: str) -> Pager:
    fd = os.open(filename, os.O_RDWR | os.O_CREAT, stat.S_IWUSR | stat.S_IRUSR)

    if fd == -1:
        print("Unable to open file")
        exit()

    file_length = os.lseek(fd, 0, os.SEEK_END)

    pager = Pager()
    pager.file_descriptor = fd
    pager.file_length = file_length
    pager.num_pages = file_length // PAGE_SIZE

    if file_length % PAGE_SIZE != 0:
        print(file_length)
        print("Db file is not a whole number of pages. Corrupt file.")
        exit()

    for i in range(TABLE_MAX_PAGES):
        pager.pages[i] = None
    return pager

def free_table(table: Table) -> None:
    if table.pager and table.pager.pages:
        for i in range(len(table.pages)):
            table.pages.pages[i] = None

def db_open(filename: str) -> Table:
    pager = pager_open(filename)

    table = Table(pager)
    table.pager = pager
    table.root_page_num = 0

    if pager.num_pages == 0:
        # New database file. Initialize page 0 as leaf node.
        root_node = get_page(pager, 0)
        initialize_leaf_node(root_node)
        set_node_root(root_node, True)

    return table

def new_input_buffer() -> Input_Buffer:
    return InputBuffer()

def print_promt() -> None:
    print("db > ", end="")

def read_input(input_buffer: str) -> None:
    bytes_read = input()

    if not sys.stdin.isatty():
        print(bytes_read)

    input_buffer.buffer = bytes_read
    input_buffer.buffer_length = len(bytes_read) - 1
    input_buffer.input_length = len(bytes_read)

    if len(bytes_read) <= 0:
        print("Error reading input")

    return bytes_read

def close_input_buffer(input_buffer: InputBuffer) -> None:
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

    for i in range(pager.num_pages):
        if pager.pages[i] is None:
            continue
        pager_flusher(pager, i)
        pager.pages[i] = None

def do_meta_command(input_buffer: str, table: Table) -> MetaCommandResult:
    if input_buffer.buffer == ".exit":
        close_input_buffer(input_buffer)
        db_close(table)
        exit()
    elif input_buffer.buffer == ".btree":
        print("Tree:")
        print_tree(table.pager, 0, 0)
        return MetaCommandResult.META_COMMAND_SUCCESS
    elif input_buffer.buffer == ".constants":
        print("Constants:")
        print_constants()
        # print_tree(get_page(table.pager, 0))
        return MetaCommandResult.META_COMMAND_SUCCESS
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

# Until we start recycling free pages, new pages will always go onto the end of the database file

def get_unused_page_num(pager: Pager) -> np.uint32:
    return np.uint32(pager.num_pages)

def create_new_root(table: Table, right_child_page_num: np.uint32) -> None:
    # Handle splitting the root.
    # Old root copied to new page, becomes left child.
    # Address of right child passed in.
    # Re-initialize root page to contain the new root node.
    # New root node points to two children.

    root = get_page(table.pager, table.root_page_num)
    right_child = get_page(table.pager, right_child_page_num)
    left_child_page_num = np.uint32(get_unused_page_num(table.pager))
    left_child = get_page(table.pager, left_child_page_num)

    # Left child has data copied from old root
    left_child[:] = root[:]
    set_node_root(left_child, False)

    # Root node is a new internal node with one key and two children
    initialize_internal_node(root)
    set_node_root(root, True)

    # WE HAVE TO CHECK THIS, MAYBE USE HELPER FUNCTIONS?
    # Check this later:
    # Set internal node num keys to 1
    num_keys_bytes = (1).to_bytes(INTERNAL_NODE_NUM_KEYS_SIZE, byteorder="little")
    root[INTERNAL_NODE_NUM_KEYS_OFFSET : INTERNAL_NODE_NUM_KEYS_OFFSET + INTERNAL_NODE_NUM_KEYS_SIZE] = np.frombuffer(num_keys_bytes, dtype=np.uint8)

    # Set left child pointer
    left_child_bytes = int(left_child_page_num).to_bytes(INTERNAL_NODE_CHILD_SIZE, byteorder="little")
    cell_offset = INTERNAL_NODE_HEADER_SIZE 
    root[cell_offset : cell_offset + INTERNAL_NODE_CHILD_SIZE] = np.frombuffer(left_child_bytes, dtype=np.uint8)

    # Set key
    left_child_max_key = get_node_max_key(left_child)
    key_bytes = int(left_child_max_key).to_bytes(INTERNAL_NODE_KEY_SIZE, byteorder="little")
    root[cell_offset + INTERNAL_NODE_CHILD_SIZE : cell_offset + INTERNAL_NODE_CHILD_SIZE + INTERNAL_NODE_KEY_SIZE] = np.frombuffer(key_bytes, dtype=np.uint8)

    # Set right child pointer
    right_child_bytes = int(right_child_page_num).to_bytes(INTERNAL_NODE_RIGHT_CHILD_SIZE, byteorder="little")
    root[INTERNAL_NODE_RIGHT_CHILD_OFFSET : INTERNAL_NODE_RIGHT_CHILD_OFFSET + INTERNAL_NODE_RIGHT_CHILD_SIZE] = np.frombuffer(right_child_bytes, dtype=np.uint8)

    bytes = int(table.root_page_num).to_bytes(PARENT_POINTER_SIZE, byteorder="little")
    left_child[PARENT_POINTER_OFFSET : PARENT_POINTER_OFFSET + PARENT_POINTER_SIZE] = np.frombuffer(bytes, dtype=np.uint8)

    bytes = int(table.root_page_num).to_bytes(PARENT_POINTER_SIZE, byteorder="little")
    right_child[PARENT_POINTER_OFFSET : PARENT_POINTER_OFFSET + PARENT_POINTER_SIZE] = np.frombuffer(bytes, dtype=np.uint8)
    # END OF WHAT WE HAVE TO CHECK.

def internal_node_insert(table: Table, parent_page_num: np.uint32, child_page_num: np.uint32) -> None:
    # Add a new child/key pair to parent that corresponds to child

    parent = get_page(table.pager, parent_page_num)
    child = get_page(table.pager, child_page_num)
    child_max_key = np.uint32(get_node_max_key(child))
    index = np.uint32(internal_node_find_child(parent, child_max_key))

    original_num_keys = np.uint32(internal_node_num_keys(parent))

    if original_num_keys >= INTERNAL_NODE_MAX_CELLS:
        print("Need to implement splitting internal node")
        exit()

    new_num_keys_bytes = int(original_num_keys + 1).to_bytes(INTERNAL_NODE_NUM_KEYS_SIZE, byteorder="little")
    parent[INTERNAL_NODE_NUM_KEYS_OFFSET : INTERNAL_NODE_NUM_KEYS_OFFSET + INTERNAL_NODE_NUM_KEYS_SIZE] = np.frombuffer(new_num_keys_bytes, dtype=np.uint8)

    right_child_page_num = internal_node_right_child(parent)
    right_child = get_page(table.pager, right_child_page_num)

    if child_max_key > get_node_max_key(right_child):
        # Replace right child
        cell_offset = INTERNAL_NODE_HEADER_SIZE + (original_num_keys * INTERNAL_NODE_CELL_SIZE)
        
        # *internal_node_child(parent, original_num_keys) = right_child_page_num
        parent[cell_offset : cell_offset + INTERNAL_NODE_CHILD_SIZE] = np.frombuffer(
            int(right_child_page_num).to_bytes(INTERNAL_NODE_CHILD_SIZE, byteorder="little"), dtype=np.uint8)
        
        # *internal_node_key(parent, original_num_keys) = get_node_max_key(right_child)
        parent[cell_offset + INTERNAL_NODE_CHILD_SIZE : cell_offset + INTERNAL_NODE_CELL_SIZE] = np.frombuffer(
            int(get_node_max_key(right_child)).to_bytes(INTERNAL_NODE_KEY_SIZE, byteorder="little"), dtype=np.uint8)
        
        # *internal_node_right_child(parent) = child_page_num
        parent[INTERNAL_NODE_RIGHT_CHILD_OFFSET : INTERNAL_NODE_RIGHT_CHILD_OFFSET + INTERNAL_NODE_RIGHT_CHILD_SIZE] = np.frombuffer(
            int(child_page_num).to_bytes(INTERNAL_NODE_RIGHT_CHILD_SIZE, byteorder="little"), dtype=np.uint8)
        
    else:
        # Make room for the new cell
        for i in range(original_num_keys, index, -1):
            dest_offset = INTERNAL_NODE_HEADER_SIZE + (i * INTERNAL_NODE_CELL_SIZE)
            src_offset = INTERNAL_NODE_HEADER_SIZE + ((i - 1) * INTERNAL_NODE_CELL_SIZE)
            parent[dest_offset : dest_offset + INTERNAL_NODE_CELL_SIZE] = parent[src_offset : src_offset + INTERNAL_NODE_CELL_SIZE]
            
        index_offset = INTERNAL_NODE_HEADER_SIZE + (index * INTERNAL_NODE_CELL_SIZE)
        
        # *internal_node_child(parent, index) = child_page_num
        parent[index_offset : index_offset + INTERNAL_NODE_CHILD_SIZE] = np.frombuffer(
            int(child_page_num).to_bytes(INTERNAL_NODE_CHILD_SIZE, byteorder="little"), dtype=np.uint8)
        
        # *internal_node_key(parent, index) = child_max_key
        parent[index_offset + INTERNAL_NODE_CHILD_SIZE : index_offset + INTERNAL_NODE_CELL_SIZE] = np.frombuffer(
            int(child_max_key).to_bytes(INTERNAL_NODE_KEY_SIZE, byteorder="little"), dtype=np.uint8)
        # HERE ENDS WHAT WE NEED TO CHECK

def update_internal_node_key(node: Any, old_key: np.uint32, new_key: np.uint32) -> None:
    old_child_index = internal_node_find_child(node, old_key)
    cell_offset = INTERNAL_NODE_HEADER_SIZE + (old_child_index * INTERNAL_NODE_CELL_SIZE)
    key_offset = cell_offset + INTERNAL_NODE_CHILD_SIZE
    # *internal_node_key(node, old_child_index_ = new_index
    # internal_node_cell_value = internal_node_cell(node, old_child_index)
    # internal_node_cell_value[INTERNAL_NODE_CHILD_SIZE : INTERNAL_NODE_CHILD_SIZE + INTERNAL_NODE_CHILD_OFFSET] = np.frombuffer(new_key, dtype=np.uint8)

    bytes = int(new_key).to_bytes(INTERNAL_NODE_KEY_SIZE, byteorder="little")
    node[key_offset : key_offset + INTERNAL_NODE_KEY_SIZE] = np.frombuffer(bytes, dtype=np.uint8)

def leaf_node_split_and_insert(cursor: Cursor, key: np.uint32, value: Row) -> None:
    # Create a new node and move half the cells over.
    # Insert the new value in one of the two nodes.
    # Update parent or create a new parent.

    old_node = get_page(cursor.table.pager, cursor.page_num)
    old_max = np.uint32(get_node_max_key(old_node))
    new_page_num = np.uint32(get_unused_page_num(cursor.table.pager))
    new_node = get_page(cursor.table.pager, new_page_num)
    initialize_leaf_node(new_node)

    bytes = node_parent(old_node).to_bytes(PARENT_POINTER_SIZE, byteorder="little")
    new_node[PARENT_POINTER_OFFSET : PARENT_POINTER_OFFSET + PARENT_POINTER_SIZE] = np.frombuffer(bytes, dtype=np.uint8)

    bytes_val = leaf_node_next_leaf(old_node).to_bytes(LEAF_NODE_NEXT_LEAF_SIZE, byteorder="little")
    new_node[LEAF_NODE_NEXT_LEAF_OFFSET : LEAF_NODE_NEXT_LEAF_OFFSET + LEAF_NODE_NEXT_LEAF_SIZE] = np.frombuffer(bytes_val, dtype=np.uint8)

    bytes_val = int(new_page_num).to_bytes(LEAF_NODE_NEXT_LEAF_SIZE, byteorder="little")
    old_node[LEAF_NODE_NEXT_LEAF_OFFSET : LEAF_NODE_NEXT_LEAF_OFFSET + LEAF_NODE_NEXT_LEAF_SIZE] = np.frombuffer(bytes_val, dtype=np.uint8)

    # All existing keys plus new key should be divided evenly between old (left) and new (right) nodes.
    # Starting from the right, move each ket to correct position.

    for i in range(LEAF_NODE_MAX_CELLS, -1, -1):
        if i >= LEAF_NODE_LEFT_SPLIT_COUNT:
            destination_node = new_node
        else:
            destination_node = old_node

        index_within_node = np.uint32(i % LEAF_NODE_LEFT_SPLIT_COUNT)
        destination = leaf_node_cell(destination_node, index_within_node)

        if i == cursor.cell_num:
            set_leaf_node_key(destination_node, index_within_node, key) # Fact check this.
            serialize_row(value, leaf_node_value(destination_node, index_within_node))
        elif i > cursor.cell_num:
            destination[:LEAF_NODE_CELL_SIZE] = leaf_node_cell(old_node, i - 1)[:LEAF_NODE_CELL_SIZE]
        else:
            destination[:LEAF_NODE_CELL_SIZE] = leaf_node_cell(old_node, i)[:LEAF_NODE_CELL_SIZE]

    set_leaf_node_num_cells(old_node, int(LEAF_NODE_LEFT_SPLIT_COUNT))
    set_leaf_node_num_cells(new_node, int(LEAF_NODE_RIGHT_SPLIT_COUNT))

    if is_node_root(old_node):
        return create_new_root(cursor.table, new_page_num)
    else:
        parent_page_num = np.uint32(node_parent(old_node))
        new_max = np.uint32(get_node_max_key(old_node))
        parent = get_page(cursor.table.pager, parent_page_num)

        update_internal_node_key(parent, old_max, new_max)
        internal_node_insert(cursor.table, parent_page_num, new_page_num)
        return

def leaf_node_insert(cursor: Cursor, key: int, value: Row) ->None: # We have to heavily modify this function to not rely on helper functions so much.
    node = get_page(cursor.table.pager, cursor.page_num)

    num_cells = leaf_node_num_cells(node)
    if num_cells >= LEAF_NODE_MAX_CELLS:
        # Node full
        leaf_node_split_and_insert(cursor, key, value)
        return

    if cursor.cell_num < num_cells:
        src_start = get_leaf_node_cell_offset(cursor.cell_num)
        src_end = get_leaf_node_cell_offset(num_cells)
        dest_start = src_start + LEAF_NODE_CELL_SIZE
        dest_end = src_end + LEAF_NODE_CELL_SIZE

        node[dest_start:dest_end] = node[src_start:src_end]

    set_leaf_node_num_cells(node, num_cells + 1)
    set_leaf_node_key(node, cursor.cell_num, key)
    serialize_row(value, leaf_node_value(node, cursor.cell_num)) 

def execute_insert(statement: Statement, table: Table) -> ExecuteResult:
    row_to_insert = statement.row_to_insert
    key_to_insert = row_to_insert.id
    cursor = table_find(table, key_to_insert)

    node = get_page(table.pager, cursor.page_num)
    num_cells = leaf_node_num_cells(node)

    if cursor.cell_num < num_cells:
        key_at_index = int.from_bytes(leaf_node_key(node, cursor.cell_num).tobytes(), byteorder="little")
        if key_at_index == key_to_insert:
            return ExecuteResult.EXECUTE_DUPLICATE_KEY

    leaf_node_insert(cursor, row_to_insert.id, row_to_insert)

    return ExecuteResult.EXECUTE_SUCCESS

def execute_select(statement: Statement, table: Table) -> ExecuteResult:
    cursor = table_start(table)
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
        match state:
            case ExecuteResult.EXECUTE_SUCCESS:
                print("Executed.")
                continue
            case ExecuteResult.EXECUTE_DUPLICATE_KEY:
                print("Error: Duplicate key.")
                continue
            case ExecuteResult.EXECUTE_TABLE_FULL:
                print("Error: Table full.")
                continue

if __name__ == "__main__":
    main()
