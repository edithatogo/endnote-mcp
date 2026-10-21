"""Shared defensive OOXML primitives. No Word or EndNote application calls."""
import hashlib
from lxml import etree

W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'

def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()

def parse_xml(raw: bytes):
    if b'<!DOCTYPE' in raw.upper() or b'<!ENTITY' in raw.upper():
        raise ValueError('DTD/entity declarations are forbidden')
    return etree.fromstring(raw, etree.XMLParser(resolve_entities=False, no_network=True))

def text(element) -> str:
    return ''.join(n.text or '' for n in element.iter(W+'t'))

def field_structure(document):
    """Return protected complex-field nodes; reject malformed field phases.

    Instruction/data are accepted only within a complex field's instruction
    phase. Every complex field requires one separator before its end.
    """
    stack = []
    protected = set()
    for node in document.iter():
        if node.tag == W+'fldChar':
            kind = node.get(W+'fldCharType')
            if kind == 'begin':
                stack.append(False)
            elif kind == 'separate':
                if not stack or stack[-1]: raise ValueError('Unexpected field separator')
                stack[-1] = True
            elif kind == 'end':
                if not stack: raise ValueError('Unexpected field end')
                if not stack[-1]: raise ValueError('Field missing separator')
                protected.add(node)
                stack.pop()
            else:
                raise ValueError('Unknown field character type')
        elif node.tag in (W+'instrText', W+'fldData'):
            if not stack or stack[-1]:
                raise ValueError('Instruction/payload outside field instruction phase')
        if stack: protected.add(node)
    if stack: raise ValueError('Truncated/unclosed complex field')
    return protected
