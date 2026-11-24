#!/usr/bin/env bash
# Build the report: docs/informe/NN-*.md -> build/TPFinal_SOR2_2026_2s_VelizLuis.docx
# Requires pandoc and python3. Use --word for the final PDF from Microsoft Word.
# The table of contents field follows the executive summary in 01-resumen.md.
set -euo pipefail

case "${1:-}" in
  "") mode=preview ;;
  --word) mode=word ;;
  *) echo "Usage: $0 [--word]" >&2; exit 2 ;;
esac
if (( $# > 1 )); then
  echo "Usage: $0 [--word]" >&2
  exit 2
fi

here="$(cd "$(dirname "$0")" && pwd)"
out_dir="$here/build"
ref="$out_dir/reference.docx"
out="$out_dir/TPFinal_SOR2_2026_2s_VelizLuis.docx"
mkdir -p "$out_dir"

# Reference document: pandoc's default styles restyled by style_reference.py (A4, Calibri 11, footer, tables).
pandoc -o "$ref" --print-default-data-file reference.docx
python3 "$here/style_reference.py" reference "$ref"

mapfile -t chapters < <(find "$here" -maxdepth 1 -name '[0-9][0-9]-*.md' | sort)
if [ "${#chapters[@]}" -eq 0 ]; then
  echo "No chapters found in $here" >&2
  exit 1
fi

cd "$here"
pandoc "${chapters[@]}" \
  --from markdown \
  --reference-doc "$ref" \
  --resource-path "$here" \
  --metadata lang=es-AR \
  -o "$out"

# Post-process: table column widths (see style_reference.py).
python3 "$here/style_reference.py" post "$out"

echo "chapters: ${#chapters[@]}, written to $out"

if [[ "$mode" == word ]]; then
  tmp="$(mktemp -d "$out_dir/word.XXXXXXXX")"
  trap 'rmdir "$tmp" 2>/dev/null || true' EXIT
  candidate="$tmp/candidate.pdf"
  powershell.exe -NoProfile -File "$(wslpath -w "$here/word_export.ps1")" \
    -Docx "$(wslpath -w "$out")" -Pdf "$(wslpath -w "$candidate")"
  LC_ALL=C pdfinfo "$candidate" | grep -E '^Creator:.*Microsoft.*Word'
  LC_ALL=C pdffonts "$candidate" | awk '/Calibri/ && $(NF-4)=="yes" {found=1} END{exit !found}'
  final="$here/$(basename "${out%.docx}").pdf"
  mv -- "$candidate" "$final"
  echo "final pdf: $final"
  exit 0
fi

# LibreOffice is only for previews; it never writes to the delivery path.
soffice="$(command -v libreoffice || command -v soffice || true)"
if [ -n "$soffice" ]; then
  pdf_out="$out_dir/preview.pdf"
  python3 "$here/export_pdf.py" "$soffice" "$out" "$pdf_out"
  echo "preview pdf: $pdf_out"
else
  echo "LibreOffice not found: skipped the preview PDF"
fi
