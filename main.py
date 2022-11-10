import enum
import json
import os
import time
from pathlib import Path

import vk_api
from dotenv import load_dotenv
from vk_api.utils import get_random_id
from vk_api.vk_api import VkApiMethod


class ChatStatus(enum.Enum):
    available = 1
    cant_write = 2
    not_found = 3


def get_filename():
    return Path.cwd() / "last_post_id.json"


def get_last_post_id() -> int | None:
    filename = get_filename()
    if Path.exists(filename):
        with open(filename, 'r') as fp:
            data = json.load(fp)
            return data['last_post_id']
    return None


def set_last_post_id(post_id: int) -> None:
    filename = get_filename()
    data = {'last_post_id': post_id}
    with open(filename, 'w') as fp:
        json.dump(data, fp)


def wall_attachment(post: dict) -> str:
    return "{type}{owner_id}_{media_id}".format(
        type="wall",
        owner_id=post['owner_id'],
        media_id=post['id'])


def check_chat(chat_id: int, vk: VkApiMethod) -> ChatStatus:
    while True:
        try:
            vk.messages.getConversationsById(peer_ids=chat_id)
        except vk_api.ApiError as e:
            if e.code == 6:
                time.sleep(10)
                continue
            if e.code == 927:
                return ChatStatus.not_found
            elif e.code == 917:
                return ChatStatus.cant_write
        else:
            return ChatStatus.available


def process_chat(chat_id: int, posts: list, vk: VkApiMethod) -> None:
    """Reposts posts to chat"""
    for post in posts:
        try:
            vk.messages.send(
                random_id=vk_api.utils.get_random_id(),
                peer_id=chat_id,
                message=os.environ['MESSAGE'] or "Новый пост!",
                attachment=wall_attachment(post))
        except vk_api.ApiError as e:
            if e.code == 917:
                break
            if e.code == 6:
                time.sleep(6)
                e.try_method()


def main():
    service_session = vk_api.VkApi(token=os.environ['SERVICE_TOKEN'])
    community_session = vk_api.VkApi(token=os.environ['ACCESS_TOKEN'])
    service = service_session.get_api()
    community = community_session.get_api()

    wall = service.wall.get(owner_id=os.environ['WALL_ID'], count=10)
    wall = wall['items']
    wall = sorted(wall, key=lambda item: item['id'])

    last_post_id = get_last_post_id()
    if last_post_id is None:
        wall = [wall[-1]]
    else:
        wall = list(filter(lambda post: post['id'] > last_post_id, wall))

    if len(wall) == 0:
        return

    i = 2000000000
    while True:
        i += 1
        status = check_chat(i, community)
        if status == ChatStatus.available:
            process_chat(i, wall, community)
        if status == ChatStatus.cant_write:
            continue
        if status == ChatStatus.not_found:
            break

    set_last_post_id(wall[-1]['id'])


if __name__ == "__main__":
    load_dotenv()
    main()
