# Appunti sui limiti (file di esempio per provare il Magazzino)

Definizione. Sia f una funzione definita in un intorno di x0. Si dice che f(x) tende a L
per x che tende a x0 se per ogni epsilon > 0 esiste delta > 0 tale che
0 < |x - x0| < delta implica |f(x) - L| < epsilon.

Teorema (di de l'Hôpital). Siano f e g derivabili in un intorno di x0, con g'(x) diverso da 0.
Se il limite di f(x)/g(x) si presenta nella forma indeterminata 0/0 oppure infinito/infinito
ed esiste il limite di f'(x)/g'(x), allora i due limiti coincidono.

Teorema (del confronto). Se g(x) <= f(x) <= h(x) in un intorno di x0 e i limiti di g e h
per x che tende a x0 valgono entrambi L, allora anche il limite di f vale L.

Metodo. Per risolvere una forma indeterminata 0/0 con funzioni trigonometriche conviene
ricondursi ai limiti notevoli, moltiplicando e dividendo per la quantità opportuna.

Esempio. Limite notevole: il limite di sin(x)/x per x che tende a 0 vale 1.
Di conseguenza il limite di (1 - cos(x))/x^2 per x che tende a 0 vale 1/2.

Esercizio svolto. Calcolare il limite di (e^x - 1)/x per x che tende a 0.
Svolgimento: la forma è 0/0. Applicando il teorema di de l'Hôpital si deriva numeratore e
denominatore: il limite diventa quello di e^x/1, che vale 1.
