
CONSOLE_NOTICE = True
CONSOLE_DEBUG = False
CONSOLE_DEBUG_DATA = False # lots of data
COLOR = False # do not push if True, it could not work for users and mess up the logs

prefix_notice = "[SANMODEL_NOTICE] "
prefix_debug = "[SANMODEL_DEBUG] "

black = "\033[30m"
red = "\033[31m"	
green = "\033[32m"	
yellow = "\033[33m"	
blue = "\033[34m"	
magenta = "\033[35m"	
cyan = "\033[36m"	
light_gray = "\033[37m"	
dark_gray = "\033[90m"	
light_red = "\033[91m"	
light_green = "\033[92m"	
light_yellow = "\033[93m"	
light_blue = "\033[94m"	
light_magenta = "\033[95m"	
light_cyan = "\033[96m"	
white = "\033[97m"
endcolor = "\033[0m"

def console_notice(*args):
    if CONSOLE_NOTICE:
        for x in args:
            if COLOR:
                print(light_blue, prefix_notice, x, endcolor)
            else:
                print(prefix_notice, x)

def console_debug(*args):
    if CONSOLE_DEBUG:
        for x in args:
            if COLOR:
                print(yellow, prefix_debug, x, endcolor)
            else:
                print(prefix_debug, x)

def console_debug_data(*args):
    if CONSOLE_DEBUG:
        if CONSOLE_DEBUG_DATA:
            for x in args:
                print(prefix_debug, x)
        else:
            print(prefix_debug, "[...]")

def vecSanmodelToBlender(vec):
    return (vec[0], vec[2], vec[1])

def vecBlenderToSanmodel(vec):
    return (vec[0], vec[2], vec[1])

def getDeepSelectionMeshes(selected_objects):
    selected = []
    for obj in selected_objects:
        # console_debug(obj.name)
        if (obj.type == "MESH") or (obj.type == "ARMATURE"):
            selected[len(selected):] = [obj]
            # console_debug(f"+1 {obj.name}")
        elif obj.type == "EMPTY":
            selected[len(selected):] = getDeepSelectionMeshes(obj.children)
    return selected
