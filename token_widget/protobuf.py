"""Decodificador mínimo de protobuf (sem schema).

O Antigravity CLI grava as conversas em SQLite com blobs protobuf. Não temos
o .proto, então lemos o formato wire direto e devolvemos [(campo, valor), ...].
"""


def _varint(buf, i):
    result = shift = 0
    while True:
        b = buf[i]
        i += 1
        result |= (b & 0x7F) << shift
        shift += 7
        if b < 0x80:
            return result, i


def parse(buf):
    """Lê uma mensagem. Campos length-delimited ficam como bytes;
    use `parse` de novo neles quando souber que são submensagens."""
    out = []
    i = 0
    n = len(buf)
    while i < n:
        key, i = _varint(buf, i)
        field, wire = key >> 3, key & 7
        if field == 0:
            raise ValueError("campo 0 inválido")
        if wire == 0:
            val, i = _varint(buf, i)
        elif wire == 2:
            ln, i = _varint(buf, i)
            val = buf[i:i + ln]
            i += ln
            if i > n:
                raise ValueError("tamanho fora do buffer")
        elif wire == 1:
            val = buf[i:i + 8]
            i += 8
        elif wire == 5:
            val = buf[i:i + 4]
            i += 4
        else:
            raise ValueError(f"wire type {wire} não suportado")
        out.append((field, val))
    return out


def first(fields, num, default=None):
    for f, v in fields:
        if f == num:
            return v
    return default
