#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Демонстрация мульти-агентного редактирования одного документа
по сложному протоколу намерений, критики и финальных правок.

Ключевые свойства:

- Один файл, без внешних сервисов (кроме OpenAI API).
- Асинхронная эмуляция множества агентов (по умолчанию 10).
- Каждый агент может сделать до MAX_EDITS_PER_AGENT завершённых правок (по умолчанию 5).
- Строго следует последней версии твоего плана с фазами 1–12,
  БЕЗ УПРОЩЕНИЙ по фазности (но с техническими допущениями внутри).

Структура цикла агента (одна "полноценная правка"):

 1.  Просмотр чата
 2.  Просмотр документа
 3.  Генерация НАМЕРЕНИЯ на основе чата и документа (модель также может сразу породить
     комментарии к чужим намерениям).
 4.  Просмотр чата
 5.  Просмотр документа
 6.  Генерация ПОДТВЕРЖДЕНИЯ/ОТКЛОНЕНИЯ намерения (и в этот момент тоже можно
     сгенерировать комментарии к чужим намерениям).
 7.  Публикация намерения (если оно подтверждено)
 8.  Просмотр чата
 9.  Просмотр документа
10.  Генерация КОНКРЕТНОЙ ПРАВКИ (модель может отменить или скорректировать намерение;
     также может сгенерировать комментарии).
11.  ЕЩЁ РАЗ просмотр чата и документа и финальное решение:
     применить правку как есть / чуть изменить (локально) / отменить.
     (Модель смотрит, не стало ли намерение вредным/устаревшим).
12.  Применение или отмена намерения (правка зафиксирована или отвергнута).
13.  Новый цикл без внутреннего стейта (всё, что сохранилось — уже в чате/документе).

Документ:
- Держится в памяти (список версий).
- Каждая версия сохраняется в файл: docs/document_vNNNN.txt

Чат:
- Все сообщения пишутся в память и в файл logs/chat_log.txt
- Есть три типа структурированных сущностей:
  - EditIntent (намерение)
  - EditComment (комментарий / критика / дополнение)
  - EditOperation (конкретная операция правки insert/replace/delete/none)

OpenAI:
- Используется новый клиент `openai.OpenAI` и Responses API.
- Ты сам впишешь OPENAI_API_KEY и OPENAI_BASE_URL.
- Модель: GPT-5.1 (можешь заменить при желании).

ВАЖНО:
- НЕ ИСПОЛЬЗУЕТСЯ env.
- Код — демонстрационный harness; некоторые вещи упрощены
  (например, мы не делаем многошаговый apply_patch и не используем V4A диффы).
"""

import asyncio
import os
import random
import string
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple

import json
from pydantic import BaseModel, Field, ValidationError

import openai

# ==========================
# НАСТРОЙКИ (ЗАПОЛНИ САМ)
# ==========================

OPENAI_API_KEY = "sk-7y1UkadZ1TktyKMRK8bFF90FE90Elm70"
OPENAI_BASE_URL = "https://api.proxyapi.ru/openai/v1"  # или твой прокси-эндпоинт

NUM_AGENTS = 10
MAX_EDITS_PER_AGENT = 5

INITIAL_DOCUMENT_TEXT = (
    "Это общий документ, который несколько агентов будут улучшать параллельно.\n"
    "Задача агентов — вносить небольшие, но полезные локальные правки.\n"
    "Тема документа — научно-фантастический детский рассказ про будущее и роботов, которые очень хотели стать людьми с моралью и принципами\n"
    "Документ начинается здесь.\n"
)

DOCS_DIR = Path("docs")
LOGS_DIR = Path("logs")
CHAT_LOG_PATH = LOGS_DIR / "chat_log.txt"

OPENAI_MODEL = "gpt-5.1"

MIN_DELAY_SECONDS = 0.2
MAX_DELAY_SECONDS = 1.0
MAX_ITERATIONS_PER_AGENT = 30


# ==========================
# УТИЛИТЫ
# ==========================

def random_id(prefix: str, length: int = 8) -> str:
    return f"{prefix}_" + "".join(random.choices(string.ascii_lowercase + string.digits, k=length))


def ensure_dirs():
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)


def print_and_log_chat(line: str):
    ts = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
    msg = f"[{ts}] {line}"
    print(msg)
    with CHAT_LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(msg + "\n")


# ==========================
# МОДЕЛИ ДАННЫХ
# ==========================

class OperationType(str, Enum):
    INSERT = "insert"
    REPLACE = "replace"
    DELETE = "delete"
    NONE = "none"  # отказ от правки


class IntentStatus(str, Enum):
    PROPOSED = "proposed"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    EXECUTED = "executed"


class CommentKind(str, Enum):
    CRITIQUE = "critique"
    SUPPORT = "support"
    SUGGESTION = "suggestion"


class EditOperation(BaseModel):
    """
    Структурированная операция правки:
    - operation: insert/replace/delete/none
    - anchor: фрагмент исходного текста (якорь)
    - position: before/after для insert
    - old_text: что ищем/меняем (если отличается от anchor)
    - new_text: новый текст для insert/replace
    - reasoning: краткое объяснение или причина отказа
    """
    operation: OperationType
    anchor: Optional[str] = Field(None)
    position: Optional[str] = Field(
        None,
        description="Для insert: 'before' или 'after'"
    )
    old_text: Optional[str] = None
    new_text: Optional[str] = None
    reasoning: Optional[str] = None


class EditIntent(BaseModel):
    """
    Намерение: описание планируемой правки до конкретного текста.
    """
    intent_id: str
    agent_id: str
    operation: OperationType
    anchor: Optional[str]
    summary: str
    status: IntentStatus
    created_at: float


class EditComment(BaseModel):
    """
    Комментарий/критика/дополнение к чужому намерению.
    """
    comment_id: str
    target_intent_id: str
    agent_id: str
    kind: CommentKind
    content: str
    created_at: float


@dataclass
class ChatMessage:
    """
    Сообщение чата: сырая строка + возможные структурированные сущности.
    """
    message_id: str
    agent_id: str
    text: str
    created_at: float
    intent: Optional[EditIntent] = None
    comment: Optional[EditComment] = None


@dataclass
class DocumentVersion:
    version_index: int
    text: str
    created_at: float
    source_agent_id: Optional[str] = None
    intent_id: Optional[str] = None


# ==========================
# ГЛОБАЛЬНОЕ СОСТОЯНИЕ
# ==========================

@dataclass
class SharedState:
    document_versions: List[DocumentVersion] = field(default_factory=list)
    chat_messages: List[ChatMessage] = field(default_factory=list)
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    def current_document(self) -> DocumentVersion:
        return self.document_versions[-1]

    def next_version_index(self) -> int:
        return len(self.document_versions)


STATE = SharedState()


# ==========================
# ДОКУМЕНТ: ВЕРСИОНИРОВАНИЕ
# ==========================

def save_document_version_to_file(doc_version: DocumentVersion):
    filename = DOCS_DIR / f"document_v{doc_version.version_index:04d}.txt"
    with filename.open("w", encoding="utf-8") as f:
        f.write(doc_version.text)


async def append_new_document_version(new_text: str,
                                      agent_id: Optional[str],
                                      intent_id: Optional[str]):
    async with STATE.lock:
        idx = STATE.next_version_index()
        doc_ver = DocumentVersion(
            version_index=idx,
            text=new_text,
            created_at=time.time(),
            source_agent_id=agent_id,
            intent_id=intent_id,
        )
        STATE.document_versions.append(doc_ver)
        save_document_version_to_file(doc_ver)
        print_and_log_chat(f"[DOC] New document version v{idx:04d} by {agent_id or 'system'} (intent={intent_id})")


# ==========================
# ЧАТ: СООБЩЕНИЯ
# ==========================

async def add_chat_message(agent_id: str,
                           text: str,
                           intent: Optional[EditIntent] = None,
                           comment: Optional[EditComment] = None) -> ChatMessage:
    msg = ChatMessage(
        message_id=random_id("msg"),
        agent_id=agent_id,
        text=text,
        created_at=time.time(),
        intent=intent,
        comment=comment,
    )
    async with STATE.lock:
        STATE.chat_messages.append(msg)
    print_and_log_chat(f"[CHAT][{agent_id}] {text}")
    return msg


def snapshot_chat() -> List[ChatMessage]:
    # Демонстрационно: без блокировки. Для реальной системы нужен более строгий доступ.
    return list(STATE.chat_messages)


# ==========================
# OPENAI CLIENT
# ==========================

openai_client = openai.OpenAI(
    api_key=OPENAI_API_KEY,
    base_url=OPENAI_BASE_URL,
)


async def call_openai_json(
    system_prompt: str,
    user_prompt: str,
) -> Dict[str, Any]:
    """
    Вызов OpenAI Responses API и парсинг одного JSON-объекта из ответа.
    ВНИМАНИЕ: модель обязуемся промптом заставить вернуть ОДИН JSON-объект без лишнего текста.
    """
    instructions = (
        "Ответь строго ОДНИМ JSON-объектом. "
        "Не добавляй никакого текста до или после JSON. "
        "Если нужно что-то объяснить, делай это внутри полей JSON (например, reasoning)."
    )

    response = await asyncio.to_thread(
        openai_client.responses.create,
        model=OPENAI_MODEL,
        input=[
            {"role": "system", "content": system_prompt + "\n\n" + instructions},
            {"role": "user", "content": user_prompt},
        ],
    )

    raw_text = None
    try:
        if hasattr(response, "output_text") and response.output_text:
            raw_text = response.output_text
        else:
            if response.output and len(response.output) > 0:
                first_item = response.output[0]
                if hasattr(first_item, "content") and first_item.content:
                    pieces = []
                    for c in first_item.content:
                        if getattr(c, "type", None) == "output_text":
                            pieces.append(c.text)
                    if pieces:
                        raw_text = "\n".join(pieces)
    except Exception as e:
        print_and_log_chat(f"[ERROR] Failed to extract text from response: {e}")

    if not raw_text:
        raise RuntimeError("No text content from OpenAI response")

    txt = raw_text.strip()
    first_brace = txt.find("{")
    last_brace = txt.rfind("}")
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        txt = txt[first_brace:last_brace + 1]

    try:
        data = json.loads(txt)
    except Exception as e:
        print_and_log_chat(f"[ERROR] Failed to parse JSON from model: {e}\nRaw text: {txt}")
        raise

    return data


# ==========================
# АГЕНТ
# ==========================

class Agent:
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.completed_edits = 0

    async def run(self):
        iteration = 0
        while self.completed_edits < MAX_EDITS_PER_AGENT and iteration < MAX_ITERATIONS_PER_AGENT:
            iteration += 1
            await asyncio.sleep(random.uniform(MIN_DELAY_SECONDS, MAX_DELAY_SECONDS))

            try:
                await self.one_full_edit_cycle(iteration)
            except Exception as e:
                print_and_log_chat(f"[AGENT {self.agent_id}] Exception in cycle {iteration}: {e}")

        print_and_log_chat(f"[AGENT {self.agent_id}] Finished. Completed edits: {self.completed_edits}")

    # --------------------------
    # Один полный цикл правки
    # --------------------------

    async def one_full_edit_cycle(self, iteration: int):
        # ===== ШАГИ 1–2: Просмотр чата и документа =====
        chat_snapshot_1 = snapshot_chat()
        doc_snapshot_1 = STATE.current_document()
        chat_summary_1 = self.build_chat_summary(chat_snapshot_1)

        # ===== ШАГ 3: Генерация НАМЕРЕНИЯ + возможные комментарии/критика =====
        intent_op, pre_comments = await self.generate_intent_and_comments(
            document_text=doc_snapshot_1.text,
            chat_context=chat_summary_1,
            chat_snapshot=chat_snapshot_1,
        )

        # Публикуем сгенерированные комментарии/критики
        await self.publish_comments(pre_comments)

        if intent_op.operation == OperationType.NONE:
            await add_chat_message(
                self.agent_id,
                f"(no-op) Решил не предлагать правку в этой итерации.",
            )
            return

        intent = EditIntent(
            intent_id=random_id("intent"),
            agent_id=self.agent_id,
            operation=intent_op.operation,
            anchor=intent_op.anchor,
            summary=intent_op.reasoning or "Намерение без подробного объяснения",
            status=IntentStatus.PROPOSED,
            created_at=time.time(),
        )

        # ===== ШАГИ 4–5: Снова читаем чат и документ =====
        await asyncio.sleep(random.uniform(MIN_DELAY_SECONDS, MAX_DELAY_SECONDS))
        chat_snapshot_2 = snapshot_chat()
        doc_snapshot_2 = STATE.current_document()

        # ===== ШАГ 6: Подтверждение/отмена намерения (модель может скорректировать) + комментарии =====
        confirm_op, mid_comments = await self.confirm_intent_and_comment(
            intent=intent,
            old_doc=doc_snapshot_1,
            new_doc=doc_snapshot_2,
            chat_snapshot=chat_snapshot_2,
        )
        await self.publish_comments(mid_comments)

        if confirm_op.operation == OperationType.NONE:
            intent.status = IntentStatus.CANCELLED
            await add_chat_message(
                self.agent_id,
                f"(intent cancelled) {intent.summary}",
                intent=intent,
            )
            return

        # Обновляем намерение по скорректированной операции
        intent.operation = confirm_op.operation
        intent.anchor = confirm_op.anchor
        intent.summary = confirm_op.reasoning or intent.summary
        intent.status = IntentStatus.CONFIRMED

        # ===== ШАГ 7: Публикация намерения =====
        await add_chat_message(
            self.agent_id,
            f"(intent confirmed) {intent.summary} | op={intent.operation.value} anchor={repr(intent.anchor)[:80]}",
            intent=intent,
        )

        # ===== ШАГИ 8–9: Снова чата + документа =====
        await asyncio.sleep(random.uniform(MIN_DELAY_SECONDS, MAX_DELAY_SECONDS))
        chat_snapshot_3 = snapshot_chat()
        doc_snapshot_3 = STATE.current_document()
        chat_summary_3 = self.build_chat_summary(chat_snapshot_3)

        # ===== ШАГ 10: Генерация КОНКРЕТНОЙ ПРАВКИ + комментарии =====
        final_op, final_comments = await self.generate_final_operation_and_comments(
            intent=intent,
            document_text=doc_snapshot_3.text,
            chat_context=chat_summary_3,
        )
        await self.publish_comments(final_comments)

        if final_op.operation == OperationType.NONE:
            intent.status = IntentStatus.CANCELLED
            await add_chat_message(
                self.agent_id,
                f"(intent dropped at final) Модель решила отказаться от правки: {intent.summary}",
                intent=intent,
            )
            return

        # ===== ШАГ 11: ещё раз читаем чат и документ и решаем: публиковать/изменить/отменить =====
        await asyncio.sleep(random.uniform(MIN_DELAY_SECONDS, MAX_DELAY_SECONDS))
        chat_snapshot_4 = snapshot_chat()
        doc_snapshot_4 = STATE.current_document()
        chat_summary_4 = self.build_chat_summary(chat_snapshot_4)

        final_op_adjusted = await self.review_and_adjust_final_operation(
            intent=intent,
            op=final_op,
            current_document_text=doc_snapshot_4.text,
            chat_context=chat_summary_4,
        )

        if final_op_adjusted.operation == OperationType.NONE:
            intent.status = IntentStatus.CANCELLED
            await add_chat_message(
                self.agent_id,
                f"(intent cancelled at post-review) Модель отменила правку после дополнительного осмотра.",
                intent=intent,
            )
            return

        # ===== ШАГ 12: применяем правку к текущему документу =====
        old_text = doc_snapshot_4.text
        new_text, applied = self.apply_operation_to_text(old_text, final_op_adjusted)

        if not applied:
            intent.status = IntentStatus.CANCELLED
            await add_chat_message(
                self.agent_id,
                f"(intent failed to apply) Не удалось применить правку (anchor не найден/конфликт). {intent.summary}",
                intent=intent,
            )
            return

        # Создаём новую версию документа
        intent.status = IntentStatus.EXECUTED
        await append_new_document_version(new_text, self.agent_id, intent.intent_id)

        await add_chat_message(
            self.agent_id,
            f"(edit applied) {intent.summary} | op={final_op_adjusted.operation.value}",
            intent=intent,
        )

        self.completed_edits += 1

    # --------------------------
    # Вспомогательные методы агента
    # --------------------------

    def build_chat_summary(self, messages: List[ChatMessage], max_messages: int = 30) -> str:
        last = messages[-max_messages:]
        lines = []
        for m in last:
            tag = ""
            if m.intent:
                tag = f"[INTENT:{m.intent.status.value}] "
            elif m.comment:
                tag = f"[COMMENT:{m.comment.kind.value}] "
            lines.append(f"{m.agent_id}: {tag}{m.text}")
        return "\n".join(lines) if lines else "(чат пуст)"

    def find_recent_intents(self, messages: List[ChatMessage], max_age_sec: float = 60.0) -> List[EditIntent]:
        now = time.time()
        intents = []
        for m in messages:
            if m.intent and (now - m.intent.created_at) <= max_age_sec:
                intents.append(m.intent)
        return intents

    async def publish_comments(self, comments: List[EditComment]):
        for c in comments:
            await add_chat_message(
                self.agent_id,
                f"(comment {c.kind.value} to {c.target_intent_id}) {c.content}",
                comment=c,
            )

    # --------------------------
    # ГЕНЕРАЦИЯ НАМЕРЕНИЯ + КОММЕНТАРИЕВ
    # --------------------------

    async def generate_intent_and_comments(
        self,
        document_text: str,
        chat_context: str,
        chat_snapshot: List[ChatMessage],
    ) -> Tuple[EditOperation, List[EditComment]]:
        """
        Первый запрос к модели:
        - Сгенерировать НАМЕРЕНИЕ (как EditOperation).
        - Сгенерировать список комментариев/критики к уже существующим намерениям.
        """
        recent_intents = self.find_recent_intents(chat_snapshot)
        intents_desc = [
            f"{it.intent_id} from {it.agent_id}: op={it.operation.value}, anchor={repr(it.anchor)[:60]}, status={it.status.value}, summary={it.summary}"
            for it in recent_intents
        ]
        intents_text = "\n".join(intents_desc) if intents_desc else "(намёрений нет)"

        system_prompt = (
            "Ты — один из параллельных агентов-редакторов.\n"
            "Сейчас ты должен:\n"
            "1) Сформировать потенциальную ЛОКАЛЬНУЮ правку (намерение) для документа.\n"
            "2) При желании прокомментировать или покритиковать некоторые чужие намерения.\n\n"
            "Верни ОДИН JSON-объект вида:\n"
            "{\n"
            '  "intent_operation": {... EditOperation ...},\n'
            '  "comments": [\n'
            '    {\n'
            '      "target_intent_id": "string",\n'
            '      "kind": "critique" | "support" | "suggestion",\n'
            '      "content": "string"\n'
            '    }, ...\n'
            '  ]\n'
            "}\n\n"
            "Если не хочешь предлагать правку — поставь intent_operation.operation=\"none\".\n"
            "Если нет комментариев — верни пустой массив comments.\n"
        )

        user_prompt = (
            f"Текущий документ:\n{document_text}\n\n"
            f"Последние сообщения в чате:\n{chat_context}\n\n"
            f"Недавние намерения других агентов:\n{intents_text}\n\n"
            "Сформируй своё намерение (или откажись) и опциональные комментарии к чужим намерениям."
        )

        data = await call_openai_json(system_prompt, user_prompt)

        # Парсим intent_operation
        intent_data = data.get("intent_operation", {})
        try:
            intent_op = EditOperation(**intent_data)
        except ValidationError as ve:
            print_and_log_chat(f"[AGENT {self.agent_id}] Validation error in intent_operation: {ve}")
            intent_op = EditOperation(operation=OperationType.NONE)

        # Парсим comments
        comments: List[EditComment] = []
        for raw_c in data.get("comments", []):
            try:
                c = EditComment(
                    comment_id=random_id("cmt"),
                    target_intent_id=str(raw_c.get("target_intent_id", "")),
                    agent_id=self.agent_id,
                    kind=CommentKind(raw_c.get("kind", "critique")),
                    content=str(raw_c.get("content", "")),
                    created_at=time.time(),
                )
                if c.target_intent_id and c.content.strip():
                    comments.append(c)
            except Exception as e:
                print_and_log_chat(f"[AGENT {self.agent_id}] Failed to parse comment: {e} | raw={raw_c}")

        return intent_op, comments

    # --------------------------
    # ПОДТВЕРЖДЕНИЕ НАМЕРЕНИЯ + КОММЕНТАРИИ
    # --------------------------

    async def confirm_intent_and_comment(
        self,
        intent: EditIntent,
        old_doc: DocumentVersion,
        new_doc: DocumentVersion,
        chat_snapshot: List[ChatMessage],
    ) -> Tuple[EditOperation, List[EditComment]]:
        """
        Второй запрос к модели:
        - Решить, подтверждать ли намерение (или скорректировать/отменить).
        - Сгенерировать дополнительные комментарии/критику к чужим намерениям.
        """
        chat_summary = self.build_chat_summary(chat_snapshot)
        recent_intents = self.find_recent_intents(chat_snapshot)
        intents_desc = [
            f"{it.intent_id} from {it.agent_id}: op={it.operation.value}, anchor={repr(it.anchor)[:60]}, status={it.status.value}, summary={it.summary}"
            for it in recent_intents
        ]
        intents_text = "\n".join(intents_desc) if intents_desc else "(намерений нет)"

        system_prompt = (
            "Ты — агент, который уже сформировал намерение, но теперь должен решить, оставлять ли его.\n"
            "Мир изменился: документ и чат могли поменяться.\n\n"
            "Верни ОДИН JSON-объект:\n"
            "{\n"
            '  "updated_intent": {... EditOperation ...},\n'
            '  "comments": [\n'
            '    {"target_intent_id": "string", "kind": "critique|support|suggestion", "content": "string"}, ...\n'
            '  ]\n'
            "}\n\n"
            "Если хочешь отменить своё намерение, поставь updated_intent.operation = \"none\".\n"
        )

        user_prompt = (
            f"Твоё исходное намерение:\n"
            f"- operation: {intent.operation.value}\n"
            f"- anchor: {repr(intent.anchor)}\n"
            f"- summary: {intent.summary}\n\n"
            f"Документ в момент намерения:\n{old_doc.text}\n\n"
            f"Документ сейчас:\n{new_doc.text}\n\n"
            f"Последние сообщения в чате:\n{chat_summary}\n\n"
            f"Недавние намерения других агентов:\n{intents_text}\n\n"
            "Реши, стоит ли сохранить/скорректировать или отменить своё намерение. "
            "И при желании прокомментируй чужие намерения."
        )

        data = await call_openai_json(system_prompt, user_prompt)

        op_data = data.get("updated_intent", {})
        try:
            op = EditOperation(**op_data)
        except ValidationError as ve:
            print_and_log_chat(f"[AGENT {self.agent_id}] Validation error in updated_intent: {ve}")
            op = EditOperation(operation=OperationType.NONE)

        comments: List[EditComment] = []
        for raw_c in data.get("comments", []):
            try:
                c = EditComment(
                    comment_id=random_id("cmt"),
                    target_intent_id=str(raw_c.get("target_intent_id", "")),
                    agent_id=self.agent_id,
                    kind=CommentKind(raw_c.get("kind", "critique")),
                    content=str(raw_c.get("content", "")),
                    created_at=time.time(),
                )
                if c.target_intent_id and c.content.strip():
                    comments.append(c)
            except Exception as e:
                print_and_log_chat(f"[AGENT {self.agent_id}] Failed to parse mid-comment: {e} | raw={raw_c}")

        return op, comments

    # --------------------------
    # ФИНАЛЬНАЯ ПРАВКА + КОММЕНТАРИИ
    # --------------------------

    async def generate_final_operation_and_comments(
        self,
        intent: EditIntent,
        document_text: str,
        chat_context: str,
    ) -> Tuple[EditOperation, List[EditComment]]:
        """
        Третий запрос к модели:
        - Сгенерировать конкретную правку (EditOperation).
        - Опционально ещё покомментировать чужие намерения.
        """
        system_prompt = (
            "Ты — агент, который сейчас должен СФОРМИРОВАТЬ КОНКРЕТНУЮ ПРАВКУ по уже подтверждённому намерению.\n"
            "Но ты всё ещё можешь решить, что она больше не нужна (operation = \"none\").\n\n"
            "Верни JSON:\n"
            "{\n"
            '  "final_operation": {... EditOperation ...},\n'
            '  "comments": [\n'
            '    {"target_intent_id": "string", "kind": "critique|support|suggestion", "content": "string"}, ...\n'
            '  ]\n'
            "}\n"
        )

        user_prompt = (
            f"Подтверждённое намерение:\n"
            f"- operation: {intent.operation.value}\n"
            f"- anchor: {repr(intent.anchor)}\n"
            f"- summary: {intent.summary}\n\n"
            f"Текущий документ:\n{document_text}\n\n"
            f"Последние сообщения в чате:\n{chat_context}\n\n"
            "Сформируй конкретную локальную правку или откажись от неё (operation = none). "
            "И при желании покомментируй чужие намерения."
        )

        data = await call_openai_json(system_prompt, user_prompt)

        op_data = data.get("final_operation", {})
        try:
            op = EditOperation(**op_data)
        except ValidationError as ve:
            print_and_log_chat(f"[AGENT {self.agent_id}] Validation error in final_operation: {ve}")
            op = EditOperation(operation=OperationType.NONE)

        comments: List[EditComment] = []
        for raw_c in data.get("comments", []):
            try:
                c = EditComment(
                    comment_id=random_id("cmt"),
                    target_intent_id=str(raw_c.get("target_intent_id", "")),
                    agent_id=self.agent_id,
                    kind=CommentKind(raw_c.get("kind", "critique")),
                    content=str(raw_c.get("content", "")),
                    created_at=time.time(),
                )
                if c.target_intent_id and c.content.strip():
                    comments.append(c)
            except Exception as e:
                print_and_log_chat(f"[AGENT {self.agent_id}] Failed to parse final-comment: {e} | raw={raw_c}")

        return op, comments

    # --------------------------
    # ПОСЛЕ-ГЕНЕРАЦИОННЫЙ REVIEW ПРАВКИ
    # --------------------------

    async def review_and_adjust_final_operation(
        self,
        intent: EditIntent,
        op: EditOperation,
        current_document_text: str,
        chat_context: str,
    ) -> EditOperation:
        """
        Четвёртый запрос (ревью уже сгенерированной правки):
        - перечитываем чат + документ,
        - решаем: применить, чуть изменить, или отменить (operation=none).
        """
        system_prompt = (
            "Ты — агент, который уже сгенерировал конкретную правку (EditOperation), "
            "но теперь перечитывает чат и документ и решает, стоит ли её применять.\n\n"
            "Верни ОДИН JSON-объект вида EditOperation. Если считаешь, что правка устарела или вредна, "
            "верни operation=\"none\" и объясни в reasoning.\n"
            "Можешь слегка скорректировать anchor/old_text/new_text, но не переписывай всё радикально."
        )

        user_prompt = (
            f"Твоё утверждённое намерение:\n"
            f"- operation: {intent.operation.value}\n"
            f"- anchor: {repr(intent.anchor)}\n"
            f"- summary: {intent.summary}\n\n"
            f"Сейчас у тебя есть следующая конкретная правка (EditOperation):\n"
            f"{op.dict()}\n\n"
            f"Текущий документ:\n{current_document_text}\n\n"
            f"Последние сообщения в чате:\n{chat_context}\n\n"
            "Реши, что делать с правкой: применить, немного скорректировать или отменить.\n"
        )

        data = await call_openai_json(system_prompt, user_prompt)
        try:
            adjusted = EditOperation(**data)
        except ValidationError as ve:
            print_and_log_chat(f"[AGENT {self.agent_id}] Validation error in review operation: {ve}")
            adjusted = EditOperation(operation=OperationType.NONE)
        return adjusted

    # --------------------------
    # ПРИМЕНЕНИЕ ПРАВКИ К ТЕКСТУ
    # --------------------------

    def apply_operation_to_text(self, text: str, op: EditOperation) -> Tuple[str, bool]:
        """
        Применяет семантическую операцию к тексту документа.
        ЛОГИКА:
        - всё по текстовым якорям, никаких индексов.
        - если фрагмент не найден — правка не применяется.
        """
        if op.operation == OperationType.NONE:
            return text, False

        def find_target() -> Optional[str]:
            if op.old_text and op.old_text.strip():
                return op.old_text
            if op.anchor and op.anchor.strip():
                return op.anchor
            return None

        if op.operation == OperationType.INSERT:
            if not op.anchor or not op.new_text or not op.position:
                return text, False
            idx = text.find(op.anchor)
            if idx == -1:
                return text, False
            if op.position == "before":
                insert_pos = idx
            elif op.position == "after":
                insert_pos = idx + len(op.anchor)
            else:
                return text, False
            new_text = text[:insert_pos] + op.new_text + text[insert_pos:]
            return new_text, True

        if op.operation == OperationType.REPLACE:
            target = find_target()
            if not target or not op.new_text:
                return text, False
            idx = text.find(target)
            if idx == -1:
                return text, False
            new_text = text[:idx] + op.new_text + text[idx + len(target):]
            return new_text, True

        if op.operation == OperationType.DELETE:
            target = find_target()
            if not target:
                return text, False
            idx = text.find(target)
            if idx == -1:
                return text, False
            new_text = text[:idx] + text[idx + len(target):]
            return new_text, True

        return text, False


# ==========================
# MAIN
# ==========================

async def main():
    ensure_dirs()

    # очищаем старый лог
    if CHAT_LOG_PATH.exists():
        CHAT_LOG_PATH.unlink()

    # начальная версия документа
    initial_doc = DocumentVersion(
        version_index=0,
        text=INITIAL_DOCUMENT_TEXT,
        created_at=time.time(),
        source_agent_id=None,
        intent_id=None,
    )
    STATE.document_versions.append(initial_doc)
    save_document_version_to_file(initial_doc)
    print_and_log_chat("[SYSTEM] Created initial document version v0000")

    # создаём агентов
    agents = [Agent(agent_id=f"agent-{i:02d}") for i in range(NUM_AGENTS)]
    tasks = [asyncio.create_task(a.run()) for a in agents]

    await asyncio.gather(*tasks)

    print_and_log_chat("[SYSTEM] All agents finished.")
    final_doc = STATE.current_document()
    print_and_log_chat(f"[SYSTEM] Final document version: v{final_doc.version_index:04d}")
    print_and_log_chat("[SYSTEM] See docs/ for document versions and logs/chat_log.txt for chat history.")


if __name__ == "__main__":
    asyncio.run(main())