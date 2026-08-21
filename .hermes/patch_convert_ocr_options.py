from pathlib import Path

path = Path(r"C:/Users/james/developer/headcleaner-cli/src/headcleaner/cli.py")
text = path.read_text(encoding="utf-8")
old = (
    '        fmt=fmt.lower(),\n'
    '        ocr=ocr,\n'
    '        include_glob=list(include) if include else None,\n'
)
new = (
    '        fmt=fmt.lower(),\n'
    '        ocr=ocr,\n'
    '        ocr_profile=ocr_profile,\n'
    '        ocr_languages=tuple(code.strip() for code in (ocr_lang or "").split(",") if code.strip()),\n'
    '        include_glob=list(include) if include else None,\n'
)
assert text.count(old) == 2
path.write_text(text.replace(old, new, 1), encoding="utf-8")
