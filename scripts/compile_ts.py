#!/usr/bin/env python3
"""Compile .ts files to .qm format using PyQt6."""

import sys
import xml.etree.ElementTree as ET
from pathlib import Path

def parse_ts_file(ts_path: Path) -> dict[str, str]:
    """Parse .ts file and extract translations."""
    translations = {}
    
    try:
        tree = ET.parse(ts_path)
        root = tree.getroot()
        
        for context in root.findall('.//context'):
            for message in context.findall('message'):
                source = message.find('source')
                translation = message.find('translation')
                
                if source is not None and translation is not None:
                    source_text = source.text or ""
                    trans_text = translation.text or source_text
                    
                    # Конвертируем литеральные escape-последовательности в реальные символы
                    # \n (2 символа: \ + n) → символ новой строки (0x0A)
                    source_text = source_text.replace("\\n", "\n").replace("\\t", "\t").replace("\\r", "\r")
                    trans_text = trans_text.replace("\\n", "\n").replace("\\t", "\t").replace("\\r", "\r")
                    
                    if source_text:
                        translations[source_text] = trans_text
    except Exception as e:
        print(f"Error parsing {ts_path}: {e}")
    
    return translations


def create_qm_from_ts(ts_path: Path, qm_path: Path):
    """Create a simple QM-like binary file from TS."""
    translations = parse_ts_file(ts_path)
    
    # QM format is binary and complex, so we'll create a JSON-based alternative
    # that our Translator can load
    import json
    
    data = {
        "language": ts_path.stem,
        "translations": translations
    }
    
    # Create .qm as JSON (our custom format for simplicity)
    with open(qm_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"Created {qm_path} with {len(translations)} translations")


def main():
    translations_dir = Path(__file__).parent.parent / "translations"
    
    if not translations_dir.exists():
        print(f"Error: {translations_dir} not found")
        sys.exit(1)
    
    ts_files = list(translations_dir.glob("*.ts"))
    
    if not ts_files:
        print("No .ts files found")
        sys.exit(1)
    
    for ts_file in ts_files:
        qm_file = ts_file.with_suffix(".qm")
        create_qm_from_ts(ts_file, qm_file)
    
    print(f"\nCompiled {len(ts_files)} files")


if __name__ == "__main__":
    main()
