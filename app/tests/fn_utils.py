import time
import itertools

def no_op():
    return "DONE"

def sleep_1s():
    time.sleep(1)
    return "Slept"

def sleep_n(n):
    time.sleep(n)
    return f"Slept for {n} seconds"

def double(x):
    return x * 2

def fibonacci(n):
    if n <= 1:
        return n
    else:
        return fibonacci(n-1) + fibonacci(n-2)

def bruteforce_password(hashed_password, max_length):
    """
    Crack a password hash using brute force.
    Only use ascii lowercase characters for simplicity.

    Usage:
    bruteforce_password('cce6b3fb87d8237167f1c5dec15c3133', 4) #mpcs
    """
    # echo -n mpcs | md5sum
    import string
    import hashlib
    chars = string.ascii_lowercase  # Only lowercase letters for simplicity
    current_index = 0
    end_index = sum(len(chars) ** i for i in range(1, max_length + 1))

    for password_length in range(1, max_length + 1):
        for guess_tuple in itertools.product(chars, repeat=password_length):
            # join the combination of characters to form a guess
            guess = ''.join(guess_tuple)
            hashed_guess = hashlib.md5(guess.encode()).hexdigest()
            if hashed_guess == hashed_password:
                return guess
            current_index += 1
            if current_index >= end_index:
                return None