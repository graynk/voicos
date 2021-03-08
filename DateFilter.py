from typing import Union, Dict, Optional

from telegram import Message
from telegram.ext import MessageFilter
from datetime import datetime, timezone


class DateFilter(MessageFilter):
    def filter(self, message: Message) -> Optional[Union[bool, Dict]]:
        return (datetime.now(timezone.utc) - message.date).days <= 3
