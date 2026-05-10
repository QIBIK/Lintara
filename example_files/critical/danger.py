def dangerous_function(user_input):
    exec(user_input) # КРИТИЧЕСКАЯ УЯЗВИМОСТЬ

def very_complex(a, b, c, d):
    # Ранг C/D
    if a:
        for i in range(10):
            if i % 2:
                for j in range(5):
                    if j > 2:
                        if c:
                            while d < 10:
                                d += 1
                                if d == 5: print("Mid")
    return a + b
