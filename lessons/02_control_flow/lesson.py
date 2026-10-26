"""Make decisions with if statements and repeat work with loops."""

score = 76

if score >= 90:
    print("Grade: A")
elif score >= 80:
    print("Grade: B")
elif score >= 70:
    print("Grade: C")
else:
    print("Keep practicing.")

print("Counting down:")
for number in range(3, 0, -1):
    print(number)
print("Go!")

"""
Exercises:
1. Ask for an age and print whether the person is a child, teen, or adult.
2. Print the numbers from 1 to 20, but label each as even or odd.
3. Use a while loop to keep asking for a password until it matches your choice.
4. Make a number guessing game using a fixed secret number and a limited number
   of guesses.
"""
