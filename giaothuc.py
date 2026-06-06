import socket

HOST = "127.0.0.1"
PORT = 23

client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

client.connect((HOST, PORT))

client.send("Hello robot\n".encode())

client.close()

print("Sent")