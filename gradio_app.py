import csv
import json
import tempfile
import traceback
from pathlib import Path
from typing import Any

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


TOPIC_ORDER = [topic.value for topic in LocalTopic]

TOPIC_LABELS_VI = {
    LocalTopic.KNOWN.value: "Đã xử lý",
    LocalTopic.ALERT.value: "Cảnh báo",
    LocalTopic.SOCIAL_ORDER.value: "Trật tự xã hội",
    LocalTopic.SAR.value: "PCCC và cứu hộ cứu nạn",
    LocalTopic.ACCIDENT.value: "Tai nạn giao thông",
    LocalTopic.COMPLAINT.value: "Khiếu nại tố cáo",
    LocalTopic.SECURITY.value: "An ninh chính trị",
    LocalTopic.CHILD.value: "Bảo vệ trẻ em",
    LocalTopic.FICTION.value: "Hư cấu / giải trí",
    LocalTopic.SANITATION_POLLUTION.value: "Môi trường, an toàn thực phẩm",
    LocalTopic.CYBERSECURITY.value: "An ninh mạng",
    LocalTopic.MOVEMENT.value: "Phong trào toàn dân",
    LocalTopic.OTHER.value: "Khác",
}

DEFAULT_STAGE_1_PROMPT = """Bạn là một hệ thống phân loại nội dung tiếng Việt.

Với mỗi nội dung đầu vào, hãy thực hiện 2 việc:
1. Xác định nội dung có nhắc tới địa điểm/khu vực cụ thể liên quan trực tiếp tới sự việc hay không. Trả về location=true nếu có, location=false nếu không có.
2. Gán đúng một nhãn chính trong danh sách sau:
- Known: Sự vụ đã được công an, cảnh sát, cơ quan có thẩm quyền xử lý, can thiệp, bắt giữ, triệt phá, khởi tố, xét xử, tạm giam, phúc thẩm hoặc xử phạt.
- Alert: Cảnh báo lừa đảo, cảnh báo thiên tai hoặc cảnh báo rủi ro.
- Social Order: Trật tự xã hội như giết người, đánh nhau, gây rối, mua bán vũ khí, tiền giả, giấy tờ giả, lừa đảo, tín dụng đen, mua bán dữ liệu, mua bán người, đua xe, cờ bạc, tà đạo.
- SAR: Phòng cháy chữa cháy và cứu hộ cứu nạn như cháy nổ, đuối nước, thiên tai, cứu hộ nạn nhân.
- Accident: Tai nạn giao thông nghiêm trọng, gây thiệt hại về người hoặc tài sản.
- Complaint: Phản ánh, tố cáo, khiếu nại, kiến nghị, tụ tập phản đối liên quan cơ quan nhà nước hoặc doanh nghiệp.
- Security: Xuyên tạc, công kích nhà nước, lãnh đạo; thông tin tiêu cực liên quan đại hội, đồn đoán, lộ tài liệu mật của Nhà nước Việt Nam.
- Child: Bảo vệ trẻ em trên không gian mạng.
- Fiction: Truyện, tiểu thuyết, bài đăng giả tưởng, kể chuyện, giải trí, gameshow, phim truyền hình.
- SanitationPollution: Ô nhiễm môi trường, vệ sinh an toàn thực phẩm.
- Cybersecurity: An ninh mạng và tội phạm sử dụng công nghệ cao.
- Movement: Phong trào toàn dân bảo vệ an ninh trật tự.
- Other: Nội dung tích cực, trung lập, tổng hợp nhiều tin nhỏ lẻ hoặc không thuộc các nhóm trên.

Chỉ trả về dữ liệu theo schema được yêu cầu, không giải thích thêm."""

OUTPUT_COLUMNS = ["content", "result places", "label", "final result"]

SCHEMA_MAPPING = {
    "RawText": ("raw", None),
    "LocationResult": ("structured", LocationResult),
    "ValidationResult": ("structured", ValidationResult),
    "SeverityResult2Lv": ("structured", SeverityResult2Lv),
    "SeverityResult3Lv": ("structured", SeverityResult3Lv),
    "SeverityResult3Lv2": ("structured", SeverityResult3Lv2),
    "SeverityResult4Lv": ("structured", SeverityResult4Lv),
}

CUSTOM_CSS = """
.prompt-box textarea {
    font-family: ui-monospace, SFMono-Regular, Consolas, "Liberation Mono", monospace;
    font-size: 13px;
    line-height: 1.45;
}
.status-box textarea {
    font-weight: 600;
}
"""


def json_text(data: Any):
    return json.dumps(data, ensure_ascii=False, indent=2)


def topic_prompt_defaults():
    validator.update_cache()
    return {topic: validator.prompt_location.get(topic, "") for topic in TOPIC_ORDER}


def _file_path(file_obj) -> Path | None:
    if file_obj is None:
        return None
    if isinstance(file_obj, (str, Path)):
        return Path(file_obj)
    if isinstance(file_obj, dict) and file_obj.get("path"):
        return Path(file_obj["path"])
    name = getattr(file_obj, "name", None)
    return Path(name) if name else None


def _content_column_name(fieldnames: list[str]) -> str:
    for fieldname in fieldnames:
        if fieldname and fieldname.strip().lower() == "content":
            return fieldname

    columns = ", ".join(fieldnames)
    raise ValueError(f"CSV phải có cột 'content'. Các cột hiện có: {columns}")


def _read_csv(file_obj) -> list[str]:
    path = _file_path(file_obj)
    if path is None:
        raise ValueError("Chưa chọn file CSV.")

    last_error = None
    for encoding in ("utf-8-sig", "utf-8", "cp1258", "latin-1"):
        try:
            with path.open("r", encoding=encoding, newline="") as file:
                reader = csv.DictReader(file)
                if not reader.fieldnames:
                    raise ValueError("File CSV không có header.")
                content_column = _content_column_name(reader.fieldnames)

                contents = []
                for row in reader:
                    contents.append(str(row.get(content_column) or "").strip())
                return contents
        except UnicodeDecodeError as exc:
            last_error = exc
            continue

    raise ValueError(f"Không đọc được file CSV: {last_error}")


def _write_result_csv(rows: list[list[Any]]) -> str:
    tmp = tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".csv",
        prefix="cms_batch_result_",
        delete=False,
        encoding="utf-8-sig",
        newline="",
    )
    with tmp:
        writer = csv.writer(tmp)
        writer.writerow(OUTPUT_COLUMNS)
        writer.writerows(rows)
    return tmp.name


def _write_prompt_csv(
    places_override: str | None,
    stage_1_prompt: str,
    topic_prompt_values: tuple[Any, ...],
) -> str:
    tmp = tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".csv",
        prefix="cms_prompts_edited_",
        delete=False,
        encoding="utf-8-sig",
        newline="",
    )
    with tmp:
        writer = csv.writer(tmp)
        writer.writerow(["step", "topic", "label", "prompt"])
        writer.writerow(["stage_1", "", "Prompt bước 1", stage_1_prompt or ""])
        writer.writerow(["places_override", "", "Places override", places_override or ""])
        for topic, prompt in zip(TOPIC_ORDER, topic_prompt_values):
            writer.writerow(
                [
                    "stage_2",
                    topic,
                    TOPIC_LABELS_VI.get(topic, topic),
                    prompt or "",
                ]
            )
    return tmp.name


def _to_row_value(value: Any):
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    return str(value)


def _stage_1_prompt_with_places(stage_1_prompt: str, places_override: str | None) -> str:
    places_override = (places_override or "").strip()
    if not places_override:
        return stage_1_prompt

    return (
        f"{stage_1_prompt}\n\n"
        "Bổ sung yêu cầu places override:\n"
        "Chỉ trả location=true nếu nội dung liên quan trực tiếp tới một trong các địa điểm dưới đây. "
        "Nếu nội dung có địa điểm khác nhưng không khớp danh sách này, trả location=false.\n\n"
        f"Địa điểm cần kiểm tra:\n{places_override}"
    )


def run_csv_batch(
    csv_file,
    places_override,
    stage_1_prompt,
    *topic_prompt_values,
):
    try:
        model_name = validator.model_default
        stage_1_prompt = (stage_1_prompt or "").strip()
        if not stage_1_prompt:
            return [], None, None, "Prompt bước 1 đang trống."
        stage_1_prompt = _stage_1_prompt_with_places(stage_1_prompt, places_override)

        topic_prompts = {
            topic: (prompt or "").strip()
            for topic, prompt in zip(TOPIC_ORDER, topic_prompt_values)
        }
        contents = _read_csv(csv_file)

        rows = []
        errors = []
        for index, content in enumerate(contents, start=1):
            if not content:
                rows.append(["", None, "", None])
                continue

            places_result = None
            label = ""
            final_result = None

            first_response = validator.llm_parser(
                content=content,
                entity=LocationResult,
                model_name=model_name,
                system_prompt=stage_1_prompt,
                request_id=str(index),
            )

            first_llm = first_response.get("llm") or {}
            if not first_llm:
                errors.append(f"Dòng {index}: lỗi prompt bước 1")
                rows.append([content, places_result, label, final_result])
                continue

            places_result = first_llm.get("location")
            topic = first_llm.get("topic")
            label = TOPIC_LABELS_VI.get(topic, topic or "")

            if places_result is not True:
                final_result = False
                rows.append([content, _to_row_value(places_result), label, final_result])
                continue

            second_prompt = topic_prompts.get(topic, "")
            if not second_prompt:
                errors.append(f"Dòng {index}: chưa có prompt bước 2 cho label {label}")
                rows.append([content, _to_row_value(places_result), label, final_result])
                continue

            second_response = validator.llm_parser(
                content=content,
                entity=ValidationResult,
                model_name=model_name,
                system_prompt=second_prompt,
                request_id=str(index),
            )
            second_llm = second_response.get("llm") or {}
            if "result" not in second_llm:
                errors.append(f"Dòng {index}: lỗi prompt bước 2 cho label {label}")
            else:
                final_result = second_llm.get("result")

            rows.append([content, _to_row_value(places_result), label, final_result])

        output_file = _write_result_csv(rows)
        status = f"Đã xử lý {len(rows)} dòng."
        if errors:
            status += f" Có {len(errors)} lỗi/nhắc nhở: " + "; ".join(errors[:5])
            if len(errors) > 5:
                status += "..."

        return rows, output_file, output_file, status
    except Exception:
        return [], None, None, traceback.format_exc()


def download_prompt_csv(places_override, stage_1_prompt, *topic_prompt_values):
    try:
        return _write_prompt_csv(places_override, stage_1_prompt or "", topic_prompt_values)
    except Exception:
        return None


def run_prompt_lab(system_prompt, content, schema_name, model_name):
    schema_mode, entity = SCHEMA_MAPPING[schema_name]
    model_name = model_name or validator.model_default

    try:
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
    prompt_defaults = topic_prompt_defaults()

    with gr.Blocks(title="CMS Prompt Studio") as demo:
        gr.Markdown(
            """
            # CMS Prompt Studio
            Upload CSV có cột `content`, chỉnh prompt bước 1 để lấy `result places` và `label`, rồi chỉnh prompt bước 2 theo từng label để tính `final result`.
            """
        )

        with gr.Tab("CSV Batch"):
            with gr.Row():
                with gr.Column(scale=3):
                    csv_file = gr.File(
                        label="CSV đầu vào",
                        file_types=[".csv"],
                        type="filepath",
                    )
                with gr.Column(scale=2):
                    places_override = gr.Textbox(
                        label="Places override",
                        lines=3,
                        placeholder="Nhập nhanh tỉnh/thành để test prompt bước 1. VD: Hà Nội, TP.HCM, Đà Nẵng",
                    )

            with gr.Accordion("Prompt bước 1: result places + label", open=True):
                stage_1_prompt = gr.Textbox(
                    label="Prompt bước 1",
                    lines=18,
                    value=DEFAULT_STAGE_1_PROMPT,
                    elem_classes=["prompt-box"],
                )

            with gr.Accordion("Prompt bước 2 theo label", open=True):
                prompt_inputs = []
                with gr.Tabs():
                    for topic in TOPIC_ORDER:
                        tab_label = TOPIC_LABELS_VI.get(topic, topic)
                        with gr.Tab(tab_label):
                            prompt_inputs.append(
                                gr.Textbox(
                                    label=f"{tab_label} ({topic})",
                                    lines=14,
                                    value=prompt_defaults.get(topic, ""),
                                    placeholder=(
                                        "Nhập prompt bước 2 cho label này. "
                                        "Nếu để trống, final result sẽ không chạy cho label này."
                                    ),
                                    elem_classes=["prompt-box"],
                                )
                            )

            with gr.Row():
                run_btn = gr.Button("Chạy CSV", variant="primary")
                output_file = gr.File(label="File kết quả", interactive=False)
                download_result_btn = gr.DownloadButton(
                    "Download CSV kết quả",
                    value=None,
                    variant="secondary",
                )
                download_prompts_btn = gr.DownloadButton(
                    "Download CSV prompts đã sửa",
                    value=download_prompt_csv,
                    inputs=[places_override, stage_1_prompt, *prompt_inputs],
                    variant="secondary",
                )

            status = gr.Textbox(
                label="Trạng thái",
                interactive=False,
                elem_classes=["status-box"],
            )
            result_table = gr.Dataframe(
                label="Kết quả",
                headers=OUTPUT_COLUMNS,
                datatype=["str", "bool", "str", "bool"],
                interactive=False,
                wrap=True,
            )

            run_btn.click(
                run_csv_batch,
                inputs=[
                    csv_file,
                    places_override,
                    stage_1_prompt,
                    *prompt_inputs,
                ],
                outputs=[result_table, output_file, download_result_btn, status],
            )

        with gr.Tab("Custom Prompt Lab"):
            with gr.Row():
                with gr.Column(scale=1):
                    schema_name = gr.Dropdown(
                        label="Schema",
                        choices=list(SCHEMA_MAPPING.keys()),
                        value="RawText",
                    )
                    lab_model_name = gr.Textbox(
                        label="Model",
                        value=validator.model_default,
                    )
                    run_custom_btn = gr.Button("Run prompt", variant="primary")
                with gr.Column(scale=2):
                    custom_prompt = gr.Textbox(
                        label="System prompt",
                        lines=18,
                        elem_classes=["prompt-box"],
                    )
            with gr.Row():
                with gr.Column():
                    custom_content = gr.Textbox(label="User content", lines=16)
                with gr.Column():
                    custom_output = gr.Code(label="Result", language="json")

            run_custom_btn.click(
                run_prompt_lab,
                inputs=[custom_prompt, custom_content, schema_name, lab_model_name],
                outputs=[custom_output],
            )

    return demo


demo = build_demo()


if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860, css=CUSTOM_CSS)
