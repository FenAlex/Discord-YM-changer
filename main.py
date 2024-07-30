import psutil
import pymem.memory
import pymem.pattern
import pystray
from pystray import MenuItem, Icon
from PIL import Image, ImageDraw
import pymem
import pymem.process
from pymem.ptypes import RemotePointer
import re

# Константы
TARGET_PROCESS_NAME = "Яндекс Музыка.exe"
# SEQUENCE_TO_CHECK = bytes([0x46, 0x00, 0x4C, 0x00, 0x41, 0x00, 0x4D, 0x00, 0x4D, 0x00, 0x41]) 
SEQUENCE_TO_CHECK = rb"\x46\x00\x4C\x00\x41\x00\x4D\x00\x4D\x00\x41" # Заданная последовательность

# Функция для создания иконки
def create_image(width, height):
    image = Image.new('RGB', (width, height), (255, 255, 255))
    dc = ImageDraw.Draw(image)
    dc.ellipse((0, 0, width, height), fill=(0, 0, 255))
    return image


def get_yandex_music_pids():
    pids = []
    for proc in psutil.process_iter(['pid', 'name']):
        if proc.info['name'] == TARGET_PROCESS_NAME:
            pids.append(proc.info['pid'])
    return pids

def check_memory_for_sequence(pid):
    nameLen = getMmusicLen(pid)
    
    if nameLen == False or nameLen == 0:
        return False
    
    try:
        actorNameLen = getActorNameLen(pid)
    except Exception as e:
        print("actorNameLen: " + e)
        actorNameLen = 25

    if nameLen > 0:

        try:
            actorName = getActorName(pid, actorNameLen)
        except Exception as e:
            print("actorName: " + e)
            actorName = "Unknown"

        try:
            pause = getPausedInfo(pid)
        except Exception as e:
            print("pause: " + e)
            pause = ""

        musicName = getMusicName(pid, nameLen)
        print(pause + " " + actorName + " - " + musicName)
        return True

def getPausedInfo(pid):
    pm  = pymem.Pymem(pid)
    PauseOffsets = [0x10,0x48,0x68,0x68,0x38,0x10,0x2CC]
    base_address = pm.base_address+0x09FC1AE8
    pause=RemotePointer(pm.process_handle, base_address)
    if pause.value==0:
        return False
    for PauseOffset in PauseOffsets:
        if PauseOffset==PauseOffsets[-1]:
            pause=pause.value+PauseOffsets[-1]
            break
        pause=RemotePointer(pm.process_handle, pause.value+PauseOffset)

    if pm.read_int(pause)==3:
        return "▶️ "
    else:
        return "⏸️ "

def getActorNameLen(pid):
    pm  = pymem.Pymem(pid)
    NameLenOffsets = [0x108,0x38,0x2C0,0x50,0x28,0x1F0]
    base_address = pm.base_address+0x09F5B198
    nameLen=RemotePointer(pm.process_handle, base_address)
    if nameLen.value==0:
        return False
    for NameLenOffset in NameLenOffsets:
        if NameLenOffset==NameLenOffsets[-1]:
            nameLen=nameLen.value+NameLenOffsets[-1]
            break
        nameLen=RemotePointer(pm.process_handle, nameLen.value+NameLenOffset)
    return pm.read_int(nameLen)

def getActorName(pid, nameLen = 25):
    pm  = pymem.Pymem(pid)
    ActorNameOffsets = [0x8,0x90,0x28,0x48,0x10,0x1A8,0x0]
    base_address = pm.base_address+0x0A0551E8
    actorName=RemotePointer(pm.process_handle, base_address)
    if actorName.value==0:
        return False
    for ActorNameOffset in ActorNameOffsets:
        if ActorNameOffset==ActorNameOffsets[-1]:
            actorName=actorName.value+ActorNameOffsets[-1]
            break
        actorName=RemotePointer(pm.process_handle, actorName.value+ActorNameOffset)
    
    temp = b'' + pm.read_bytes(actorName, nameLen * 2)
    return(temp.decode("utf-16").rstrip('\x00'))

def getMmusicLen(pid):
    pm  = pymem.Pymem(pid)
    NameLenOffsets = [0x8,0x60,0x10,0x10,0x18,0x98,0x1E8]
    base_address = pm.base_address+0x09FA2A18
    nameLen=RemotePointer(pm.process_handle, base_address)
    if nameLen.value==0:
        return False
    for NameLenOffset in NameLenOffsets:
        if NameLenOffset==NameLenOffsets[-1]:
            nameLen=nameLen.value+NameLenOffsets[-1]
            break
        nameLen=RemotePointer(pm.process_handle, nameLen.value+NameLenOffset)
    return pm.read_int(nameLen)

def getMusicName(pid, nameLen):
    pm  = pymem.Pymem(pid)
    NameOffsets = [0x8,0x68,0x48,0x98,0x30,0x1D0,0x0]
    base_address = pm.base_address+0x09FC11B8 
    name=RemotePointer(pm.process_handle, base_address)
    if name.value==0:
        return False
    
    for NameOffset in NameOffsets:
        if NameOffset==NameOffsets[-1]:
            name=name.value+NameOffsets[-1]
            break

        name=RemotePointer(pm.process_handle, name.value+NameOffset)

    temp = b'' + pm.read_bytes(name, nameLen * 2)
    return(temp.decode("utf-16").rstrip('\x00'))

# Функция для обновления информации о PID
def update_pid(icon):
    pids = get_yandex_music_pids()
    count = len(pids)
    icon.title = f"Discord менеджер: {count} Яндекс Музыка"
    
    # Проверяем память каждого PID на наличие последовательности
    for pid in pids:
        if check_memory_for_sequence(pid):
            print(f"Последовательность найдена в процессе с PID: {pid:08X}")

# Функция выхода из программы
def exit_action(icon, item):
    icon.stop()

# Основная функция
def main():
    icon = Icon("test_icon", create_image(64, 64), title="Discord менеджер", menu=(
        MenuItem("Яндекс Музыка: 0", update_pid),
        MenuItem("Закрыть программу", exit_action),
    ))
    
    icon.run()

if __name__ == "__main__":
    main()
