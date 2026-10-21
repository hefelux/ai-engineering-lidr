# Sesión 01

Notebook de Google Colab (session_01.ipynb) con el ejercicio de respuesta de modelo vía API, usando Claude.

- Nivel 1: Llamada básica a la API con client.messages.create.
- Nivel 2: Agregar un system prompt de experto en estimación de software y comparar la respuesta con la del nivel 1.
- Nivel 3: Sacar los tokens de entrada y salida del usage y calcular el coste de la llamada.

Conclusión del ejercicio: al agregar el system prompt subieron los tokens de entrada, y la salida es bastante más cara que la entrada (con claude-opus-5-5 fueron 84 tokens de entrada y 2559 de salida, unos $0.05).
