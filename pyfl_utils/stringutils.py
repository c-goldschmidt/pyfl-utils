
# todo: probably not needed anymore after python3 update

def try_encode(input):
    try:
        input = input.encode('utf-8')
    except:
        pass
    return input


def try_decode(input):
    try:
        input = input.decode('utf-8')
    except:
        pass
    return input
