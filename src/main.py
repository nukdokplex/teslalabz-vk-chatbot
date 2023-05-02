import argparse
import logging
import sqlite3
from typing import Optional
import random

from vkbottle import GroupEventType, GroupTypes, VKAPIError
from vkbottle.bot import Bot, Message
from vkbottle.modules import logger

from rules import RuleIsAdmin


parser = argparse.ArgumentParser(
    prog="VKBotWallNotifier",
    description="This bot notifies about new posts in chats",
    epilog="Consider supporting me! https://github.com/nukdokplex",
)
parser.add_argument("token", help="Bot token")
parser.add_argument(
    "admin",
    help='Bot admin id (has permission to "/subscribe" and "/unsubscribe" commands)',
)
parser.add_argument(
    "-d", "--database", help="Path to database file", default="subscriptions.db"
)
args = parser.parse_args()
bot = Bot(args.token)
logging.basicConfig(level=logging.INFO)
logging.info("Initializing database...")
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
bot.labeler.custom_rules["only_admin"] = RuleIsAdmin


@bot.on.chat_message(
    text=["/subscribe <text>", "/subscribe"], only_admin=int(args.admin)
)
async def subscribe_cmd(message: Message, text: Optional[str] = None):
    logging.info(f'"subscribe" command invoked by {str(message.peer_id)}.')
    if text is not None:
        text = text.format(all="@all", everyone="@everyone", online="@online", here="@here")
    try:
        with con:
            sql = "INSERT INTO subscriptions(group_id,chat_id,msg_text) VALUES(?,?,?);"
            entry = (message.group_id, message.chat_id, text)
            con.execute(sql, entry)
    except Exception as e:
        logger.error(e)
        await message.answer("not okay, check console")
    else:
        await message.answer("okay")


@bot.on.chat_message(text=["/unsubscribe"], only_admin=int(args.admin))
async def unsubscribe_cmd(message: Message):
    logging.info(
        f'"unsubscribe" command invoked by {message.from_id} in {message.peer_id}.'
    )

    try:
        with con:
            sql = "DELETE FROM subscriptions WHERE group_id = ? AND chat_id = ?;"
            entry = (message.group_id, message.chat_id)
            con.execute(sql, entry)
    except Exception as e:
        logging.error(e)
        await message.answer("not okay, check console")
    else:
        await message.answer("okay")


@bot.on.raw_event(GroupEventType.WALL_POST_NEW, GroupTypes.WallPostNew)
async def wall_post_new_handler(event: GroupTypes.WallPostNew):
    logging.info("New post event, performing notifications.")
    try:
        sql = "SELECT * FROM subscriptions WHERE group_id = ?;"
        with con:
            for subscription in con.execute(sql, (bot.polling.group_id,)):
                try:
                    await bot.api.messages.send(
                        random_id=random.randint(-2_147_483_638, 2_147_483_637),
                        chat_id=subscription[2],
                        message=subscription[3] or "",
                        attachment=f"wall{-bot.polling.group_id}_{event.object.id}",
                    )
                except Exception as e:
                    logger.error(e)
                    logger.error(f"Can't send to {subscription[2]} chat.")
    except Exception as e:
        logger.error(e)
        logger.error("Common error while distribution.")


bot.run_forever()
