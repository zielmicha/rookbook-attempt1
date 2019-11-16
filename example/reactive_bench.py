import timeit, random
from rookcore.reactive import reactive, VarRef, stabilise, Observer

def main():
    r = random.Random(13)
    vars = []

    def make_tree(level):
        if level == 0:
            v = VarRef(random.randrange(100))
            vars.append(v)
            return v
        else:
            a = make_tree(level-1)
            b = make_tree(level-1)
            return reactive(lambda: a.value + b.value)

    t = make_tree(10)
    o = Observer(t)
    stabilise()

    for i in range(10000):
        random.choice(vars).value = random.randrange(100)
        stabilise()

if __name__ == '__main__':
    print(timeit.timeit(lambda: main(), number=20))
    # [20]
    # - python3: 13.4s
    # - pypy: 1.14s
    # - cython (base): 9.5s
    # - cython (basic types): 7s
