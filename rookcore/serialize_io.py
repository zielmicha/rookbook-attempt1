'''
Test writing/reading integers

>>> import io
>>> out = OutputBuffer(); list(write_uint(0))
[0]
>>> out = OutputBuffer(); list(write_uint(10))
[10]
>>> out = OutputBuffer(); list(write_uint(100))
[100]
>>> out = OutputBuffer(); list(write_uint(129))
[129, 1]
>>> out = OutputBuffer(); list(write_uint(10**10))
[128, 200, 175, 160, 37]
>>> def roundtrip(x):
...   assert read_uint(write_uint(x))[1] == x
>>> for i in range(0, 1000): roundtrip(i)
>>> for i in range(0, 1000): roundtrip(i * 6000001)
'''

class OutputBuffer:
    def __init__(self):
        self.out = []
        self.size = 0

    def write(self, b):
        assert isinstance(b, (OutputBuffer, bytes))
        self.size += len(b)
        self.out.append(b)

    def __len__(self):
        return self.size

    def getvalue(self):
        result = bytearray()
        for b in self.out:
            if isinstance(b, OutputBuffer):
                result += b.getvalue()
            else:
                result += b

        return memoryview(result)

def write_uint(n):
    assert n >= 0
    data = []
    while True:
        n_rest = n >> 7
        if n_rest == 0:
            data.append(n)
            break
        else:
            data.append((1 << 7) | (n & ((1 << 7) - 1)))

        n = n_rest

    return bytes(data)

def int_to_uint(n):
    if n >= 0:
        return n * 2
    else:
        return -1 - n * 2

def read_uint(mem):
    result = 0
    shift = 0
    i = 0
    while True:
        if i >= len(mem): raise EOFError()
        b = mem[i]
        result |= (b & ((1 << 7) - 1)) << shift
        shift += 7

        i += 1

        if b & (1 << 7) == 0:
            break

    return i, result

def uint_to_int(n):
    if n & 1 == 0:
        return n >> 1
    else:
        return -(n >> 1)-1

def write(out, x):
    if isinstance(x, int):
        out.write(write_uint(x))
    elif isinstance(x, (bytes, OutputBuffer)):
        out.write(write_uint(len(x)))
        out.write(x)
    else:
        raise Exception('invalid value')

def write_message(items):
    out = OutputBuffer()

    for k, v in items:
        if isinstance(v, int):
            type_tag = 0
        elif isinstance(v, (bytes, OutputBuffer)):
            type_tag = 2
        else:
            raise Exception('invalid value %r' % v)

        out.write(write_uint((k << 3) | type_tag))
        write(out, v)

    return out

def read(mem, kind):
    if kind == 0:
        return read_uint(mem)
    elif kind == 2:
        i, length = read_uint(mem)
        value = mem[i : i + length]
        return i + length, value
    else:
        raise Exception('invalid kind (%d)' % kind)

def read_message(mem):
    result = []
    i = 0
    while i < len(mem):
        i_, tag = read_uint(mem[i:])
        i += i_
        kind = tag & 7
        key = tag >> 3
        i_, value = read(mem[i:], kind)
        i += i_
        result.append((key, value))
    return result
