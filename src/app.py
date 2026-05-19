import time
import traceback

from fastapi import FastAPI

from src import configs
from src.cms_validate import CMSValidator
from src.utils import ErrorCodes, InputBase, OutputValidation, logging_service

app = FastAPI(title="CMS Validation")
cms_validator = CMSValidator()


@app.post(configs.CMS_VALIDATION_URL)
async def process(input_params: InputBase):
    start_time = time.time()
    try:
        output = cms_validator.validate_cms(**input_params.model_dump())
    except Exception:
        output = OutputValidation(request_id=input_params.request_id)
        output.set_error(ErrorCodes.INTERNAL_ERROR)
        logging_service.error(traceback.format_exc())

    processed_time = time.time() - start_time
    logging_service.info(
        f"Request ID: {input_params.request_id} - Processed time: {processed_time:.6f}s"
    )
    return output
