import re

from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.message_components import At, Node, Nodes, Plain
from astrbot.api.star import Context, Star


class QQSayPlugin(Star):
    def __init__(self, context: Context, config=None) -> None:
        super().__init__(context)
        self.config = config or {}

    def _cfg(self, key: str, default=None):
        return self.config.get(key, default)

    def _parse_id_list(self, key: str) -> set[str]:
        raw_value = str(self._cfg(key, "") or "").strip()
        if not raw_value:
            return set()
        parts = re.split(r"[\s,，]+", raw_value)
        return {part.strip() for part in parts if part.strip()}

    def _is_admin(self, event: AstrMessageEvent) -> bool:
        sender_id = str(event.get_sender_id())
        admins = self.context.get_config().get("admins_id", []) or []
        return sender_id in {str(item) for item in admins}

    def _get_group_whitelist(self) -> set[str]:
        return self._parse_id_list("group_whitelist")

    def _get_protected_users(self) -> set[str]:
        return self._parse_id_list("protected_users")

    def _is_group_allowed(self, event: AstrMessageEvent) -> bool:
        if self._is_admin(event):
            return True
        whitelist = self._get_group_whitelist()
        if not whitelist:
            return True
        group_id = str(event.get_group_id() or "").strip()
        return bool(group_id and group_id in whitelist)

    def _is_private_chat_allowed(self, event: AstrMessageEvent) -> bool:
        if self._is_admin(event):
            return True
        return bool(self._cfg("allow_private_chat", False))

    async def _get_display_name(self, event: AstrMessageEvent, user_id: str) -> str:
        try:
            if hasattr(event, "bot") and event.get_group_id():
                info = await event.bot.get_group_member_info(
                    group_id=int(event.get_group_id()), user_id=int(user_id)
                )
                if isinstance(info, dict):
                    return str(info.get("card") or info.get("nickname") or user_id)
        except Exception as e:
            logger.debug(f"QQ说获取群成员信息失败，user_id={user_id}: {e}")
        try:
            if hasattr(event, "bot"):
                info = await event.bot.get_stranger_info(
                    user_id=int(user_id), no_cache=True
                )
                if isinstance(info, dict):
                    return str(info.get("nickname") or user_id)
        except Exception as e:
            logger.debug(f"QQ说获取陌生人信息失败，user_id={user_id}: {e}")
        return user_id

    async def _get_mentions(
        self, event: AstrMessageEvent
    ) -> list[dict[str, str | list[str]]]:
        mentions: list[dict[str, str | list[str]]] = []
        seen_user_ids: set[str] = set()
        body = self._extract_body(event)

        for comp in event.message_obj.message:
            if isinstance(comp, At) and str(comp.qq) != "all":
                user_id = str(comp.qq)
                seen_user_ids.add(user_id)
                name = (getattr(comp, "name", "") or "").strip()
                if name.startswith("@"):
                    name = name[1:].strip()
                display_name = name or await self._get_display_name(event, user_id)
                aliases = [
                    f"@{display_name}({user_id})",
                    f"@{display_name}",
                    f"[At:{user_id}]",
                    f"@{user_id}",
                    user_id,
                ]
                mentions.append(
                    {
                        "user_id": user_id,
                        "name": display_name,
                        "aliases": aliases,
                    }
                )

        for user_id in re.findall(r"@(\d{5,})", body):
            if user_id in seen_user_ids:
                continue
            seen_user_ids.add(user_id)
            display_name = await self._get_display_name(event, user_id)
            mentions.append(
                {
                    "user_id": user_id,
                    "name": display_name,
                    "aliases": [
                        f"@{display_name}({user_id})",
                        f"@{display_name}",
                        f"@{user_id}",
                        user_id,
                    ],
                }
            )

        return mentions

    def _extract_body(self, event: AstrMessageEvent) -> str:
        text = event.message_str.strip()
        lowered = text.lower()
        if lowered.startswith("/qq说"):
            return text[5:].strip()
        if lowered.startswith("qq说"):
            return text[4:].strip()
        return text

    async def _parse_dialogues(
        self, event: AstrMessageEvent
    ) -> list[tuple[str, str, str]]:
        body = self._extract_body(event)
        mentions = await self._get_mentions(event)
        if not body or not mentions:
            return []

        speaker_blocks: list[dict[str, str]] = []
        current_block: dict[str, str] | None = None
        pending_switch = False
        message_separator = str(self._cfg("message_separator", "*")).strip() or "*"
        speaker_separator = str(self._cfg("speaker_separator", "---")).strip() or "---"

        for raw_line in body.splitlines():
            line = raw_line.rstrip()
            stripped = line.strip()
            if not stripped:
                continue

            if stripped.startswith(speaker_separator):
                pending_switch = True
                stripped = stripped[len(speaker_separator) :].strip()
                if not stripped:
                    continue

            matched = None
            for mention in mentions:
                for alias in mention["aliases"]:
                    if stripped.startswith(str(alias)):
                        matched = (
                            str(alias),
                            str(mention["user_id"]),
                            str(mention["name"]),
                        )
                        break
                if matched:
                    break

            if matched:
                rendered, user_id, name = matched
                content = stripped[len(rendered) :].strip()
                current_block = {
                    "user_id": user_id,
                    "name": name,
                    "content": content,
                }
                speaker_blocks.append(current_block)
                pending_switch = False
                continue

            if pending_switch:
                continue

            if current_block is not None:
                if current_block["content"]:
                    current_block["content"] += "\n" + stripped
                else:
                    current_block["content"] = stripped

        dialogues: list[tuple[str, str, str]] = []
        for block in speaker_blocks:
            parts = [part.strip() for part in block["content"].split(message_separator)]
            for part in parts:
                if part:
                    dialogues.append((block["user_id"], block["name"], part))

        return dialogues

    def _build_forward_nodes(self, dialogues: list[tuple[str, str, str]]) -> Nodes:
        nodes = [
            Node(name=name, uin=user_id, content=[Plain(message)])
            for user_id, name, message in dialogues
        ]
        return Nodes(nodes)

    def _get_protected_dialogue(
        self, dialogues: list[tuple[str, str, str]]
    ) -> tuple[str, str] | None:
        protected_users = self._get_protected_users()
        if not protected_users:
            return None
        for user_id, name, _message in dialogues:
            if str(user_id) in protected_users:
                return str(user_id), str(name)
        return None

    async def _handle_qq_say(self, event: AstrMessageEvent):
        if event.get_group_id():
            if not self._is_group_allowed(event):
                yield event.plain_result("当前群聊不在白名单中，无法使用")
                return
        else:
            if not self._is_private_chat_allowed(event):
                yield event.plain_result("当前不允许在私聊中使用")
                return

        dialogues = await self._parse_dialogues(event)
        if not dialogues:
            yield event.plain_result("格式错误请重新输入")
            return

        if not self._is_admin(event):
            protected_dialogue = self._get_protected_dialogue(dialogues)
            if protected_dialogue is not None:
                yield event.plain_result("你没有权限伪造该用户的消息")
                return

        yield event.chain_result([self._build_forward_nodes(dialogues)])

    @filter.command("QQ说")
    async def qq_say_upper(self, event: AstrMessageEvent):
        async for result in self._handle_qq_say(event):
            yield result

    @filter.command("qq说")
    async def qq_say_lower(self, event: AstrMessageEvent):
        async for result in self._handle_qq_say(event):
            yield result
