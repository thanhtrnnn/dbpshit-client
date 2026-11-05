import json
import re
from html import unescape

def clean_val(v):
    if not v:
        return ""
    v = v.strip()
    # Remove markdown backticks if any
    v = v.strip('`').strip()
    # Remove trailing period if it is not part of a domain (like .edu or .vn) or float
    if v.endswith('.') and not v.endswith('..'):
        # Check if preceded by a letter followed by dot like "Payment."
        if not re.search(r'\.[a-zA-Z]{2,4}\.$', v) and not re.search(r'\d+\.\d+\.$', v):
            v = v[:-1].strip()
    return v

def extract_testcase(desc, proto_type):
    soup = unescape(desc)
    
    # Extract port
    port_match = re.search(r'(?:cổng|port)\s*([0-9]{4,5})', soup, re.IGNORECASE)
    port = int(port_match.group(1)) if port_match else None
    if not port:
        if "2206" in soup: port = 2206
        elif "2207" in soup: port = 2207
        elif "2208" in soup: port = 2208
        elif "2209" in soup: port = 2209
        elif "1099" in soup: port = 1099

    # Clean text by paragraphs
    paragraphs = re.split(r'</?(?:p|div|li|h[1-6])[^>]*>', soup)
    examples = []
    for p in paragraphs:
        p_clean = re.sub(r'<[^>]+>', ' ', p)
        p_clean = re.sub(r'\s+', ' ', p_clean).strip()
        if not p_clean:
            continue
        m = re.search(r'(?:Ví dụ|Ví dụ:|ví dụ)\s*:?\s*(.*)', p_clean, re.IGNORECASE)
        if m:
            val = clean_val(m.group(1))
            if val:
                examples.append(val)

    # All <code> tags
    raw_codes = re.findall(r'<code>(.*?)</code>', soup)
    codes = [clean_val(re.sub(r'<[^>]+>', '', c)) for c in raw_codes if clean_val(re.sub(r'<[^>]+>', '', c))]

    # Handshake format / example
    handshake_format = ""
    handshake_example = ""
    for c in codes:
        if "studentCode" in c and "qCode" in c:
            handshake_format = c
            break
    if not handshake_format:
        for p in paragraphs:
            if "studentCode" in p and "qCode" in p:
                m = re.search(r'([;]?studentCode;qCode)', p)
                if m:
                    handshake_format = m.group(1)
                    break

    # Look for handshake example (e.g. B15DCCN001;... or ;B15DCCN001;...)
    for ex in examples:
        if re.search(r';?[B-Zb-z][0-9]{2}[A-Za-z]{4}[0-9]{3};', ex):
            handshake_example = ex
            break
    if not handshake_example:
        for c in codes:
            if re.search(r';?[B-Zb-z][0-9]{2}[A-Za-z]{4}[0-9]{3};', c):
                handshake_example = c
                break

    # Find server input and client output
    non_handshake_ex = [e for e in examples if e != handshake_example and "studentCode" not in e]
    
    server_input = ""
    expected_output = ""
    
    if len(non_handshake_ex) >= 2:
        server_input = clean_val(non_handshake_ex[0])
        expected_output = clean_val(non_handshake_ex[1])
    elif len(non_handshake_ex) == 1:
        server_input = clean_val(non_handshake_ex[0])
        non_handshake_codes = [c for c in codes if c != handshake_example and c != handshake_format and c != server_input and "studentCode" not in c and "requestId;" not in c[:15] and len(c) > 1]
        if non_handshake_codes:
            expected_output = clean_val(non_handshake_codes[-1])
    else:
        non_handshake_codes = [c for c in codes if c != handshake_example and c != handshake_format and "studentCode" not in c and len(c) > 1]
        if len(non_handshake_codes) >= 2:
            server_input = clean_val(non_handshake_codes[0])
            expected_output = clean_val(non_handshake_codes[1])
        elif len(non_handshake_codes) == 1:
            server_input = clean_val(non_handshake_codes[0])

    return {
        "port": port,
        "handshakeFormat": handshake_format or (";studentCode;qCode" if "UDP" in proto_type else "studentCode;qCode"),
        "handshakeExample": handshake_example or (";B23DCDT024;EXAMPLE" if "UDP" in proto_type else "B23DCDT024;EXAMPLE"),
        "sampleInput": server_input,
        "sampleExpectedOutput": expected_output,
        "allExamples": examples,
        "allCodeTags": codes
    }

def main():
    bank = json.load(open('sample_responses/master_jnp_questions_bank.json', encoding='utf-8'))
    result = {}
    
    for q in bank:
        code = q.get('code')
        if not code:
            continue
        proto = q.get('protocolType', '')
        alias = q.get('alias', '')
        title = q.get('title', '')
        desc = q.get('description', '')
        
        tc = extract_testcase(desc, proto)
        result[str(code)] = {
            "code": code,
            "alias": alias,
            "title": title,
            "protocolType": proto,
            "port": tc["port"],
            "handshakeFormat": tc["handshakeFormat"],
            "handshakeExample": tc["handshakeExample"],
            "sampleInput": tc["sampleInput"],
            "sampleExpectedOutput": tc["sampleExpectedOutput"],
            "allExamples": tc["allExamples"],
            "allCodeTags": tc["allCodeTags"]
        }

    out_file = 'sample_responses/mock_testcases.json'
    with open(out_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
        
    print(f"Extracted {len(result)} testcases saved to {out_file}")

    sample_codes = ["600", "700", "701", "704", "801", "802", "1621", "1622"]
    for sc in sample_codes:
        if sc in result:
            item = result[sc]
            print(f"\n--- Code {sc} [{item['protocolType']}] ({item['alias']}) ---")
            print(f"  Port: {item['port']}")
            print(f"  Handshake: {item['handshakeExample']}")
            print(f"  Sample Input: {item['sampleInput']}")
            print(f"  Sample Output: {item['sampleExpectedOutput']}")

if __name__ == "__main__":
    main()
