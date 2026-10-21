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
