"""Use the standard library and handle expected errors explicitly."""

import random


def ask_for_whole_number(prompt):
    """Keep asking until the user enters a whole number."""
    while True:
        answer = input(prompt)
        try:
            return int(answer)
        except ValueError:
            print("Please enter a whole number.")


print("A random die roll:", random.randint(1, 6))

"""
Exercises:
1. Import the `math` module and use it to calculate a circle's area.
2. Write a function that converts text to a number and reports invalid input.
3. Add a maximum number of attempts to ask_for_whole_number().
4. Put a useful function in a separate file and import it into another script.
"""
