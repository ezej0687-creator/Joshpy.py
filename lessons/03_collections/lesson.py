"""Store related values in lists, dictionaries, tuples and sets."""

shopping_list = ["apples", "bread", "tea"]
shopping_list.append("rice")
print("Shopping:", shopping_list)

scores = {"Ari": 8, "Bo": 10}
scores["Cam"] = 7
for player, score in scores.items():
    print(f"{player}: {score}")

unique_tags = {"python", "beginner", "python"}
print("Unique tags:", unique_tags)

location = (51.5, -0.1)
print("Location:", location)

"""
Exercises:
1. Make a list of three favorite foods. Add one, remove one, then print each.
2. Make a dictionary of names and phone numbers; look up a name safely.
3. Count how many times each word appears in a sentence using a dictionary.
4. Store two shopping lists and find which items appear in both using sets.
"""
