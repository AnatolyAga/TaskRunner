import time

def get_spaces():
    global spaces_for_running_man
    spaces_for_running_man += 1

def running_man():
    print(f"It's running man!")

def hallelujah():
    print(f"{' '*spaces_for_running_man}Hallelujah!")


spaces_for_running_man = 0

for rm in range (1, 5):
    get_spaces()
    running_man()
    time.sleep(1)
    hallelujah()
    time.sleep(1.1)



