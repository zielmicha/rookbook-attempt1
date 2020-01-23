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
            # make it a bit harder for a tracing JIT
            variant = r.randrange(40)
            if variant == 0:
                return reactive(lambda: a.value + b.value)

            elif variant == 1:
                return reactive(lambda: a.value + b.value + 1)

            elif variant == 2:
                return reactive(lambda: a.value + b.value + 2)

            elif variant == 3:
                return reactive(lambda: a.value + b.value + 3)

            elif variant == 4:
                return reactive(lambda: a.value + b.value + 4)

            elif variant == 5:
                return reactive(lambda: a.value + b.value + 5)

            elif variant == 6:
                return reactive(lambda: a.value + b.value + 6)

            elif variant == 7:
                return reactive(lambda: a.value + b.value + 7)

            elif variant == 8:
                return reactive(lambda: a.value + b.value + 8)

            elif variant == 9:
                return reactive(lambda: a.value + b.value + 9)

            elif variant == 10:
                return reactive(lambda: a.value + b.value + 10)

            elif variant == 11:
                return reactive(lambda: a.value + b.value + 11)

            elif variant == 12:
                return reactive(lambda: a.value + b.value + 12)

            elif variant == 13:
                return reactive(lambda: a.value + b.value + 13)

            elif variant == 14:
                return reactive(lambda: a.value + b.value + 14)

            elif variant == 15:
                return reactive(lambda: a.value + b.value + 15)

            elif variant == 16:
                return reactive(lambda: a.value + b.value + 16)

            elif variant == 17:
                return reactive(lambda: a.value + b.value + 17)

            elif variant == 18:
                return reactive(lambda: a.value + b.value + 18)

            elif variant == 19:
                return reactive(lambda: a.value + b.value + 19)

            elif variant == 20:
                return reactive(lambda: a.value + b.value + 20)

            elif variant == 21:
                return reactive(lambda: a.value + b.value + 21)

            elif variant == 22:
                return reactive(lambda: a.value + b.value + 22)

            elif variant == 23:
                return reactive(lambda: a.value + b.value + 23)

            elif variant == 24:
                return reactive(lambda: a.value + b.value + 24)

            elif variant == 25:
                return reactive(lambda: a.value + b.value + 25)

            elif variant == 26:
                return reactive(lambda: a.value + b.value + 26)

            elif variant == 27:
                return reactive(lambda: a.value + b.value + 27)

            elif variant == 28:
                return reactive(lambda: a.value + b.value + 28)

            elif variant == 29:
                return reactive(lambda: a.value + b.value + 29)

            elif variant == 30:
                return reactive(lambda: a.value + b.value + 30)

            elif variant == 31:
                return reactive(lambda: a.value + b.value + 31)

            elif variant == 32:
                return reactive(lambda: a.value + b.value + 32)

            elif variant == 33:
                return reactive(lambda: a.value + b.value + 33)

            elif variant == 34:
                return reactive(lambda: a.value + b.value + 34)

            elif variant == 35:
                return reactive(lambda: a.value + b.value + 35)

            elif variant == 36:
                return reactive(lambda: a.value + b.value + 36)

            elif variant == 37:
                return reactive(lambda: a.value + b.value + 37)

            elif variant == 38:
                return reactive(lambda: a.value + b.value + 38)

            elif variant == 39:
                return reactive(lambda: a.value + b.value + 39)


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
