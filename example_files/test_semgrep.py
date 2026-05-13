import os

def insecure_function(user_input):
    # This should be caught by our new semgrep rule
    os.system("ls " + user_input)

def another_one():
    password = "password123" # Should be caught by generic rule
    print(password)

if __name__ == "__main__":
    insecure_function("test")
