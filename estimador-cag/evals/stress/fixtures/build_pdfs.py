"""Genera los PDF de prueba de 5, 20, 50 y 100 KB de texto.

Siempre salen iguales (no hay nada al azar), por eso no se suben al repo:
el runner los vuelve a generar si no estan.

Cada PDF trae dos datos para medir si el modelo los ve:
- al principio: el pago es con Stripe
- al final: los eventos van por Kafka
El adjunto se corta en 20.000 caracteres (MAX_CHARS_PER_FILE), asi que en los
PDF grandes el dato del final se pierde. Eso es parte de lo que se mide.

Uso: uv run python -m evals.stress.fixtures.build_pdfs
"""

from pathlib import Path

from fpdf import FPDF

FOLDER = Path(__file__).parent
SIZES_KB = [5, 20, 50, 100]

START = "Requisito principal: los pagos con tarjeta se procesan con Stripe.\n"
END = "Requisito final: todos los eventos del sistema se publican en Kafka.\n"

# Parrafos de relleno que parecen un documento de requisitos
FILLER = [
    "El sistema permite a los usuarios crear una cuenta con correo y contraseña.",
    "Cada pedido guarda la fecha, el cliente, los productos y el estado del envío.",
    "El panel de administración muestra las ventas del día y de la semana.",
    "Los reportes se pueden exportar a CSV desde la pantalla de pedidos.",
    "Las notificaciones se envían por correo cuando cambia el estado del pedido.",
    "El catálogo tiene categorías, filtros por precio y búsqueda por nombre.",
    "Los administradores pueden dar de alta productos con foto y descripción.",
    "La aplicación debe funcionar en el navegador del teléfono y del computador.",
]


def build_text(size_kb):
    target = size_kb * 1024
    lines = [START]
    total = len(START) + len(END)
    number = 1
    while total < target:
        line = f"{number}. {FILLER[number % len(FILLER)]}\n"
        lines.append(line)
        total += len(line)
        number += 1
    lines.append(END)
    return "".join(lines)


def build_pdf(size_kb):
    pdf = FPDF()
    pdf.set_auto_page_break(True, margin=15)
    pdf.add_page()
    pdf.set_font("helvetica", size=10)
    pdf.multi_cell(0, 5, build_text(size_kb))
    path = FOLDER / f"attach_{size_kb}kb.pdf"
    pdf.output(str(path))
    return path


# Devuelve la ruta del PDF y lo crea si todavia no existe
def get_pdf(size_kb):
    path = FOLDER / f"attach_{size_kb}kb.pdf"
    if not path.exists():
        build_pdf(size_kb)
    return path


if __name__ == "__main__":
    for size in SIZES_KB:
        path = build_pdf(size)
        print(f"{path.name}: {path.stat().st_size // 1024} KB de archivo")
