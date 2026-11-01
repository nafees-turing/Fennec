import hashlib
from pathlib import Path

from app.modules.base import Finding, ModuleResult, ModuleSpec

SPEC = ModuleSpec(
    id="metadata",
    title="File metadata",
    milestone="M6",
    summary="Local file only: hash, type, and EXIF. No network.",
    input_label="File",
    placeholder="",
    available=True,
    input_kind="file",
    network=False,
)

EXIF_TAGS = {"DateTime", "DateTimeOriginal", "Make", "Model", "Software", "Artist", "ImageDescription"}


def run(raw: str) -> ModuleResult:
    path = Path(raw)
    if not path.is_file():
        return ModuleResult(status="failed", error="Choose a file to inspect on this machine.")

    data = path.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    findings = [
        Finding("file", path.name, "fennec", "high", f"{len(data)} bytes"),
        Finding("hash", digest, "sha256", "high", "SHA-256 of the file bytes"),
    ]
    try:
        from PIL import Image
        from PIL.ExifTags import TAGS

        with Image.open(path) as img:
            findings.append(
                Finding("format", f"{img.format} {img.size[0]}x{img.size[1]}", "Pillow", "high", img.mode)
            )
            exif = img.getexif()
            for tag_id, value in exif.items():
                name = TAGS.get(tag_id, str(tag_id))
                if name in EXIF_TAGS and value not in (None, "", b""):
                    findings.append(Finding("exif", f"{name}={value}", "Pillow", "medium", name))
            if any(TAGS.get(tag_id) == "GPSInfo" for tag_id in exif):
                findings.append(
                    Finding(
                        "gps",
                        "present",
                        "Pillow",
                        "medium",
                        "GPS tags exist in the file. This is not a live location.",
                    )
                )
    except Exception:
        pass
    return ModuleResult(status="ok", findings=findings)
