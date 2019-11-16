
compiled = False

def locals(**kwargs):
    def wrapper(f):
        return f

    return wrapper
