"""
Disegna l'icona di Blueprint (blueprint.ico): un segno di integrale bianco su carta blu,
con il bordo tratteggiato da disegno tecnico e un punto giallo. Usata dal programma e dall'installer.
"""

from pathlib import Path

from PIL import Image, ImageDraw

BLU, AZZURRINO, BIANCO, GIALLO = (11, 61, 145), (169, 200, 245), (244, 248, 255), (255, 216, 102)


def disegna(lato: int) -> Image.Image:
    # Disegniamo in grande (4x) e poi rimpiccioliamo: i bordi vengono più morbidi
    s = lato * 4
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, s - 1, s - 1], radius=s // 8, fill=BLU)

    # Bordo tratteggiato
    margine, tratto = s // 10, max(2, s // 64)
    passo = s // 16
    for t in range(margine, s - margine, passo * 2):
        fine = min(t + passo, s - margine)
        for linea in (
            [(t, margine), (fine, margine)],
            [(t, s - margine), (fine, s - margine)],
            [(margine, t), (margine, fine)],
            [(s - margine, t), (s - margine, fine)],
        ):
            d.line(linea, fill=AZZURRINO, width=tratto)

    # Segno di integrale: una "S" allungata fatta con due archi e un tratto obliquo
    spessore = s // 11
    d.arc([s * 0.47, s * 0.16, s * 0.71, s * 0.40], start=190, end=340, fill=BIANCO, width=spessore)
    d.line([(s * 0.535, s * 0.30), (s * 0.465, s * 0.70)], fill=BIANCO, width=spessore)
    d.arc([s * 0.29, s * 0.60, s * 0.53, s * 0.84], start=10, end=160, fill=BIANCO, width=spessore)

    # Punto giallo (il colore d'accento dell'app)
    r = s * 0.075
    d.ellipse([s * 0.72 - r, s * 0.72 - r, s * 0.72 + r, s * 0.72 + r], fill=GIALLO)
    return img.resize((lato, lato), Image.LANCZOS)


if __name__ == "__main__":
    destinazione = Path(__file__).resolve().parent / "blueprint.ico"
    grande = disegna(256)
    grande.save(destinazione, sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    grande.save(destinazione.with_suffix(".png"))  # anteprima, comoda da guardare
    print("Icona creata:", destinazione)
