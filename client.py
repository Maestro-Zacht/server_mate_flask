import asyncio
import websockets


async def hello():
    role = str(input("inserire il ruolo:\t"))

    uri = f"ws://servercatta.herokuapp.com/{role}"
    async with websockets.connect(uri) as ws:
        inp = 'ciao'
        while inp != 'end':
            inp = str(input("inp:\t"))

            if inp == 'recv':
                print(await ws.recv())

            elif inp == 'send':
                s = str(input("send:\t"))
                await ws.send(s)


asyncio.get_event_loop().run_until_complete(hello())
