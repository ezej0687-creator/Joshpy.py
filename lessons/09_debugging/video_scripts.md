# Module 09: Debugging — Video Scripts

Here are three short video scripts (2–3 minutes each) to accompany this module. You can record these using OBS Studio, QuickTime, or Loom.

---

## Video 1: How to Read a Traceback
**Length:** 2 minutes
**Goal:** Teach the viewer to read errors bottom-up.

**[0:00] — Intro**
"Hi, I'm [Your Name], and this is Joshpy. Today we're talking about tracebacks. When Python crashes, it gives you a wall of red text. Most beginners read it top-down. Today, I'm going to show you why you should read it bottom-up."

**[0:30] — Show the Bug**
(On screen: A simple Python script that divides by zero)

def divide(a, b):
    return a / b

result = divide(10, 0)
print(result)

"If I run this, Python throws a ZeroDivisionError."

**[0:50] — Show the Traceback**
(Show the terminal output)
"Look at this. If you read top-down, you see a bunch of file paths and lines. But look at the very bottom. ZeroDivisionError: division by zero. That tells you exactly what happened. Now look one line above it. It shows return a / b. That tells you exactly where it happened."

**[1:30] — The Fix**
"To fix this, I don't need to rewrite the whole program. I just need to handle the specific case where b is zero. I can add an if statement, or use a try/except block. But the important part is: I knew where to look immediately."

**[1:50] — Outro**
"Read from the bottom. That's the rule. In the next video, we'll look at the bugs that don't crash your program, but silently give you the wrong answer."

---

## Video 2: The Silent Killers (Common Bugs)
**Length:** 2.5 minutes
**Goal:** Explain mutable defaults and truthiness traps.

**[0:00] — Intro**
"Welcome back. Crashes are annoying, but the bugs that don't crash are worse. They silently give you the wrong answer. Let's look at two of the most common ones."

**[0:20] — Mutable Defaults**
(On screen: A function with a default list)

def add_item(item, my_list=[]):
    my_list.append(item)
    return my_list

print(add_item(1)) # [1]
print(add_item(2)) # [2]? No, it's [1, 2]!

"When you use an empty list as a default argument, Python creates it once when the function is defined, not every time it's called. So the list gets shared across every call. The fix? Use None as the default, and create the list inside the function."

**[1:10] — The Truthiness Trap**
(On screen: A function checking if a number is zero)

def check_zero(num):
    if not num:
        return "Zero"
    return "Not zero"

print(check_zero(0))    # Zero (correct)
print(check_zero(False)) # Zero (Is False zero? No!)

"In Python, 0, False, empty strings, and empty lists all evaluate to False. If you use if not x:, you might catch things you didn't mean to. Be explicit: use if x == 0: or if x is False:."

**[2:10] — Outro**
"Being explicit saves you hours of debugging. In the final video, we'll look at the tool that lets you pause time: the debugger."

---

## Video 3: The Debugger
**Length:** 2 minutes
**Goal:** Show breakpoint() and stepping through code.

**[0:00] — Intro**
"Print statements are fine, but they require you to guess what you want to see. The debugger lets you pause your code mid-execution and look at everything."

**[0:20] — Setting a Breakpoint**
(On screen: A script that loops and calculates)

def calculate():
    total = 0
    for i in range(5):
        breakpoint() # <--- Add this here
        total += i
    return total

print(calculate())

"If I put breakpoint() in my code and run it, Python pauses right here."

**[0:50] — Using the Debugger**
(Show the terminal prompt (Pdb))
"Now I can type p total to see what the total is. I can type n to go to the next line. I can type p i to see what the loop variable is. This lets you see exactly what the code is doing at every step, without cluttering your code with print statements."

**[1:30] — Continue and Quit**
"When you're done looking, you can type c to continue running the code, or q to quit. The debugger is built into Python, so you can use it anywhere, anytime."

**[1:50] — Outro**
"That wraps up Module 09. You know how to read errors, spot silent bugs, and use the debugger. Try the capstone project next, and I'll see you in the next module."
