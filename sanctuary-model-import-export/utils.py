
CONSOLE_DEBUG = True
CONSOLE_DEBUG_DATA = False
def console_debug(*args):
    if CONSOLE_DEBUG:
        for x in args:
            print(x)
def console_debug_data(*args):
    if CONSOLE_DEBUG:
        if CONSOLE_DEBUG_DATA:
            for x in args:
                print(x)
        else:
            print("[...]")
def vecSanmodelToBlender(vec):
    return (vec[0], vec[2], vec[1])
def vecBlenderToSanmodel(vec):
    return (vec[0], vec[2], vec[1])