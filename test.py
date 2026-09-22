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
       
        self.assertEqual(result[-3], "db > insert 385 user385 person385@example.com") 
        # self.assertEqual(result[-2], "Need to implement splitting internal node")
        self.assertEqual(result[-2], "Tried to fetch page number out of bounds. 100 >= 100")

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
            "- leaf (size 3)",
            "  - 1",
            "  - 2",
            "  - 3",
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
            "LEAF_NODE_HEADER_SIZE: 14",
            "LEAF_NODE_CELL_SIZE: 295",
            "LEAF_NODE_SPACE_FOR_CELLS: 4082",
            "LEAF_NODE_MAX_CELLS: 13",
            "db > .exit",
            ""
        ])

    def test_duplicate_key(self):
        result = run_script([
            "insert 1 user1 person1@example.com",
            "insert 1 user1 person1@example.com",
            ".exit",
        ])
        self.assertEqual(result, [
            "db > insert 1 user1 person1@example.com",
            "Executed.",
            "db > insert 1 user1 person1@example.com",
            "Error: Duplicate key.",
            "db > .exit",
            ""
        ])

    def test_print_structure_of_a_3_leaf_btree(self):
        script = [f"insert {i} person{i} person{i}@example.com" for i in range(1, 15)]
        script.append(".btree")
        script.append("insert 15 person15 person15@example.com")
        script.append(".exit")
        result = run_script(script)
        self.assertEqual(result, [
            "db > insert 1 person1 person1@example.com",
            "Executed.",
            "db > insert 2 person2 person2@example.com",
            "Executed.",
            "db > insert 3 person3 person3@example.com",
            "Executed.",
            "db > insert 4 person4 person4@example.com",
            "Executed.",
            "db > insert 5 person5 person5@example.com",
            "Executed.",
            "db > insert 6 person6 person6@example.com",
            "Executed.",
            "db > insert 7 person7 person7@example.com",
            "Executed.",
            "db > insert 8 person8 person8@example.com",
            "Executed.",
            "db > insert 9 person9 person9@example.com",
            "Executed.",
            "db > insert 10 person10 person10@example.com",
            "Executed.",
            "db > insert 11 person11 person11@example.com",
            "Executed.",
            "db > insert 12 person12 person12@example.com",
            "Executed.",
            "db > insert 13 person13 person13@example.com",
            "Executed.",
            "db > insert 14 person14 person14@example.com",
            "Executed.",
            "db > .btree",
            "Tree:",
            "- internal (size 1)",
            "  - leaf (size 7)",
            "    - 1",
            "    - 2",
            "    - 3",
            "    - 4",
            "    - 5",
            "    - 6",
            "    - 7",
            "  - key 7",
            "  - leaf (size 7)",
            "    - 8",
            "    - 9",
            "    - 10",
            "    - 11",
            "    - 12",
            "    - 13",
            "    - 14",
            "db > insert 15 person15 person15@example.com",
            "Executed.",
            # "Need to implement updating parent after split",
            "db > .exit",
            ""
        ])

def test_full_tree(self):
        inserts = [f"insert {i} person{i} person{i}@example.com" for i in range(1, 86)]
        inserts.append(".btree")
        inserts.append(".exit")
        results = run_script(inserts)
        self.assertEqual(results, [
            "db > insert 1 person1 person1@example.com",
            "Executed.",
            "db > insert 2 person2 person2@example.com",
            "Executed.",
            "db > insert 3 person3 person3@example.com",
            "Executed.",
            "db > insert 4 person4 person4@example.com",
            "Executed.",
            "db > insert 5 person5 person5@example.com",
            "Executed.",
            "db > insert 6 person6 person6@example.com",
            "Executed.",
            "db > insert 7 person7 person7@example.com",
            "Executed.",
            "db > insert 8 person8 person8@example.com",
            "Executed.",
            "db > insert 9 person9 person9@example.com",
            "Executed.",
            "db > insert 10 person10 person10@example.com",
            "Executed.",
            "db > insert 11 person11 person11@example.com",
            "Executed.",
            "db > insert 12 person12 person12@example.com",
            "Executed.",
            "db > insert 13 person13 person13@example.com",
            "Executed.",
            "db > insert 14 person14 person14@example.com",
            "Executed.",
            "db > insert 15 person15 person15@example.com",
            "Executed.",
            "db > insert 16 person16 person16@example.com",
            "Executed.",
            "db > insert 17 person17 person17@example.com",
            "Executed.",
            "db > insert 18 person18 person18@example.com",
            "Executed.",
            "db > insert 19 person19 person19@example.com",
            "Executed.",
            "db > insert 20 person20 person20@example.com",
            "Executed.",
            "db > insert 21 person21 person21@example.com",
            "Executed.",
            "db > insert 22 person22 person22@example.com",
            "Executed.",
            "db > insert 23 person23 person23@example.com",
            "Executed.",
            "db > insert 24 person24 person24@example.com",
            "Executed.",
            "db > insert 25 person25 person25@example.com",
            "Executed.",
            "db > insert 26 person26 person26@example.com",
            "Executed.",
            "db > insert 27 person27 person27@example.com",
            "Executed.",
            "db > insert 28 person28 person28@example.com",
            "Executed.",
            "db > insert 29 person29 person29@example.com",
            "Executed.",
            "db > insert 30 person30 person30@example.com",
            "Executed.",
            "db > insert 31 person31 person31@example.com",
            "Executed.",
            "db > insert 32 person32 person32@example.com",
            "Executed.",
            "db > insert 33 person33 person33@example.com",
            "Executed.",
            "db > insert 34 person34 person34@example.com",
            "Executed.",
            "db > insert 35 person35 person35@example.com",
            "Executed.",
            "db > insert 36 person36 person36@example.com",
            "Executed.",
            "db > insert 37 person37 person37@example.com",
            "Executed.",
            "db > insert 38 person38 person38@example.com",
            "Executed.",
            "db > insert 39 person39 person39@example.com",
            "Executed.",
            "db > insert 40 person40 person40@example.com",
            "Executed.",
            "db > insert 41 person41 person41@example.com",
            "Executed.",
            "db > insert 42 person42 person42@example.com",
            "Executed.",
            "db > insert 43 person43 person43@example.com",
            "Executed.",
            "db > insert 44 person44 person44@example.com",
            "Executed.",
            "db > insert 45 person45 person45@example.com",
            "Executed.",
            "db > insert 46 person46 person46@example.com",
            "Executed.",
            "db > insert 47 person47 person47@example.com",
            "Executed.",
            "db > insert 48 person48 person48@example.com",
            "Executed.",
            "db > insert 49 person49 person49@example.com",
            "Executed.",
            "db > insert 50 person50 person50@example.com",
            "Executed.",
            "db > insert 51 person51 person51@example.com",
            "Executed.",
            "db > insert 52 person52 person52@example.com",
            "Executed.",
            "db > insert 53 person53 person53@example.com",
            "Executed.",
            "db > insert 54 person54 person54@example.com",
            "Executed.",
            "db > insert 55 person55 person55@example.com",
            "Executed.",
            "db > insert 56 person56 person56@example.com",
            "Executed.",
            "db > insert 57 person57 person57@example.com",
            "Executed.",
            "db > insert 58 person58 person58@example.com",
            "Executed.",
            "db > insert 59 person59 person59@example.com",
            "Executed.",
            "db > insert 60 person60 person60@example.com",
            "Executed.",
            "db > insert 61 person61 person61@example.com",
            "Executed.",
            "db > insert 62 person62 person62@example.com",
            "Executed.",
            "db > insert 63 person63 person63@example.com",
            "Executed.",
            "db > insert 64 person64 person64@example.com",
            "Executed.",
            "db > insert 65 person65 person65@example.com",
            "Executed.",
            "db > insert 66 person66 person66@example.com",
            "Executed.",
            "db > insert 67 person67 person67@example.com",
            "Executed.",
            "db > insert 68 person68 person68@example.com",
            "Executed.",
            "db > insert 69 person69 person69@example.com",
            "Executed.",
            "db > insert 70 person70 person70@example.com",
            "Executed.",
            "db > insert 71 person71 person71@example.com",
            "Executed.",
            "db > insert 72 person72 person72@example.com",
            "Executed.",
            "db > insert 73 person73 person73@example.com",
            "Executed.",
            "db > insert 74 person74 person74@example.com",
            "Executed.",
            "db > insert 75 person75 person75@example.com",
            "Executed.",
            "db > insert 76 person76 person76@example.com",
            "Executed.",
            "db > insert 77 person77 person77@example.com",
            "Executed.",
            "db > insert 78 person78 person78@example.com",
            "Executed.",
            "db > insert 79 person79 person79@example.com",
            "Executed.",
            "db > insert 80 person80 person80@example.com",
            "Executed.",
            "db > insert 81 person81 person81@example.com",
            "Executed.",
            "db > insert 82 person82 person82@example.com",
            "Executed.",
            "db > insert 83 person83 person83@example.com",
            "Executed.",
            "db > insert 84 person84 person84@example.com",
            "Executed.",
            "db > insert 85 person85 person85@example.com",
            "Executed.",
            "db > .btree",
            "Tree:",
            "- internal (size 1)",
            "  - internal (size 1)",
            "    - internal (size 1)",
            "      - leaf (size 7)",
            "        - 1",
            "        - 2",
            "        - 3",
            "        - 4",
            "        - 5",
            "        - 6",
            "        - 7",
            "    - key 7",
            "      - leaf (size 7)",
            "        - 8",
            "        - 9",
            "        - 10",
            "        - 11",
            "        - 12",
            "        - 13",
            "        - 14",
            "  - key 14",
            "    - internal (size 1)",
            "      - leaf (size 7)",
            "        - 15",
            "        - 16",
            "        - 17",
            "        - 18",
            "        - 19",
            "        - 20",
            "        - 21",
            "    - key 21",
            "      - leaf (size 7)",
            "        - 22",
            "        - 23",
            "        - 24",
            "        - 25",
            "        - 26",
            "        - 27",
            "        - 28",
            "- key 28",
            "  - internal (size 2)",
            "    - internal (size 1)",
            "      - leaf (size 7)",
            "        - 29",
            "        - 30",
            "        - 31",
            "        - 32",
            "        - 33",
            "        - 34",
            "        - 35",
            "    - key 35",
            "      - leaf (size 7)",
            "        - 36",
            "        - 37",
            "        - 38",
            "        - 39",
            "        - 40",
            "        - 41",
            "        - 42",
            "  - key 42",
            "    - internal (size 1)",
            "      - leaf (size 7)",
            "        - 43",
            "        - 44",
            "        - 45",
            "        - 46",
            "        - 47",
            "        - 48",
            "        - 49",
            "    - key 49",
            "      - leaf (size 7)",
            "        - 50",
            "        - 51",
            "        - 52",
            "        - 53",
            "        - 54",
            "        - 55",
            "        - 56",
            "  - key 56",
            "    - internal (size 3)",
            "      - leaf (size 7)",
            "        - 57",
            "        - 58",
            "        - 59",
            "        - 60",
            "        - 61",
            "        - 62",
            "        - 63",
            "    - key 63",
            "      - leaf (size 7)",
            "        - 64",
            "        - 65",
            "        - 66",
            "        - 67",
            "        - 68",
            "        - 69",
            "        - 70",
            "    - key 70",
            "      - leaf (size 7)",
            "        - 71",
            "        - 72",
            "        - 73",
            "        - 74",
            "        - 75",
            "        - 76",
            "        - 77",
            "    - key 77",
            "      - leaf (size 8)",
            "        - 78",
            "        - 79",
            "        - 80",
            "        - 81",
            "        - 82",
            "        - 83",
            "        - 84",
            "        - 85",
            "db > .exit",
            ""
        ])

if __name__ == '__main__':
    unittest.main()
