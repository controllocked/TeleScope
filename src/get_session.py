


import asyncio
import logging

from dotenv import load_dotenv
from getpass import getpass
import os
import qrcode
from telethon import TelegramClient, errors


load_dotenv()

def create_client() -> TelegramClient:
    return TelegramClient(os.getenv('SESSION_NAME'), int(os.getenv('API_ID')), os.getenv('API_HASH'))
def _print_qr(url: str) -> None:
    qr = qrcode.QRCode(border=1)
    qr.add_data(url)
    qr.make(fit=True)
    qr.print_ascii(invert=True)


def _resolve_2fa_password() -> str:
    password = os.getenv("2FA")
    if password:
        return password
    return getpass("2FA password: ")


async def _authorize_with_qr(client: TelegramClient) -> None:
    qr = await client.qr_login()
    _print_qr(qr.url)
    await qr.wait(timeout=120)


async def _authorize_with_phone(client: TelegramClient) -> None:
    phone = os.getenv("PHONE") or input("Phone number (international format): ").strip()
    await client.send_code_request(phone)
    code = input("Login code: ").strip()
    try:
        await client.sign_in(phone=phone, code=code)
    except errors.SessionPasswordNeededError:
        await client.sign_in(password=_resolve_2fa_password())


def _pick_login_method() -> str:
    method = (os.getenv("LOGIN_METHOD") or "").strip().lower()
    if method in {"qr", "phone"}:
        return method
    while True:
        print("")
        print("Login methods:")
        print("[1] QR code")
        print("[2] Phone code")
        print("[3] Exit")
        print("Select a login method: \n")
        choice = input("telescope > ").strip()
        if choice == '1':
            return "qr"
        elif choice == '2':
            return "phone"
        elif choice == "3":
            raise SystemExit(0)
        else:
            print("Invalid option. Please choose 1, 2, or 3.")


async def authorize(client: TelegramClient) -> None:
    if await client.is_user_authorized():
        return

    try:
        method = _pick_login_method()
        if method == "phone":
            await _authorize_with_phone(client)
        else:
            await _authorize_with_qr(client)
    except errors.SessionPasswordNeededError:
        await client.sign_in(password=_resolve_2fa_password())

async def main() -> None:
    client = create_client()
    await client.connect()

    await authorize(client)

    me = await client.get_me()
    logging.info(f"Logged in as: {me.first_name}")

    await client.disconnect()




if __name__ == "__main__":
    asyncio.run(main())
