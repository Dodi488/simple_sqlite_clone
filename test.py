import subprocess
import unittest

def run_script(commands):
    # Join the commands with newlines and add a trailing newline
    input_data = "\n".join(commands) + "\n"
    
    # Run the compiled ./db executable, passing the commands via stdin
    result = subprocess.run(
        ["python3", "./main.py"],
        input=input_data,
        text=True,
        capture_output=True
    )
    
    # Split the raw output by newline to match the Ruby implementation
    return result.stdout.split("\n")


class TestDatabase(unittest.TestCase):
    def test_inserts_and_retrieves_a_row(self):
        result = run_script([
            "insert 1 user1 person1@example.com",
            "select",
            ".exit",
        ])
        self.assertEqual(result, [
            "db > Executed.",
            "db > 1, user1, person1@example.com",
            "Executed.",
            "db > ",
        ])

    def test_prints_error_message_when_table_is_full(self):
        script = [f"insert {i} user{i} person{i}@example.com" for i in range(1, 1402)]
        script.append(".exit")
        
        result = run_script(script)
        
        # Check the second-to-last output line
        self.assertEqual(result[-2], "db > Error: Table full.")

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
            "db > Executed.",
            f"db > 1, {long_username}, {long_email}",
            "Executed.",
            "db > ",
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
            "db > String is too long.",
            "db > Executed.",
            "db > ",
        ])

    def test_prints_error_message_if_id_is_negative(self):
        script = [
            "insert -1 cstack foo@bar.com",
            "select",
            ".exit",
        ]
        result = run_script(script)
        
        self.assertEqual(result, [
            "db > ID must be positive.",
            "db > Executed.",
            "db > ",
        ])

if __name__ == '__main__':
    unittest.main()
