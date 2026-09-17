Tengo que correjir que cuando un id es negativo o cuando una palabra es muy grande el programa crashea en vez de tener un error.

..FF.
======================================================================
FAIL: test_prints_error_message_if_id_is_negative (__main__.TestDatabase.test_prints_error_message_if_id_is_negative)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/simple_sqlite_clone/test.py", line 84, in test_prints_error_message_if_id_is_negative
    self.assertEqual(result, [
    ~~~~~~~~~~~~~~~~^^^^^^^^^^
        "db > ID must be positive.",
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
        "db > Executed.",
        ^^^^^^^^^^^^^^^^^
        "db > ",
        ^^^^^^^^
    ])
    ^^
AssertionError: Lists differ: ['db > '] != ['db > ID must be positive.', 'db > Executed.', 'db > ']

First differing element 0:
'db > '
'db > ID must be positive.'

Second list contains 2 additional elements.
First extra element 1:
'db > Executed.'

- ['db > ']
+ ['db > ID must be positive.', 'db > Executed.', 'db > ']

======================================================================
FAIL: test_prints_error_message_if_strings_are_too_long (__main__.TestDatabase.test_prints_error_message_if_strings_are_too_long)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/simple_sqlite_clone/test.py", line 70, in test_prints_error_message_if_strings_are_too_long
    self.assertEqual(result, [
    ~~~~~~~~~~~~~~~~^^^^^^^^^^
        "db > String is too long.",
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^
        "db > Executed.",
        ^^^^^^^^^^^^^^^^^
        "db > ",
        ^^^^^^^^
    ])
    ^^
AssertionError: Lists differ: ['db > '] != ['db > String is too long.', 'db > Executed.', 'db > ']

First differing element 0:
'db > '
'db > String is too long.'

Second list contains 2 additional elements.
First extra element 1:
'db > Executed.'

- ['db > ']
+ ['db > String is too long.', 'db > Executed.', 'db > ']

----------------------------------------------------------------------
Ran 5 tests in 0.564s

FAILED (failures=2)
