from vkbottle import ABCRule
from vkbottle.bot import Message


class RuleIsAdmin(ABCRule[Message]):
    def __init__(self, admin_id: int):
        self.admin_id = admin_id

    async def check(self, event: Message) -> bool:
        event.admin_author_id
        return event.from_id == self.admin_id
