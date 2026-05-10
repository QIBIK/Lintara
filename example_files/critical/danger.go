package main

import "fmt"

func main() {
	var x int
	if true {
		x = 10
	}
	// x используется, но staticcheck может найти другие проблемы
	fmt.Println(x)
	
	for {
		// Бесконечный цикл без выхода (иногда считается плохой практикой)
		break
	}
}

func unusedFunction() {
	// Эту функцию никто не вызывает
}
