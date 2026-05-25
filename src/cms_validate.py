# cms_validate.py

import json
import traceback
from typing import Any

import httpx
from openai import OpenAI
from pydantic import BaseModel

from src import configs
from src.utils import (
    ErrorCodes,
    LocalTopic,
    LocationResult,
    OutputValidation,
    SEVERITY_MAPPING,
    ValidationResult,
    logging_service,
)


PROMPT_LIKE_TOPICS = {
    LocalTopic.ALERT.value,
    LocalTopic.SOCIAL_ORDER.value,
    LocalTopic.SAR.value,
    LocalTopic.ACCIDENT.value,
    LocalTopic.COMPLAINT.value,
    LocalTopic.SECURITY.value,
    LocalTopic.CHILD.value,
    LocalTopic.SANITATION_POLLUTION.value,
    LocalTopic.CYBERSECURITY.value,
    LocalTopic.MOVEMENT.value,
}


class CMSValidator:
    def __init__(self):
        self.time_out = configs.TIMEOUT
        self.max_try = configs.MAX_TRY
        self.openai_client = self._build_client()
        self.update_cache()

    def _build_client(self):
        if not configs.OPENAI_API_KEY:
            logging_service.warning("OPENAI_API_KEY is empty. LLM calls will fail.")
            return None

        http_client = None
        if configs.OPENAI_PROXY:
            http_client = httpx.Client(proxy=configs.OPENAI_PROXY)

        return OpenAI(
            api_key=configs.OPENAI_API_KEY,
            http_client=http_client,
            timeout=self.time_out,
        )

    def _load_json(self, path):
        return configs.load_json(path)

    def _save_json(self, path, data: dict):
        with path.open("w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=4)

    def update_cache(self):
        self.cms_location = self._load_json(configs.LOCATION_PATH)
        self.prompt_location = self._load_json(configs.PROMPT_PATH)
        self.prompt_custom = self._load_json(configs.CUSTOM_PROMPT_PATH)
        self.prompt_severity = self._load_json(configs.SEVERITY_PROMPT_PATH)
        self.model_name = self.prompt_location.get("model_name", {})
        self.model_default = self.model_name.get("default", configs.MODEL_DEFAULT)

    def save_prompt(self, key: str, value: str):
        data = self._load_json(configs.PROMPT_PATH)
        data[key] = value
        self._save_json(configs.PROMPT_PATH, data)
        self.update_cache()

    def get_prompt(self, key: str):
        self.update_cache()
        return self.prompt_location.get(key, "")

    def get_places(self, event_id: str):
        self.update_cache()
        return self.cms_location.get(event_id)

    def llm_parser(
        self,
        content: str,
        entity: type[BaseModel],
        model_name: str,
        system_prompt: str,
        request_id: str = "",
    ) -> dict[str, Any]:
        if self.openai_client is None:
            return {
                "request_id": request_id,
                "llm": {},
                "error": "OPENAI_API_KEY is empty",
            }

        msg = ""
        for _ in range(self.max_try):
            try:
                response = self.openai_client.responses.parse(
                    model=model_name,
                    input=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": content},
                    ],
                    text_format=entity,
                    temperature=0.1,
                    top_p=0.95,
                    timeout=self.time_out,
                )
                parsed = response.output_parsed
                return {"request_id": request_id, "llm": parsed.model_dump()}
            except Exception:
                msg = traceback.format_exc()
                logging_service.error(msg)

        return {"request_id": request_id, "llm": {}, "error": msg}

    def llm_text(
        self,
        content: str,
        system_prompt: str,
        model_name: str | None = None,
    ) -> dict[str, Any]:
        if self.openai_client is None:
            return {"text": "", "error": "OPENAI_API_KEY is empty"}

        model_name = model_name or self.model_default
        msg = ""
        for _ in range(self.max_try):
            try:
                response = self.openai_client.responses.create(
                    model=model_name,
                    input=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": content},
                    ],
                    temperature=0.1,
                    top_p=0.95,
                    timeout=self.time_out,
                )
                return {"text": response.output_text, "error": ""}
            except Exception:
                msg = traceback.format_exc()
                logging_service.error(msg)

        return {"text": "", "error": msg}

    def validate_local(
        self,
        text: str,
        event_id: str,
        places: str,
        output: OutputValidation,
        location_prompt_override: str | None = None,
    ):
        logging_service.info(
            "[validate_local] start request_id=%s event_id=%s text_len=%s places_len=%s override_prompt=%s",
            output.request_id,
            event_id,
            len(text or ""),
            len(places or ""),
            bool(location_prompt_override),
        )

        location_prompt = location_prompt_override or self.prompt_location[configs.LOCATION]

        logging_service.info(
            "[validate_local] running location parser request_id=%s model=%s",
            output.request_id,
            self.model_name.get(configs.LOCATION, self.model_default),
        )

        llm_location = self.llm_parser(
            content=text,
            entity=LocationResult,
            model_name=self.model_name.get(configs.LOCATION, self.model_default),
            system_prompt=f"{location_prompt}{places}",
            request_id=output.request_id,
        )

        output.result_detail["location_parser"] = llm_location.get("llm", {})
        if llm_location.get("error"):
            output.result_detail["location_error"] = llm_location["error"]
            logging_service.info(
                "[validate_local] location parser error request_id=%s error=%s",
                output.request_id,
                llm_location["error"],
            )

        if not llm_location.get("llm"):
            output.set_error(ErrorCodes.OPENAI_ERROR)
            output.description = llm_location.get("error") or output.description
            logging_service.info(
                "[validate_local] stop: empty location llm request_id=%s description=%s",
                output.request_id,
                output.description,
            )
            return output

        is_valid_loc = llm_location["llm"].get("location")
        topic = llm_location["llm"].get("topic")
        output.location = is_valid_loc
        output.topic = topic
        output.result = False

        logging_service.info(
            "[validate_local] location parsed request_id=%s location=%s topic=%s",
            output.request_id,
            is_valid_loc,
            topic,
        )

        if not is_valid_loc or not topic:
            logging_service.info(
                "[validate_local] stop: invalid location/topic request_id=%s location=%s topic=%s",
                output.request_id,
                is_valid_loc,
                topic,
            )
            return output

        if topic == LocalTopic.KNOWN.value and self.prompt_location.get(LocalTopic.KNOWN.value):
            logging_service.info(
                "[validate_local] running known topic validation request_id=%s topic=%s model=%s",
                output.request_id,
                topic,
                self.model_name.get(LocalTopic.KNOWN.value, self.model_default),
            )

            llm_known = self.llm_parser(
                content=text,
                entity=ValidationResult,
                model_name=self.model_name.get(LocalTopic.KNOWN.value, self.model_default),
                system_prompt=self.prompt_location[LocalTopic.KNOWN.value],
                request_id=output.request_id,
            )
            output.result_detail["topic_validation"] = llm_known.get("llm", {})

            logging_service.info(
                "[validate_local] done known topic validation request_id=%s llm=%s",
                output.request_id,
                llm_known.get("llm", {}),
            )
            return output

        if topic not in PROMPT_LIKE_TOPICS:
            logging_service.info(
                "[validate_local] stop: topic does not need prompt validation request_id=%s topic=%s",
                output.request_id,
                topic,
            )
            return output

        topic_prompt = self.prompt_location.get(topic)
        severity_entity = SEVERITY_MAPPING.get(topic)
        severity_prompt = self.prompt_severity.get(topic)

        if not topic_prompt or severity_entity is None or not severity_prompt:
            output.set_error(ErrorCodes.CONFIG_ERROR)
            logging_service.info(
                "[validate_local] stop: config error request_id=%s topic=%s has_topic_prompt=%s has_severity_entity=%s has_severity_prompt=%s",
                output.request_id,
                topic,
                bool(topic_prompt),
                severity_entity is not None,
                bool(severity_prompt),
            )
            return output

        logging_service.info(
            "[validate_local] running topic validation request_id=%s topic=%s model=%s",
            output.request_id,
            topic,
            self.model_name.get(topic, self.model_default),
        )
        llm_topic = self.llm_parser(
            content=text,
            entity=ValidationResult,
            model_name=self.model_name.get(topic, self.model_default),
            system_prompt=topic_prompt,
            request_id=output.request_id,
        )

        topic_result = llm_topic.get("llm", {}).get("result")
        output.result_detail["topic_validation"] = llm_topic.get("llm", {})

        if llm_topic.get("error"):
            output.result_detail["topic_error"] = llm_topic["error"]
            logging_service.info(
                "[validate_local] topic validation error request_id=%s topic=%s error=%s",
                output.request_id,
                topic,
                llm_topic["error"],
            )

        logging_service.info(
            "[validate_local] topic validation parsed request_id=%s topic=%s result=%s",
            output.request_id,
            topic,
            topic_result,
        )

        if topic_result is None:
            output.set_error(ErrorCodes.OPENAI_ERROR)
            output.description = llm_topic.get("error") or output.description
            logging_service.info(
                "[validate_local] stop: topic result is None request_id=%s description=%s",
                output.request_id,
                output.description,
            )
            return output

        if not topic_result:
            output.result = False
            logging_service.info(
                "[validate_local] stop: topic result false request_id=%s topic=%s",
                output.request_id,
                topic,
            )
            return output

        output.result = True

        logging_service.info(
            "[validate_local] running severity parser request_id=%s topic=%s model=%s entity=%s",
            output.request_id,
            topic,
            configs.MODEL_SEVERITY,
            severity_entity.__name__,
        )

        llm_severity = self.llm_parser(
            content=text,
            entity=severity_entity,
            model_name=configs.MODEL_SEVERITY,
            system_prompt=severity_prompt,
            request_id=output.request_id,
        )

        output.result_detail["severity_parser"] = llm_severity.get("llm", {})

        if llm_severity.get("error"):
            output.result_detail["severity_error"] = llm_severity["error"]
            logging_service.info(
                "[validate_local] severity parser error request_id=%s topic=%s error=%s",
                output.request_id,
                topic,
                llm_severity["error"],
            )

        severity = llm_severity.get("llm", {}).get("severity")

        logging_service.info(
            "[validate_local] severity parsed request_id=%s topic=%s severity=%s",
            output.request_id,
            topic,
            severity,
        )

        if severity is None:
            output.set_error(ErrorCodes.OPENAI_ERROR)
            output.description = llm_severity.get("error") or output.description
            logging_service.info(
                "[validate_local] stop: severity is None request_id=%s description=%s",
                output.request_id,
                output.description,
            )
            return output

        output.severity = severity

        logging_service.info(
            "[validate_local] done request_id=%s event_id=%s location=%s topic=%s result=%s severity=%s",
            output.request_id,
            event_id,
            output.location,
            output.topic,
            output.result,
            output.severity,
        )

        return output

    def validate_cms(
        self,
        content: str,
        title: str,
        description: str,
        display_name: str,
        event_id: str,
        places_override: str | None = None,
        location_prompt_override: str | None = None,
        **kwargs,
    ):
        output = OutputValidation(request_id=kwargs.get("request_id", ""))
        text = f"{title}\n{description}\n{display_name}\n{content}".strip()
        custom_prompt = self.prompt_custom.get(event_id)
        places = places_override or self.cms_location.get(event_id)

        if not text:
            output.set_error(ErrorCodes.CONTENT_ERROR)
            return output

        if custom_prompt:
            llm = self.llm_parser(
                content=text,
                entity=ValidationResult,
                model_name=self.model_default,
                system_prompt=custom_prompt,
                request_id=output.request_id,
            )
            if llm.get("llm"):
                output.result = llm["llm"]["result"]
            else:
                output.set_error(ErrorCodes.OPENAI_ERROR)
                output.description = llm.get("error") or output.description
            return output

        if not places:
            output.set_error(ErrorCodes.EVENT_ERROR)
            return output

        return self.validate_local(
            text=text,
            event_id=event_id,
            places=places,
            output=output,
            location_prompt_override=location_prompt_override,
        )
