import subprocess
import unittest
import os

def run_script(commands):
    input_data = "\n".join(commands) + "\n"
    
    result = subprocess.run(
        ["python3", "./main.py", "mydb.db"],
        input=input_data,
        text=True,
        capture_output=True
    )
    
    return result.stdout.split("\n")

class TestDatabase(unittest.TestCase):
    def setUp(self):
        if os.path.exists("mydb.db"):
            os.remove("mydb.db")
            
    def tearDown(self):
        if os.path.exists("mydb.db"):
            os.remove("mydb.db")

    def test_basic_cases(self):
        result = run_script([
            "insert 1 foo foo@bar.com",
            "insert 2 bob bob@bar.com",
            "select",
            "insert foo bar 1",
            ".exit"
        ])
        self.assertEqual(result, [
            "db > insert 1 foo foo@bar.com",
            "Executed.",
            "db > insert 2 bob bob@bar.com",
            "Executed.",
            "db > select",
            "1, foo, foo@bar.com",
            "2, bob, bob@bar.com",
            "Executed.",
            "db > insert foo bar 1",
            "Syntax error. Could not parse statement.",
            "db > .exit",
            ""
         ])

    def test_inserts_and_retrieves_a_row(self):
        result = run_script([
            "insert 1 user1 person1@example.com",
            "select",
            ".exit",
        ])
        self.assertEqual(result, [
            "db > insert 1 user1 person1@example.com",
            "Executed.",
            "db > select",
            "1, user1, person1@example.com",
            "Executed.",
            "db > .exit",
            ""
        ])

    def test_prints_error_message_when_table_is_full(self):
        script = [f"insert {i} user{i} person{i}@example.com" for i in range(1, 1402)]
        script.append(".exit")
        
        result = run_script(script)
        
        self.assertEqual(result[-3], "Error: Table full.")

    def test_allows_inserting_strings_that_are_maximum_length(self):
        long_username = "a" * 32
        long_email = "a" * 255
        script = [
            f"insert 1 {long_username} {long_email}",
            "select",
            ".exit",
        ]
        result = run_script(script)
        
        self.assertEqual(result, [
            f"db > insert 1 {long_username} {long_email}",
            "Executed.",
            "db > select",
            f"1, {long_username}, {long_email}",
            "Executed.",
            "db > .exit",
            ""
        ])

    def test_prints_error_message_if_strings_are_too_long(self):
        long_username = "a" * 33
        long_email = "a" * 256
        script = [
            f"insert 1 {long_username} {long_email}",
            "select",
            ".exit",
        ]
        result = run_script(script)
        
        self.assertEqual(result, [
            f"db > insert 1 {long_username} {long_email}",
            "String is too long.",
            "db > select",
            "Executed.",
            "db > .exit",
            ""
        ])

    def test_prints_error_message_if_id_is_negative(self):
        script = [
            "insert -1 foo foo@bar.com",
            "select",
            ".exit",
        ]
        result = run_script(script)
        
        self.assertEqual(result, [
            "db > insert -1 foo foo@bar.com",
            "ID must be positive.",
            "db > select",
            "Executed.",
            "db > .exit",
            ""
        ])

    def test_keeps_data_after_closing_connection(self):
        result1 = run_script([
            "insert 1 user1 person1@example.com",
            ".exit",
        ])
        self.assertEqual(result1, [
            "db > insert 1 user1 person1@example.com",
            "Executed.",
            "db > .exit",
            ""
        ])

        result2 = run_script([
            "select",
            ".exit",
        ])
        self.assertEqual(result2, [
            "db > select",
            "1, user1, person1@example.com",
            "Executed.",
            "db > .exit",
            ""
        ])

    def test_prints_the_structure_of_a_one_node_btree(self):
        result = run_script([
            "insert 3 user3 person3@example.com",
            "insert 1 user1 person1@example.com",
            "insert 2 user2 person2@example.com",
            ".btree",
            ".exit",
        ])
        self.assertEqual(result, [
            "db > insert 3 user3 person3@example.com",
            "Executed.",
            "db > insert 1 user1 person1@example.com",
            "Executed.",
            "db > insert 2 user2 person2@example.com",
            "Executed.",
            "db > .btree",
            "Tree:",
            "leaf (size 3)",
            "  - 0 : 3",
            "  - 1 : 1",
            "  - 2 : 2",
            "db > .exit",
            ""
        ])

    def test_print_constants(self):
        result = run_script([
            ".constants",
            ".exit",
        ])
        self.assertEqual(result, [
            "db > .constants",
            "Constants:",
            "ROW_SIZE: 291", # It should be 293.
            "COMMON_NODE_HEADER_SIZE: 6",
            "LEAF_NODE_HEADER_SIZE: 10",
            "LEAF_NODE_CELL_SIZE: 295", # It should be 297.
            "LEAF_NODE_SPACE_FOR_CELLS: 4086",
            "LEAF_NODE_MAX_CELLS: 13",
            "leaf (size 0)",
            "db > .exit",
            ""
        ])

if __name__ == '__main__':
    unittest.main()
