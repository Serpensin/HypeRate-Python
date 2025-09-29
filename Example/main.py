import asyncio

import hyperate


async def get_valid_api_key():
    while True:
        api_key = input("Please enter your HypeRate API Key: ").strip()
        hr = hyperate.HypeRate(api_key)
        try:
            await hr.connect()
            if hr.connected:
                return hr
            else:
                print("Invalid API key. Please try again.")
        except Exception:
            print("Connection failed. Please try again.")


async def main():
    hr = await get_valid_api_key()

    def on_heartbeat(data):
        print("Heartbeat received:", data["hr"])

    hr.on("heartbeat", on_heartbeat)

    await hr.join_heartbeat_channel("internal-testing")

    try:
        while True:
            await asyncio.sleep(1)
    except (KeyboardInterrupt, Exception):
        print("Exiting...")

    await hr.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
