import subprocess
import unittest

def run_script(commands):
    input_data = "\n".join(commands) + "\n"
    
    result = subprocess.run(
        ["python3", "./main.py"],
        input=input_data,
        text=True,
        capture_output=True
    )
    
    return result.stdout.split("\n")

class TestDatabase(unittest.TestCase):
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
            "insert -1 cstack foo@bar.com",
            "select",
            ".exit",
        ]
        result = run_script(script)
        
        self.assertEqual(result, [
            "db > insert -1 cstack foo@bar.com",
            "ID must be positive.",
            "db > select",
            "Executed.",
            "db > .exit",
            ""
        ])

if __name__ == '__main__':
    unittest.main()
