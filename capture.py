from rich import console, table
import threading
import pathlib
import shutil
import time
import udp


# Remove existing data dir
try:
    shutil.rmtree(pathlib.Path("command"))
    shutil.rmtree(pathlib.Path("status"))
    shutil.rmtree(pathlib.Path("video"))
except FileNotFoundError:
    pass


Console = console.Console()
CommandServer = udp.Server(8889)
StatusServer = udp.Server(8890)
VideoServer = udp.Server(11111, decode=False)


# Scan Tello In Subnet
CommandServer.broadcast("command", 8889)
time.sleep(2)
CommandServer.broadcast("sn?", 8889)
time.sleep(2)

# Print Tello Info
InfoTable = table.Table(show_header=True, show_lines=True)
InfoTable.add_column("IP")
InfoTable.add_column("SN")
while CommandServer.new:
    datagram = CommandServer.read()
    if datagram.text != "ok":
        InfoTable.add_row(
            datagram.ip,
            datagram.text
        )
Console.print(InfoTable)


# Thread func
def save_status(server: udp.Server, target_ip: str):
    # Create data dir
    pathlib.Path("status").mkdir(exist_ok=True)
    # Save
    status_count = 0
    global stop_all
    while not stop_all:
        with open(f"status/{status_count}.txt", "wb") as status_file:
            if server.new:
                status_data = server.read()
                if status_data.ip == target_ip:
                    status_file.write(status_data.content)
                    status_count += 1


def save_video(server: udp.Server, target_ip: str):
    # Create data dir
    pathlib.Path("video").mkdir(exist_ok=True)
    # Save
    global stop_all
    video = b""
    while not stop_all:
        if server.new:
            dgram = server.read()
            if dgram.ip == target_ip:
                video += dgram.content
    with open("video/video.h264", "wb") as file:
        file.write(video)


# Let users input ip
ip = input("Please input target IP: ")
stop_all = False

# Create thread
status_thread = threading.Thread(target=save_status, args=[StatusServer, ip], daemon=True)
video_thread = threading.Thread(target=save_video, args=[VideoServer, ip], daemon=True)
status_thread.start()
video_thread.start()

# Start loop command
count = 0
pathlib.Path("command").mkdir(exist_ok=True)
while not stop_all:
    cmd = input("Input CMD: ")
    if cmd == "exit":
        stop_all = True
        break
    start = time.time()
    CommandServer.send(cmd, ip, 8889)
    while not CommandServer.new:
        pass
    end = time.time()
    data = CommandServer.read()
    Console.print(f"Response: {data.text}")
    Console.print(f"Time Used: {end - start}s\n")
    with open(f"command/{count}.txt", "wb") as f:
        f.write(data.content)
        count += 1

status_thread.join()
video_thread.join()
