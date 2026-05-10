#include <iostream>

void someFunction(int x) {
    int unused = 10; // Неиспользуемая переменная
    if (x == 0) {
        std::cout << "Zero" << std::endl;
    }
}

int main() {
    someFunction(5);
    return 0;
}
