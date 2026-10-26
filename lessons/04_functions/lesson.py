"""Package reusable behavior into functions."""


def rectangle_area(width, height):
    """Return the area of a rectangle."""
    return width * height


def greet(name="friend"):
    """Return a friendly greeting."""
    return f"Hello, {name}!"


print(greet("Sam"))
print(greet())
print("Area:", rectangle_area(4, 3))

"""
Exercises:
1. Write a function that converts Celsius to Fahrenheit and returns the result.
2. Write a function that returns the largest of three numbers.
3. Write a function that accepts a list of numbers and returns their average.
4. Split your number guessing game into small functions with clear names.
"""
