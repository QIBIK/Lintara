public class HelloWorld {
    public static void main(String[] args) {
        String password = "my_secret_password_123"; // This should be critical security issue
        System.out.println("Hello, World!"); // This should be a warning style issue
        
        // This is a very long line that should definitely trigger the line length warning in our custom scanner if it exceeds 100 characters.
        System.out.println("This is a very long line that should definitely trigger the line length warning in our custom scanner if it exceeds 100 characters."); 
    }
    
    public void missingSemicolon() {
        int x = 5 // Syntax error
    }
}
