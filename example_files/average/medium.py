import sys # Неиспользуемый импорт

def complex_ish_logic(n):
    # Умеренная сложность (Ранг B)
    count = 0
    for i in range(n):
        if i % 2 == 0:
            for j in range(5):
                if j > 2:
                    count += 1
    return count

res = complex_ish_logic(10)
print(res)
