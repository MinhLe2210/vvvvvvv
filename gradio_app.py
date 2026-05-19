import json
import traceback

import gradio as gr

from src.cms_validate import CMSValidator
from src.utils import (
    LocalTopic,
    LocationResult,
    SeverityResult2Lv,
    SeverityResult3Lv,
    SeverityResult3Lv2,
    SeverityResult4Lv,
    ValidationResult,
)


validator = CMSValidator()


SCHEMA_MAPPING = {
    "LocationResult": ("structured", None),
    "ValidationResult": ("structured", ValidationResult),
    "SeverityResult2Lv": ("structured", SeverityResult2Lv),
    "SeverityResult3Lv": ("structured", SeverityResult3Lv),
    "SeverityResult3Lv2": ("structured", SeverityResult3Lv2),
    "SeverityResult4Lv": ("structured", SeverityResult4Lv),
    "RawText": ("raw", None),
}


def json_text(data):
    return json.dumps(data, ensure_ascii=False, indent=2)


def refresh_location_prompt():
    return validator.get_prompt("Location")


def refresh_event_choices():
    validator.update_cache()
    choices = sorted(validator.cms_location.keys())
    return gr.update(
        choices=choices,
        value=choices[0] if choices else None,
    )


def show_places(event_id):
    places = validator.get_places(event_id) if event_id else None
    return places or ""


def save_location_prompt(prompt_text):
    if not prompt_text.strip():
        return "Prompt rỗng, chưa lưu."
    validator.save_prompt("Location", prompt_text)
    return "Đã lưu `cms_prompt.json[\"Location\"]` và reload cache."


def run_validation(
    event_id,
    request_id,
    title,
    description,
    display_name,
    content,
    places_override,
    location_prompt_text,
):
    try:
        output = validator.validate_cms(
            title=title,
            description=description,
            display_name=display_name,
            content=content,
            event_id=event_id or "",
            request_id=request_id or "",
            places_override=places_override or None,
            location_prompt_override=location_prompt_text or None,
        )
        mapped_places = validator.get_places(event_id) or ""
        return (
            mapped_places,
            output.location,
            output.topic,
            output.result,
            output.severity,
            output.description,
            json_text(output.model_dump()),
        )
    except Exception:
        return "", None, None, None, None, "Lỗi runtime", traceback.format_exc()


def run_prompt_lab(system_prompt, content, schema_name, model_name):
    schema_mode, entity = SCHEMA_MAPPING[schema_name]
    model_name = model_name or validator.model_default

    try:
        if schema_name == "LocationResult":
            response = validator.llm_parser(
                content=content,
                entity=LocationResult,
                model_name=model_name,
                system_prompt=system_prompt,
            )
            return json_text(response)

        if schema_mode == "structured":
            response = validator.llm_parser(
                content=content,
                entity=entity,
                model_name=model_name,
                system_prompt=system_prompt,
            )
            return json_text(response)

        response = validator.llm_text(
            content=content,
            system_prompt=system_prompt,
            model_name=model_name,
        )
        return json_text(response)
    except Exception:
        return traceback.format_exc()


def build_demo():
    with gr.Blocks(title="CMS Prompt Studio") as demo:
        gr.Markdown(
            """
            # CMS Prompt Studio
            Tab 1 dùng đúng luồng `CMS_VALIDATION_URL`, chỉ tập trung vào prompt `Location`.
            Tab 2 dùng để kiểm thử prompt tùy ý và xem parser trả về dữ liệu thế nào.
            """
        )

        with gr.Tab("Location Prompt"):
            with gr.Row():
                with gr.Column(scale=1):
                    event_id = gr.Dropdown(
                        label="Event ID",
                        choices=sorted(validator.cms_location.keys()),
                        value=sorted(validator.cms_location.keys())[0]
                        if validator.cms_location
                        else None,
                        allow_custom_value=True,
                    )
                    request_id = gr.Textbox(label="Request ID")
                    places_override = gr.Textbox(
                        label="places_override",
                        placeholder="Để trống để dùng mapping từ cms_location.json",
                    )
                    mapped_places = gr.Textbox(
                        label="Mapped places từ cms_location.json",
                        lines=6,
                        value=show_places(
                            sorted(validator.cms_location.keys())[0]
                            if validator.cms_location
                            else ""
                        ),
                        interactive=False,
                    )
                    refresh_event = gr.Button("Reload event mapping")

                with gr.Column(scale=2):
                    location_prompt = gr.Textbox(
                        label='cms_prompt.json["Location"]',
                        lines=24,
                        value=validator.get_prompt("Location"),
                    )
                    with gr.Row():
                        refresh_prompt_btn = gr.Button("Reload prompt file")
                        save_prompt_btn = gr.Button("Save prompt")
                        run_btn = gr.Button("Run validation", variant="primary")
                    save_status = gr.Textbox(label="Save status", interactive=False)

            with gr.Row():
                with gr.Column():
                    title = gr.Textbox(label="Title")
                    description = gr.Textbox(label="Description", lines=4)
                    display_name = gr.Textbox(label="Display name")
                    content = gr.Textbox(label="Content", lines=12)
                with gr.Column():
                    location_value = gr.Textbox(label="location", interactive=False)
                    topic_value = gr.Textbox(
                        label=f"topic ({', '.join(topic.value for topic in LocalTopic)})",
                        interactive=False,
                    )
                    result_value = gr.Textbox(label="result", interactive=False)
                    severity_value = gr.Textbox(label="severity", interactive=False)
                    description_value = gr.Textbox(label="status/description", interactive=False)
                    raw_output = gr.Code(label="Raw output", language="json")

            event_id.change(show_places, inputs=[event_id], outputs=[mapped_places])
            refresh_event.click(refresh_event_choices, outputs=[event_id])
            refresh_prompt_btn.click(refresh_location_prompt, outputs=[location_prompt])
            save_prompt_btn.click(save_location_prompt, inputs=[location_prompt], outputs=[save_status])
            run_btn.click(
                run_validation,
                inputs=[
                    event_id,
                    request_id,
                    title,
                    description,
                    display_name,
                    content,
                    places_override,
                    location_prompt,
                ],
                outputs=[
                    mapped_places,
                    location_value,
                    topic_value,
                    result_value,
                    severity_value,
                    description_value,
                    raw_output,
                ],
            )

        with gr.Tab("Custom Prompt Lab"):
            with gr.Row():
                with gr.Column(scale=1):
                    schema_name = gr.Dropdown(
                        label="Schema",
                        choices=list(SCHEMA_MAPPING.keys()),
                        value="LocationResult",
                    )
                    model_name = gr.Textbox(
                        label="Model name",
                        value=validator.model_default,
                    )
                    run_custom_btn = gr.Button("Run prompt", variant="primary")
                with gr.Column(scale=2):
                    custom_prompt = gr.Textbox(label="System prompt", lines=18)
            with gr.Row():
                with gr.Column():
                    custom_content = gr.Textbox(label="User content", lines=16)
                with gr.Column():
                    custom_output = gr.Code(label="Result", language="json")

            run_custom_btn.click(
                run_prompt_lab,
                inputs=[custom_prompt, custom_content, schema_name, model_name],
                outputs=[custom_output],
            )

    return demo


demo = build_demo()


if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860)
