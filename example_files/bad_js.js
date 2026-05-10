function checkProject(name) {
    const unused = "I am not used";
    
    // ESLint должен найти console.log и отсутствие использования переменных
    console.log("Checking project: " + name);

    if (name == "admin") { // Использование == вместо ===
        return true
    }

    // Ошибка: переменная не объявлена
    undefinedVariable = 100;

    return false;
}

checkProject("test");
