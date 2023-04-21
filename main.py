import argparse
import vk_api
import random
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
from vk_api.execute import VkApiMethod
import sqlite3

SUBSCRIBE_COMMAND = "!subscribe"
UNSUBSCRIBE_COMMAND = "!unsubscribe"


def send_message(
    vk: VkApiMethod, chat_id: int, message: str, attachments: list[str] = None
):
    args = {
        "chat_id": chat_id,
        "message": message,
        "random_id": random.randint(-2_147_483_648, 2_147_483_647),
    }
    if attachments is not None:
        args["attachment"] = ",".join(attachments)
    vk.messages.send(**args)


def main(args: argparse.Namespace):
    """The main method which runs cycle"""
    print("Creating session...")

    session = vk_api.VkApi(token=args.token)
    longpoll = VkBotLongPoll(session, abs(int(args.group_id)))
    vk = session.get_api()

    print("Connecting database...")
    con = sqlite3.connect(args.database)
    with con:
        con.execute(
            "CREATE TABLE IF NOT EXISTS subscriptions("
            "id INTEGER PRIMARY KEY, "
            "group_id UNSIGNED BIG INT NOT NULL, "
            "chat_id UNSIGNED BIG INT NOT NULL, "
            "msg_text TEXT, "
            "UNIQUE(group_id, chat_id) ON CONFLICT REPLACE);"
        )

    print("Bot started! Listening to longpoll events...")

    for event in longpoll.listen():
        if event.type == VkBotEventType.WALL_POST_NEW:
            print("New post event! Sending to subscribed chats...")
            with con:
                sql = "SELECT * FROM subscriptions WHERE group_id = ?;"
                for subscription in con.execute(sql, (int(args.group_id),)):
                    send_message(
                        vk,
                        subscription[2],
                        subscription[3] or "",
                        [f"wall{args.group_id}_{event.obj.id}"],
                    )
        if event.type == VkBotEventType.MESSAGE_NEW:
            if event.from_chat and event.obj.message['from_id'] == int(args.admin):
                if str.startswith(event.obj.message['text'], SUBSCRIBE_COMMAND):
                    text = None
                    if str.startswith(event.obj.message['text'], SUBSCRIBE_COMMAND + " "):
                        text = event.obj.message['text'][len(SUBSCRIBE_COMMAND) + 1 :]
                        text = str.format(text, all="@all")
                    try:
                        with con:
                            sql = "INSERT INTO subscriptions(group_id,chat_id) VALUES(?,?);"
                            entry = (int(args.group_id), int(event.chat_id))
                            if text is not None and text:
                                sql = "INSERT INTO subscriptions(group_id,chat_id,msg_text) VALUES(?,?,?);"
                                entry = (int(args.group_id), int(event.chat_id), text)
                            con.execute(sql, entry)
                    except Exception:
                        print(Exception)
                        send_message(
                            vk,
                            chat_id=int(event.chat_id),
                            message="not okay, check console",
                        )

                    else:
                        send_message(vk, chat_id=int(event.chat_id), message="okay")
                    continue
                if str.startswith(event.obj.message['text'], UNSUBSCRIBE_COMMAND):
                    try:
                        with con:
                            sql = "DELETE FROM subscriptions WHERE group_id = ? AND chat_id = ?;"
                            entry = (int(args.group_id), int(event.chat_id))
                            con.execute(sql, entry)
                    except Exception:
                        print(Exception)
                        send_message(
                            vk,
                            chat_id=int(event.chat_id),
                            message="not okay, check console",
                        )
                    else:
                        send_message(vk, chat_id=int(event.chat_id), message="okay")
                    continue
        else:
            print(f"Unhandled event ({str(event.type)})")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="VKBotWallNotifier",
        description="This bot notifies about new posts in chats",
        epilog="Consider supporting me! https://github.com/nukdokplex",
    )

    parser.add_argument(
        "group_id",
        help="Identifier of your group",
    )
    parser.add_argument("token", help="Bot token")

    parser.add_argument(
        "admin",
        help='Bot admin id (has permission to "!subscribe" and "!unsubscribe" commands)',
    )
    parser.add_argument(
        "-d", "--database", help="Path to database file", default="subscriptions.db"
    )

    args = parser.parse_args()
    main(args)
