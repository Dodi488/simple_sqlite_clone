from enum import Enum

class MetaCommandResult(Enum):
    META_COMMAND_SUCCESS = 0
    META_COMMAND_UNRECOGNIZED_COMMAND = 1

class PrepareResult(Enum):
    PREPARE_SUCCESS = 0
    PREPARE_UNRECOGNIZED_STATEMENT = 1

class StatementType(Enum):
    STATEMENT_INSERT = 0
    STATEMENT_SELECT = 1

class Statement(Enum):
    STATEMENT_INSERT = 0
    STATEMENT_SELECT = 1

def print_promt():
    print("db > ", end="")

def read_input():
    bytes_read = input()

    if len(bytes_read) <= 0:
        print("Error reading input")

    return bytes_read

def do_meta_command(input):
    if input == ".exit":
        exit()
    else:
        return MetaCommandResult.META_COMMAND_UNRECOGNIZED_COMMAND

def prepare_statement(input_buffer):
    if input_buffer == "insert":
        return PrepareResult.PREPARE_SUCCESS, StatementType.STATEMENT_INSERT

    elif input_buffer == "select":
        return PrepareResult.PREPARE_SUCCESS, StatementType.STATEMENT_SELECT

    return PrepareResult.PREPARE_UNRECOGNIZED_STATEMENT, 1

def execute_statement(statement):
    match statement:
        case StatementType.STATEMENT_INSERT:
            print("This is where we would do an insert.")
        case StatementType.STATEMENT_SELECT:
            print("This is where we would do a select.");

def main(*args):
    while True:
        print_promt()
        input = read_input()

        if input[0] == ".":
            match do_meta_command(input):
                case MetaCommandResult.META_COMMAND_SUCCESS:
                    pass
                case MetaCommandResult.META_COMMAND_UNRECOGNIZED_COMMAND:
                    print(f"Unrecognized command '{input}'.")
                    continue

        prepare_statement_value, statement_type = prepare_statement(input.split()[0])
        match prepare_statement_value:
            case PrepareResult.PREPARE_SUCCESS:
                pass
            case PrepareResult.PREPARE_UNRECOGNIZED_STATEMENT:
                print(f"Unrecognized keyword at start of '{input}'.")
                continue
        
        execute_statement(statement_type)
        print("Executed.")

if __name__ == "__main__":
    main()
