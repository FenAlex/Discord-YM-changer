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
import threading
import time
import discord
import asyncio
from config import TOKEN

# Константы
TARGET_PROCESS_NAME = "Яндекс Музыка.exe"
# SEQUENCE_TO_CHECK = bytes([0x46, 0x00, 0x4C, 0x00, 0x41, 0x00, 0x4D, 0x00, 0x4D, 0x00, 0x41]) 
SEQUENCE_TO_CHECK = rb"\x46\x00\x4C\x00\x41\x00\x4D\x00\x4D\x00\x41" # Заданная последовательность

# Глобавьные переменные
pids = []
stop_thread = False
program_pause = False
music_info = "Яндекс Музыка"

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

    if nameLen > 0:

        try:
            actorName = getActorName(pid, 25)
        except Exception as e:
            print("actorName: " + str(e))
            actorName = "Unknown"

        try:
            pause = getPausedInfo(pid)
        except Exception as e:
            print("pause: " + str(e))
            pause = ""

        musicName = getMusicName(pid, nameLen)
        return pause + " " + actorName + " - " + musicName

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
    null_index = temp.find(b'\x00\x00')

    if null_index != -1:
        temp1 = temp[:null_index]
        temp2 = temp[:null_index+1]
    
    try:
        temp = temp1.decode("utf-16").rstrip('\x00')
    except:
        temp = temp2.decode("utf-16").rstrip('\x00')

    return(temp)

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
def update(icon):
    while not stop_thread:
        global program_pause
        if program_pause:
            continue

        pids = get_yandex_music_pids()
        icon.title = f"Discord менеджер"
        
        for pid in pids:
            temp = check_memory_for_sequence(pid)
            if temp:
                global music_info
                if music_info != temp:
                    music_info = temp

                    new_menu_item_music = MenuItem(music_info, history_action)
                    new_menu_item = MenuItem("Возобновить" if program_pause else "Пауза", pause_action)

                    icon.menu = (
                        new_menu_item_music,
                        new_menu_item,
                        MenuItem("Закрыть программу", exit_action),
                    )


        time.sleep(5)
    
def pause_action(icon, item):
    global program_pause
    program_pause = not program_pause

    # Create a new menu item based on the current state
    new_menu_item = MenuItem("Возобновить" if program_pause else "Пауза", pause_action)

    # Update the icon's menu with a new Menu object
    icon.menu = (
        MenuItem("Яндекс Музыка", history_action),
        new_menu_item,
        MenuItem("Закрыть программу", exit_action),
    )



def exit_action(icon, item):
    global stop_thread
    stop_thread = True
    icon.stop()

def history_action(icon, item):
    pass

class MyClient(discord.Client):
    async def on_ready(self):
        print(f'Logged on as {self.user}!')
        self.change_status_task = self.loop.create_task(self.change_status())

    async def change_status(self):
        global program_pause
        global music_info
        global stop_thread
        actual_music_info = ""
        while not stop_thread:
            # print("Информация об активности: " + music_info)
            # print("Акутальная информация об активности: " + actual_music_info)
            if not program_pause:
                if music_info != actual_music_info:
                    actual_music_info = music_info
                    await self.change_presence(activity=discord.Game(music_info))
                    
            await asyncio.sleep(5)

def run_discord_client():
    client = MyClient()
    client.run(TOKEN)

# Основная функция
def main():
    icon = Icon("test_icon", create_image(64, 64), title="Discord менеджер", menu=(
        MenuItem("Яндекс Музыка", history_action),
        MenuItem("Пауза", pause_action),
        MenuItem("Закрыть программу", exit_action),
    ))

    threading.Thread(target=update, args=(icon,)).start()
    threading.Thread(target=run_discord_client).start()

    
    icon.run()

if __name__ == "__main__":
    main()
