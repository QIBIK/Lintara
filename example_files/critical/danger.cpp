#include <iostream>

int main() {
    int* ptr = NULL;
    *ptr = 10; // ОШИБКА: Разыменование NULL
    
    char buffer[10];
    sprintf(buffer, "This string is definitely longer than ten characters"); // ПЕРЕПОЛНЕНИЕ БУФЕРА
    
    return 0;
}
