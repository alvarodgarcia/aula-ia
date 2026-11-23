"""Bounded avatar decoding. Store a small, metadata-free derivative, never the original."""
import io
import warnings
from PIL import Image, ImageOps, UnidentifiedImageError

MAX_BYTES = 5 * 1024 * 1024
MAX_PIXELS = 25_000_000
MAX_STORED = 128 * 1024


def normalize(payload):
    if not payload or len(payload) > MAX_BYTES:
        raise ValueError('Elige una foto de hasta 5 MB.')
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error', Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(payload)) as source:
                if source.format not in {'JPEG', 'PNG', 'WEBP', 'HEIF'}:
                    raise ValueError('Elige una foto JPG, PNG, WebP o HEIC, sin animación.')
                if source.width * source.height > MAX_PIXELS or max(source.size) > 10000:
                    raise ValueError('La foto tiene demasiada resolución. Elige una versión más pequeña.')
                if getattr(source, 'n_frames', 1) != 1:
                    raise ValueError('Elige una foto estática, sin animación.')
                source.draft('RGB', (1280, 1280))
                oriented = ImageOps.exif_transpose(source)
                cropped = ImageOps.fit(oriented, (320, 320), method=Image.Resampling.LANCZOS)
                rgba = cropped.convert('RGBA')
                background = Image.new('RGBA', rgba.size, 'white')
                background.alpha_composite(rgba)
                image = background.convert('RGB')
                image.info.clear()
                out = io.BytesIO()
                image.save(out, format='JPEG', quality=85, optimize=True)
                result = out.getvalue()
                if len(result) > MAX_STORED:
                    raise ValueError('No se pudo reducir la foto. Prueba con otra imagen.')
                return result
    except (UnidentifiedImageError, OSError, SyntaxError, Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
        raise ValueError('No se pudo leer la foto. Prueba con una imagen JPG o PNG válida.') from exc
