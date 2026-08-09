from ocr_reader import extract_text_ocr


def extract_after_label(texto, etiqueta):
    lines = texto.splitlines()

    for i, line in enumerate(lines):
        if etiqueta in line:
            for siguiente in lines[i + 1:]:
                siguiente = siguiente.strip()

                if siguiente:
                    return siguiente

    return ""


pdf = "data/input/Detalle_del_movimiento__A.pdf"

texto = extract_text_ocr(pdf)

titular = extract_after_label(texto, "Titular de la tarjeta")

print("Titular encontrado:", titular)