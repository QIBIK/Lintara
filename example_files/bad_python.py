import os
import sys

# 1. СТИЛЬ И ОШИБКИ
unused_var = 42

def hello():
    print("Hello world")

# 2. БЕЗОПАСНОСТЬ (Bandit найдет exec и пароль)
def run_dangerous_code(user_input):
    exec(user_input) # КРИТИЧЕСКАЯ УЯЗВИМОСТЬ

DB_PASSWORD = "super_secret_password_123" # ХАРДКОД СЕКРЕТА

# 3. ЭКСТРЕМАЛЬНАЯ СЛОЖНОСТЬ (Для гарантированного ранга C/D)
def crazy_complex_function(a, b, c, d, e):
    # Огромное дерево вложенности для повышения цикломатической сложности
    res = 0
    if a > 0:
        if b > 0:
            for i in range(10):
                if i % 2 == 0:
                    for j in range(5):
                        if j > 2:
                            if i + j == 7: res += 1
                            elif i - j == 1: res += 2
                            else: res += 3
                        else:
                            if c > 10: res += 4
                            else: res += 5
                else:
                    if d:
                        for k in range(3):
                            if k == e: res *= 2
                            else: res -= 1
                    else: res += 10
    else:
        if e < 0:
            while res < 100:
                res += 1
                if res % 10 == 0:
                    if a + b < 0: break
    return res
