"""Represent a thing and its behavior with a class."""


class Book:
    def __init__(self, title, author):
        self.title = title
        self.author = author
        self.is_checked_out = False

    def check_out(self):
        self.is_checked_out = True

    def return_book(self):
        self.is_checked_out = False


book = Book("A Python Book", "Alex Reader")
book.check_out()
print(f"{book.title} checked out: {book.is_checked_out}")
book.return_book()
print(f"{book.title} checked out: {book.is_checked_out}")

"""
Exercises:
1. Add a method that returns a readable description of a book.
2. Create a Library class that stores books and can find one by title.
3. Decide which behavior belongs on Book and which belongs on Library.
4. Add a rule that prevents checking out an already checked-out book.
"""
