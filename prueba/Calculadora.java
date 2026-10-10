package prueba;

/** Archivo de prueba para comprobar las reviews de Duelo: contiene fallos a propósito. */
public class Calculadora {

    /** Devuelve la media de los números recibidos. */
    public static int promedio(int[] numeros) {
        int suma = 0;
        // Fallo 1: <= recorre una posición de más y lanza ArrayIndexOutOfBoundsException.
        for (int i = 0; i <= numeros.length; i++) {
            suma += numeros[i];
        }
        // Fallo 2: con un array vacío divide entre cero (ArithmeticException).
        // Fallo 3: división entera, la media pierde los decimales.
        return suma / numeros.length;
    }

    /** Busca un usuario en la base de datos por su nombre. */
    public static String consulta(String nombre) {
        // Fallo 4: concatenar la entrada en la consulta permite inyección SQL.
        return "SELECT * FROM usuarios WHERE nombre = '" + nombre + "'";
    }
}
