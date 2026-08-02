import base64
import re
import sys


def process_comments(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Base64 decoding
    # Szukamy ciągów znaków (A-Za-z0-9+/=) o długości min 40, bez białych znaków,
    # które można poprawnie zdekodować jako UTF-8 i mają sens.
    b64_pattern = re.compile(r'\b[A-Za-z0-9+/=]{40,}\b')

    def b64_replace(match):
        encoded = match.group(0)
        try:
            # Pad if necessary
            missing_padding = len(encoded) % 4
            if missing_padding:
                encoded += '=' * (4 - missing_padding)
            decoded_bytes = base64.b64decode(encoded, validate=True)
            decoded_str = decoded_bytes.decode('utf-8')
            # Only replace if decoded string seems like text (e.g. contains spaces, printable chars)
            if re.search(r'[a-zA-Z0-9]', decoded_str) and len(decoded_str) > 5:
                return f"{match.group(0)}\n[DECODED_BASE64]: {decoded_str}\n"
        except Exception:
            pass
        return match.group(0)

    content = b64_pattern.sub(b64_replace, content)

    # 2. Thread grouping
    threads = []
    current_thread = []

    for line in content.splitlines():
        if line.startswith('--- Komentarz od:'):
            if current_thread:
                threads.append('\n'.join(current_thread))
            current_thread = [line]
        else:
            current_thread.append(line)
    if current_thread:
         threads.append('\n'.join(current_thread))

    # Wrap each thread in <THREAD> tags
    final_content = []
    for t in threads:
        if t.strip():
            final_content.append(f"<THREAD>\n{t}\n</THREAD>\n")

    return "\n".join(final_content)

if __name__ == '__main__':
    if len(sys.argv) < 2:
         print("Usage: python preprocess_comments.py <file.md>")
         sys.exit(1)

    input_file = sys.argv[1]
    output_content = process_comments(input_file)
    output_file = input_file.replace('.md', '_preprocessed.md')

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(output_content)

    print(f"Preprocessed {input_file} into {output_file}")
